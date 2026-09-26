# Corruption and Repair Comparison Report

## Overview

This report compares the same evaluation set across the clean baseline, deliberately corrupted data, and data repaired from the trusted raw snapshot.

## RAG Metrics

| Metric | Baseline | Corrupted | Repaired | Corruption change | Recovery change |
|---|---:|---:|---:|---:|---:|
| `retrieval_hit_rate` | 1.0000 | 0.8000 | 1.0000 | -0.2000 | +0.2000 |
| `mean_token_f1` | 1.0000 | 0.9000 | 1.0000 | -0.1000 | +0.1000 |
| `judge_accuracy` | 1.0000 | 0.9000 | 1.0000 | -0.1000 | +0.1000 |
| `mean_judge_score` | 5.0000 | 4.7000 | 5.0000 | -0.3000 | +0.3000 |

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
- Mean token-F1 change after corruption: -0.1000.
- Mean token-F1 recovery: +0.1000.

## Interpretation

- Removing or damaging indexed documents reduced retrieval coverage on the unchanged benchmark.
- The quality gate detected the deliberately corrupted state.
- Rebuilding from the raw snapshot restored the expected quality and freshness state.
- Repaired retrieval and answer metrics fully recovered to the clean baseline.

## Evidence

- Corruption log: `data/results/corruption_log.json`
- Corrupted metrics: `data/results/corrupted_metrics.json`
- Repaired metrics: `data/results/repaired_metrics.json`
- Corrupted quality: `data/quality/corrupted_quality_report.json`
- Repaired quality: `data/quality/repaired_quality_report.json`
