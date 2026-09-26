# Corruption and Repair Comparison Report

## Evaluation configuration

- Baseline: {'version': 2, 'retrieval': 'semantic_only', 'answer_mode': 'grounded_llm', 'provider': 'gemini', 'model': 'gemini-3.5-flash-lite', 'judge_mode': 'heuristic', 'top_k': 4, 'embedding_model': 'sentence-transformers/all-MiniLM-L6-v2', 'test_set_sha256': 'c735aa9aff78984a3d9b6d9835778866bd7a863f05a48ab9aa2705c887da6aa4'}
- Corrupted: {'version': 2, 'retrieval': 'semantic_only', 'answer_mode': 'grounded_llm', 'provider': 'gemini', 'model': 'gemini-3.5-flash-lite', 'judge_mode': 'heuristic', 'top_k': 4, 'embedding_model': 'sentence-transformers/all-MiniLM-L6-v2', 'test_set_sha256': 'c735aa9aff78984a3d9b6d9835778866bd7a863f05a48ab9aa2705c887da6aa4'}
- Repaired: {'version': 2, 'retrieval': 'semantic_only', 'answer_mode': 'grounded_llm', 'provider': 'gemini', 'model': 'gemini-3.5-flash-lite', 'judge_mode': 'heuristic', 'top_k': 4, 'embedding_model': 'sentence-transformers/all-MiniLM-L6-v2', 'test_set_sha256': 'c735aa9aff78984a3d9b6d9835778866bd7a863f05a48ab9aa2705c887da6aa4'}

## Overview

This report compares the same evaluation set across the clean baseline, deliberately corrupted data, and data repaired from the trusted raw snapshot.

## RAG Metrics

| Metric | Baseline | Corrupted | Repaired | Corruption change | Recovery change |
|---|---:|---:|---:|---:|---:|
| `retrieval_hit_rate` | 1.0000 | 0.8000 | 1.0000 | -0.2000 | +0.2000 |
| `mean_token_f1` | 0.8728 | 0.6792 | 0.8572 | -0.1936 | +0.1780 |
| `judge_accuracy` | 1.0000 | 0.7000 | 0.9000 | -0.3000 | +0.2000 |
| `mean_judge_score` | 4.4000 | 3.6000 | 4.2000 | -0.8000 | +0.6000 |

## Data Quality and Freshness

| Signal | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Overall quality gate | True | False | True |
| GX quality checks | True | False | True |
| Row count | 24.0000 | 21.0000 | 24.0000 |
| Freshness status | True | False | True |
| Stale rows | 1.0000 | 6.0000 | 1.0000 |
| Stale ratio | 0.0417 | 0.2857 | 0.0417 |

## Impact Analysis

- Retrieval hit-rate change after corruption: -0.2000.
- Retrieval hit-rate recovery: +0.2000.
- Mean token-F1 change after corruption: -0.1936.
- Mean token-F1 recovery: +0.1780.

## Interpretation

- Removing or damaging indexed documents reduced retrieval coverage on the unchanged benchmark.
- The quality gate detected the deliberately corrupted state.
- Rebuilding from the raw snapshot restored the expected quality and freshness state.
- Repaired metrics did not exactly match baseline; inspect the repaired index, evaluation answers and run configuration.

## Evidence

- Corruption log: `data/results/corruption_log.json`
- Corrupted metrics: `data/results/corrupted_metrics.json`
- Repaired metrics: `data/results/repaired_metrics.json`
- Corrupted quality: `data/quality/corrupted_quality_report.json`
- Repaired quality: `data/quality/repaired_quality_report.json`
