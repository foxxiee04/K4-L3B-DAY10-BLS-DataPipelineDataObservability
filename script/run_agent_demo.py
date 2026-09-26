"""Run a real tool-using agent and save evidence (requires a non-mock provider)."""
from core.config import load_settings, normalized_provider
from core.utils import read_json, write_json
from retrieval.agent import build_agent
from retrieval.index import LocalEmbeddingIndex


def main():
    settings = load_settings()
    if normalized_provider(settings) == "mock":
        raise ValueError("Agent demo requires a real provider; mock is only for offline QA.")
    index = LocalEmbeddingIndex.load(settings)
    question = read_json(settings.paths.eval_testset)[0]["question"]
    result = build_agent(settings, index).invoke({"messages": [{"role": "user", "content": question}]})
    messages = result.get("messages", [])
    tool_messages = [message for message in messages if getattr(message, "type", "") == "tool"]
    if not messages or not tool_messages:
        raise RuntimeError("No tool execution evidence returned by agent.")
    answer = messages[-1].content
    if not answer:
        raise RuntimeError("Agent returned no final answer.")
    write_json(settings.paths.demo_answers, {
        "provider": normalized_provider(settings), "model": settings.model_name,
        "question": question, "answer": answer,
        "tool_calls": [{"name": message.name, "content": message.content} for message in tool_messages],
    })
    print(answer)
    print(f"Saved tool execution evidence: {settings.paths.demo_answers}")


if __name__ == "__main__":
    main()
