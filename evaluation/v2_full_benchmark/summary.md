# Phase 9 — Full 250-Request Benchmark

Generated: 2026-09-16

## Accuracy on 25 Ground-Truth Samples

| Metric | V1-mode | V2-mode | Δ |
|--------|---------|---------|---|
| Exact full-row | 4/25 (16.0%) | 4/25 (16.0%) | +0 |
| Status correct | 18/25 (72.0%) | 18/25 (72.0%) | +0 |
| Method correct | 19/25 (76.0%) | 19/25 (76.0%) | +0 |
| Plan correct | 19/25 (76.0%) | 19/25 (76.0%) | +0 |
| Date correct | 17/25 (68.0%) | 17/25 (68.0%) | +0 |
| Spending correct | 22/25 (88.0%) | 22/25 (88.0%) | +0 |
| Amount MAE | 653418.56 | 632458.72 | — |
| Amount Max Error | 8370622.29 | 7956073.96 | — |

## Coverage on All 250 Requests

| Metric | V1-mode | V2-mode |
|--------|---------|---------|
| Safety violations | 0 | 0 |
| Row count | 250 | 250 |
| Latency avg (ms) | 8.93 | 9.49 |
| Latency p50 (ms) | 9.55 | 10.19 |
| Latency p95 (ms) | 16.76 | 17.17 |

## Notes

- V1-mode: deterministic pipeline with median-only forecast (V1 behavior)
- V2-mode: deterministic pipeline with adaptive CV-based forecast (Phase 1 improvement)
- No LLM calls in either mode (AGENTIC_MODE=false)
- Safety violations = 0 in both modes is expected and required