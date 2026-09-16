# V1 Limitations & Why V2 is Necessary

The V1 system was built under a 24-hour time constraint. While it successfully achieved Rank #702 out of 3,000 participants and proved the core logic, it has structural limitations preventing its use in a production environment.

## 1. Unsafe LLM Overrides
The primary flaw of V1 was allowing the multi-agent LLM topology to make final affordability decisions. An LLM reasoning layer occasionally overrode perfectly safe deterministic calculations based on hallucinated financial constraints, dropping the system's status accuracy.

## 2. Naive Forecasting
V1 treated recurring expenses by simply averaging historical transactions. 
- It did not account for high-variance expenses (which require conservative percentile buffering).
- It did not properly distinguish between historical observations and inferred future recurrence, leading to risks of double-counting.
- It lacked a robust income forecasting model capable of handling amended salary dates or raises.

## 3. Transaction Lifecycle Flaws
The system lacked a formal state machine for financial events. Cancelled, failed, pending, and amended transactions were processed using ad-hoc scripts rather than a strict reconciliation precedence pipeline.

## 4. Lack of Evaluation Automation
The V1 hackathon evaluation was limited to 25 public samples. It lacked a massive synthetic dataset capable of testing edge cases (like near-boundary affordability constraints and contradictory message evidence).

## Why V2 is Being Built
To transition from a prototype to an enterprise-grade API, V2 will rebuild the financial engine from scratch. It will institute a strictly deterministic core state, limit the LLM purely to data extraction, model transactions with a formal lifecycle, and deploy behind a scalable FastAPI wrapper.
