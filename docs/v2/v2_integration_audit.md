# V2 End-to-End Integration Audit

This audit traces the execution path of a single V2 production-style request to verify if the modules built in Phases 6-17 are correctly wired together.

## Audit Trace

### 1. Input Stage
* **Expected:** Raw request payload containing user context, raw transaction logs, and optional unstructured evidence (text/images).
* **Actual (Current state in `app/main.py` / `run_v2.py`):** The API currently expects pre-parsed `ApiRecurringEvent` objects.
* **V1 Leakage:** None, but the input is overly sanitized.

### 2. Reconciliation (Phase 6)
* **Expected:** Raw transactions route through `core/reconciliation.py` (`EventLifecycle`) to deduplicate and formalize state.
* **Actual:** **NOT WIRED**. The current execution path skips reconciliation entirely and instantiates `RecurringPattern` directly from the request JSON.
* **V1 Leakage:** None.
* **Impact:** The final decision relies on the client passing clean data rather than the system reconciling it.

### 3. Canonical State (Phase 11)
* **Expected:** Instantiation of `FinancialState` as the single source of truth.
* **Actual:** **WIRED**. `app/main.py` correctly builds and relies strictly on `FinancialState`.
* **V1 Leakage:** None.

### 4. Forecasting (Phases 7, 8, 12)
* **Expected:** Recurring expenses/income should be run through `forecasting/expenses.py` (P90 logic) and `forecasting/income.py` to buffer variance before entering the simulator.
* **Actual:** **PARTIALLY WIRED**. `simulate_cashflow` (Phase 12) is used, but the pre-simulation buffers (P90 expenses, anchored salary) from Phases 7 and 8 are skipped in the main execution path.
* **V1 Leakage:** None.
* **Impact:** Forecasts might be overly optimistic without the P90 buffer.

### 5. Evidence / Router (Phases 9, 10, 15)
* **Expected:** Evidence extraction routes through strict JSON guards (`evidence/text.py`, `evidence/image.py`), and `llm/router.py` correctly enforces routing.
* **Actual:** **ROUTER IS WIRED**, but **EVIDENCE IS NOT**. `app/main.py` uses `route_request()`, but it never invokes the evidence extraction pipelines to parse invoices.
* **V1 Leakage:** None.

### 6. Safe Amount (Phase 13)
* **Expected:** `find_max_safe_amount` computes the exact affordable amount using binary search.
* **Actual:** **WIRED**. Successfully used in the main pipeline.
* **V1 Leakage:** None.

### 7. Payment-Plan Optimization (Phase 14)
* **Expected:** `generate_payment_plans` divides the amount and simulates it.
* **Actual:** **WIRED**. The engine successfully proposes structured plans if the full amount isn't safe.
* **V1 Leakage:** None.

### 8. Safety Boundary (Phase 17)
* **Expected:** `validation/boundary.py` (`enforce_hard_safety_boundary`) runs as the absolute last step before returning the decision to prevent mathematical bankruptcy.
* **Actual:** **WIRED**. The engine explicitly throws all proposed plans against `enforce_hard_safety_boundary` inside `deterministic_pipeline` and discards any that fail.
* **V1 Leakage:** None.
* **Impact:** Mathematical safety is strictly guaranteed.

---

## Conclusion of Audit
The modules built in Phases 6-17 are mathematically sound and unit-tested in isolation, but they are **not fully integrated** into the central pipeline (`app/main.py` and `evaluation/run_v2.py`). 

To achieve a true "production-grade" pipeline, we must refactor the main entry points to ingest raw transactions, run them through reconciliation, apply the P90 forecasting buffers, invoke the evidence extractors if needed, and finalize the decision by throwing it against the Hard Safety Boundary.
