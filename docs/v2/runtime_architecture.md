# V2 Runtime Architecture

This document maps every module in the V2 architecture to ensure strict integration and traceability.

## Core Modules

### 1. `core/reconciliation.py` (EventLifecycle)
- **Purpose**: Normalizes, deduplicates, and standardizes raw transactions into canonical events.
- **Input**: Raw transaction records (initiated, pending, confirmed, failed).
- **Output**: Cleaned list of canonical `FinancialEvent` objects.
- **Caller**: Currently none (was intended for pipeline ingress).
- **Downstream Consumer**: `core/state.py` (FinancialState)
- **Test**: `tests/test_reconciliation.py` (Needs creation/verification)
- **Runtime Status**: **NOT_WIRED**

### 2. `core/state.py` (FinancialState)
- **Purpose**: Acts as the single source of truth for the user's finances at any given moment.
- **Input**: Normalized events, reconciled balance, recurring patterns.
- **Output**: Unified `FinancialState` object.
- **Caller**: `app/main.py`
- **Downstream Consumer**: Forecasting engines, Simulators, Optimizers.
- **Test**: Implicitly tested via `tests/test_api.py`
- **Runtime Status**: **WIRED**

## Forecasting Modules

### 3. `forecasting/expenses.py`
- **Purpose**: Calculates P90 (conservative) variability for recurring expenses.
- **Input**: Canonical expense events.
- **Output**: `RecurringPattern` with P90 padding.
- **Caller**: Currently none.
- **Downstream Consumer**: `FinancialState` / Simulator.
- **Test**: Needs creation.
- **Runtime Status**: **NOT_WIRED**

### 4. `forecasting/income.py`
- **Purpose**: Forecasts stable income with confidence scoring, handling delays/amendments.
- **Input**: Canonical income events.
- **Output**: Anchored `RecurringPattern` for salary.
- **Caller**: Currently none.
- **Downstream Consumer**: `FinancialState` / Simulator.
- **Test**: Needs creation.
- **Runtime Status**: **NOT_WIRED**

### 5. `forecasting/simulator.py`
- **Purpose**: Projects daily cashflow over a 90-day horizon.
- **Input**: `FinancialState`, Candidate Purchase Amount, Schedule.
- **Output**: Boolean (safe/unsafe) and projected daily balances.
- **Caller**: `optimization/engine.py` and `optimization/planner.py`
- **Downstream Consumer**: `validation/boundary.py`
- **Test**: `tests/test_properties.py`
- **Runtime Status**: **WIRED**

## Evidence & LLM Modules

### 6. `evidence/text.py` & `evidence/image.py`
- **Purpose**: Extracts structured financial facts from unstructured text or images via Qwen.
- **Input**: Raw user strings or images.
- **Output**: Strict JSON (EvidenceFact).
- **Caller**: Currently none.
- **Downstream Consumer**: `llm/router.py` / `FinancialState`
- **Test**: Needs creation.
- **Runtime Status**: **NOT_WIRED**

### 7. `llm/router.py`
- **Purpose**: Determines whether a request can be answered deterministically or requires ambiguity resolution via LLM.
- **Input**: Request parameters and ambiguity signals.
- **Output**: Routing decision (deterministic vs. agentic-fallback).
- **Caller**: `app/main.py`
- **Downstream Consumer**: Core determinism or `llm/fallback.py`
- **Test**: `tests/test_router.py`
- **Runtime Status**: **WIRED**

## Optimization & Safety Modules

### 8. `optimization/engine.py` (find_max_safe_amount)
- **Purpose**: Uses binary search to find the exact maximum upfront payment the user can afford.
- **Input**: `FinancialState`, Requested Amount.
- **Output**: Maximum safe float amount.
- **Caller**: `app/main.py`
- **Downstream Consumer**: Payment Plan Optimizer.
- **Test**: `tests/test_properties.py`
- **Runtime Status**: **WIRED**

### 9. `optimization/planner.py` (generate_payment_plans)
- **Purpose**: Divides the requested amount into a structured installment schedule if full payment is unsafe.
- **Input**: `FinancialState`, Requested Amount, Max Months.
- **Output**: List of valid payment plans.
- **Caller**: `app/main.py`
- **Downstream Consumer**: API Response / `validation/boundary.py`
- **Test**: `tests/test_properties.py`
- **Runtime Status**: **WIRED**

### 10. `validation/boundary.py`
- **Purpose**: The absolute final check to ensure mathematical bankruptcy cannot occur.
- **Input**: Final payment plan and `FinancialState`.
- **Output**: Passes silently or throws `SafetyViolationError`.
- **Caller**: Expected to be `app/main.py` at the very end.
- **Downstream Consumer**: User API Response.
- **Test**: `tests/test_boundary.py`
- **Runtime Status**: **NOT_WIRED**
