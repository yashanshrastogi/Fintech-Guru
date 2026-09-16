# FinTech Guru V2 - Architectural Portfolio

## Overview
FinTech Guru V2 is an architectural showcase of safe, agentic AI applied to deterministic financial modeling. 
It demonstrates how to effectively isolate non-deterministic Large Language Models from strict, compliance-bound mathematical logic.

## Key Design Patterns

### 1. Trust Boundaries
**The LLM is an extraction engine, not a reasoning engine.**
Instead of asking an LLM "Can this user afford this?", we ask the LLM "Extract the numeric intents from this user's natural language input". The extracted structured JSON is then injected into a classical, unit-tested deterministic pipeline (`FinancialState`).

### 2. Defensive Projection
Our 90-day simulator projects expenses using a P90 statistical bound of historical transactions, ensuring the engine aggressively accounts for inflation or variable utility bills. Salaries are conservatively anchored to their minimum historical date (e.g. 28th vs 30th).

### 3. State Invariance
Every calculated Payment Plan is mapped across the 90-day cashflow array. A hard safety boundary function guarantees that `projected_balance[day_i] >= minimum_balance_to_keep` for all `i`. Any plan that fails this invariant throws a `SafetyViolationError` and is discarded.

### 4. Metamorphic Testing
The core engine is tested via thousands of property-based, metamorphic perturbations to ensure that:
- Higher request amounts monotonically decrease safety.
- Removing salary unequivocally degrades affordability.
- Random noise in the input does not crash the system.

### 5. Multi-Container Telemetry
`DEBUG_PIPELINE_TRACE` tracks the exact sequential lifecycle of a request from Next.js -> FastAPI -> LLM Extraction -> Reconciliation -> P90 Forecast -> Safe Amount Optimization -> Safety Boundary Validation -> SQLite Persistence.
