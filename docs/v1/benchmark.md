# V1 Benchmark Results

The following telemetry was gathered from the final V1 hybrid architecture evaluated against 25 ground-truth requests.

## Accuracy (25 ground-truth samples)

| Metric | Deterministic Core | + Evidence Extraction | + Multi-Agent Review |
|--------|----------------------|-----------------------|----------------------|
| Exact full-row | 4/25 (16%) | 4/25 (16%) | 4/25 (16%) |
| Status correct | 18/25 (72%) | 18/25 (72%) | 17/25 (68%) |
| Method correct | 19/25 (76%) | 19/25 (76%) | 18/25 (72%) |
| Amount MAE | 632,458 IDR | 374,869 IDR | 374,869 IDR |
| Amount Max Error | 7,956,073 IDR | 4,135,289 IDR | 4,135,289 IDR |
| Safety violations | 0 | 0 | 0 |

## System Performance

| Metric | Deterministic Core | + Evidence Extraction | + Multi-Agent Review |
|--------|----------------------|-----------------------|----------------------|
| Avg LLM calls/req | 0 | 1.68 | 3.96 |
| Fallback rate | 0% | 0% | 0% |
| Avg latency | ~10 ms | ~41.4 s | ~56.2 s |
| P95 latency | ~18 ms | ~62.1 s | ~112.5 s|

## Key Takeaways
1. **Evidence Extraction Works:** Extracting data from unstructured text/images drastically reduced the monetary error (MAE dropped by ~40%).
2. **Multi-Agent Debates Fail:** Running 4 LLMs in a debate format degraded decision accuracy (Status dropped from 72% to 68%) while pushing the p95 latency to nearly 2 minutes per request.
