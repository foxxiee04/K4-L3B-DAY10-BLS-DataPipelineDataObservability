"""Dependency-isolated regression checks; not a substitute for GX/Chroma/LLM E2E.

Run: python -m unittest discover -s tests -v
Only selected production functions are loaded, because this review environment
does not have a usable project interpreter. External services are test doubles.
"""
import ast
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def functions(relative, names, namespace):
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
    nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names]
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)] + nodes, type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), relative, "exec"), namespace)
    return namespace


class ReviewFixes(unittest.TestCase):
    def test_semantic_results_are_not_replaced_by_exact_title(self):
        item = SimpleNamespace(paper_id="semantic", title="Other", content="Context", metadata={})
        index = Mock()
        index.search.return_value = [item]
        ns = functions("src/retrieval/qa.py", {"AnswerResult", "answer_question"}, {
            "dataclass": dataclass, "normalized_provider": lambda s: "mock",
            "_extract_answer": lambda q, r: "mock answer",
        })
        answer = ns["answer_question"]("Who authored 'Exact title'?", None, index)
        self.assertEqual(answer.retrieved_doc_ids, ["semantic"])
        index.lookup.assert_not_called()

    def test_real_provider_uses_retrieved_context(self):
        item = SimpleNamespace(paper_id="p1", title="Title", content="Known fact", metadata={})
        index = Mock(); index.search.return_value = [item]
        llm = Mock(); llm.invoke.return_value.content = "Grounded answer"
        ns = functions("src/retrieval/qa.py", {"AnswerResult", "answer_question"}, {
            "dataclass": dataclass, "normalized_provider": lambda s: "gemini", "build_llm": lambda *a, **k: llm,
        })
        self.assertEqual(ns["answer_question"]("Question", None, index).answer, "Grounded answer")
        self.assertIn("Known fact", llm.invoke.call_args.args[0][1][1])
        llm.invoke.return_value.content = ""
        with self.assertRaises(RuntimeError): ns["answer_question"]("Question", None, index)

    def judge_namespace(self):
        return functions("src/evaluation/metrics.py", {"_token_f1", "_judge_answer"}, {
            "os": os, "normalize_whitespace": lambda s: " ".join(s.split()),
            "JudgeVerdict": SimpleNamespace,
            "build_llm": Mock(side_effect=RuntimeError("service down")),
        })

    def test_heuristic_is_explicit_and_does_not_call_llm(self):
        ns = self.judge_namespace()
        with patch.dict(os.environ, {"JUDGE_MODE": "heuristic"}):
            result = ns["_judge_answer"](None, "q", "same", "same")
        self.assertEqual(result.score, 5)
        ns["build_llm"].assert_not_called()

    def test_llm_failure_does_not_fallback(self):
        ns = self.judge_namespace()
        with patch.dict(os.environ, {"JUDGE_MODE": "llm"}):
            with self.assertRaisesRegex(RuntimeError, "No silent fallback"):
                ns["_judge_answer"](None, "q", "same", "same")

    def test_contract_changes_when_test_set_changes(self):
        testset = [{"question": "first"}]
        ns = functions("src/evaluation/metrics.py", {"evaluation_contract"}, {
            "os": os, "hashlib": hashlib, "json": json,
            "read_json": lambda p: testset, "normalized_provider": lambda s: "mock",
        })
        settings = SimpleNamespace(model_name="unused", top_k=4, embedding_model="MiniLM")
        with patch.dict(os.environ, {"JUDGE_MODE": "heuristic"}):
            first = ns["evaluation_contract"](settings, "test")
            testset.append({"question": "second"})
            self.assertNotEqual(first, ns["evaluation_contract"](settings, "test"))

    def test_index_load_ignores_foreign_machine_path(self):
        tree = ast.parse((ROOT / "src/retrieval/index.py").read_text(encoding="utf-8"))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "LocalEmbeddingIndex")
        load = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "load")
        load.decorator_list = []
        ns = {"read_json": lambda p: {"collection_name": "papers-baseline", "documents": [], "persist_path": "Z:/foreign"}}
        module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), load], type_ignores=[])
        exec(compile(ast.fix_missing_locations(module), "index", "exec"), ns)
        settings = SimpleNamespace(paths=SimpleNamespace(embeddings_json="manifest", chroma_dir=Path("local/chroma")))
        result = ns["load"](lambda **kw: kw, settings)
        self.assertEqual(result["persist_path"], Path("local/chroma"))

    def test_baseline_report_uses_supplied_results(self):
        ns = functions("src/observability/reporting.py", {"generate_phase1_report"}, {
            "write_text": lambda p, s: Path(p).write_text(s, encoding="utf-8"),
        })
        with TemporaryDirectory() as directory:
            path = Path(directory) / "report.md"
            ns["generate_phase1_report"](path, {"rows": 24}, {"mean_token_f1": 0.37},
                                          {"success": False}, {"is_fresh": False})
            report = path.read_text(encoding="utf-8")
            self.assertIn("mean_token_f1: 0.37", report)
            self.assertIn("Overall success: False", report)


if __name__ == "__main__":
    unittest.main()
