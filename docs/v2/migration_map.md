# V1 to V2 Migration Map

The following table documents how the monolithic components of V1 (`code/`) will be migrated into the clean V2 baseline.

| V1 Module | V2 Target Module | Action (Reuse / Rewrite / Remove) | Reason |
|-----------|------------------|-----------------------------------|--------|
| `models.py` | `core/models.py` | **Reuse** (with additions) | The core dataclasses (`FinancialProfile`, `Request`) are solid, but need expanded fields for formal event states (e.g. `EventStatus`). |
| `data_loader.py` | `core/data_loader.py` | **Reuse** | Basic CSV parsing is reusable. We will add stricter typed parsing. |
| `fx.py` | `core/fx.py` | **Reuse** | Exchange rate mapping is stateless and mathematically correct. |
| `reconciliation.py` | `core/reconciliation.py` | **Rewrite** | V1 lacked a formal state machine for events (Pending, Cancelled, Failed). Needs a strict deterministic precedence rewrite. |
| `cashflow.py` | `forecasting/cashflow.py` | **Rewrite** | V1's average-based recurring expense forecasting is too naive. Needs robust statistics for high-variance expenses and proper salary forecasting without double-counting. |
| `optimizer.py` | `optimization/engine.py` | **Rewrite** | V1 brute-forced the amount. V2 will use a bounded monotonic search for the `max safe amount`. |
| `candidate_plans.py` | `optimization/candidates.py` | **Rewrite** | Must integrate directly with the new deterministic optimization bounds rather than relying on heuristics. |
| `validator.py` | `validation/constraints.py` | **Reuse** (with additions) | The bounds-checking logic is highly reusable but needs expansion to cover the formal financial state. |
| `ollama_client.py` | `llm/client.py` | **Reuse** | The base client for communicating with `qwen3:8b` works well. |
| `image_extractor.py` | `evidence/image.py` | **Rewrite** | Must output strict JSON and never silently override deterministic data. |
| `vision.py` | `evidence/vision.py` | **Rewrite** | Same as above. Needs strict provenance tracking. |
| `agents.py` | N/A | **Remove** | Multi-agent debate is deprecated due to latency and accuracy degradation. |
| `multi_agent.py` | N/A | **Remove** | Multi-agent concurrency is deprecated. |
| `adjudicator.py` | N/A | **Remove** | Tie-breaking adjudicator is no longer needed. |
| `tracer.py` | `app/observability.py` | **Rewrite** | Will integrate into the new FastAPI deployment layer for proper enterprise telemetry. |
| `main.py` | `app/api.py` | **Rewrite** | The monolithic pipeline will be split into a FastAPI service handling the routing logic deterministically. |
