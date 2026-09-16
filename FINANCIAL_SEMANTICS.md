# Financial Semantics & Mathematical Contracts

This document explicitly defines the deterministic behavior and rules of the FinTech Guru V2 engine.

## 1. Safety Boundary Invariant
**Invariant:** At no point in the 90-day simulation can the user's projected balance drop below their `minimum_balance_to_keep`.
If the purchase request amount or any generated payment plan violates this invariant, it is definitively blocked.

## 2. Recurrence & Forecasting
- `frequency_days=30` is mathematically treated as exactly 30 rolling calendar days from the `last_date`, overriding calendar-month oddities.
- A 30-day recurring expense will fire on day 30, day 60, and day 90 in the simulator window.
- The P90 function calculates the 90th percentile of historical variances to buffer expense spikes, providing a conservative safety net against under-estimating bills.

## 3. Same-Day Semantics
- In our deterministic engine, if an expense (like a purchase) and an income (like a salary) land on the **exact same day**, the engine treats them as sequentially safe if the incoming salary covers the outgoing expense. 
- A purchase request evaluates immediate affordability. Future affordability (via payment plans) requires subsequent installments to clear the invariant check.

## 4. LLM Fact Extraction
- Qwen3:8B extracts intent and numeric boundaries (e.g. salary changes).
- The LLM **never** touches or alters the output of `find_max_safe_amount`. It can only mutate the initial canonical input `FinancialState`.
