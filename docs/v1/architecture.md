# V1 Architecture

The V1 Hackathon submission utilized a monolithic script structure with a hybrid approach combining deterministic financial math and experimental LLM agents.

## 1. Deterministic Financial Engine
The core of V1 was a strict deterministic engine responsible for mathematical correctness:
- **Data Loading:** Parsed inputs from 8 different CSVs.
- **FX Conversion:** Standardized multi-currency amounts using a fixed exchange rate table.
- **Event Reconciliation:** Processed pending and cancelled transactions to derive a current available balance.
- **Cash-flow Simulation:** Averaged historical recurring expenses to project future affordability constraints.
- **Optimization:** Generated and ranked candidate plans (full, partial, installments, wait) ensuring the simulated balance never dipped below the user's preferred minimum balance threshold.

## 2. Qwen/Ollama Integration
To handle unstructured data (user text messages and image receipts), V1 integrated with a local `qwen3:8b` model via the Ollama API. 
The LLM was tasked with extracting financial facts (e.g., salary updates or precise invoice amounts) that were then fed back into the deterministic engine.

## 3. Multi-Agent Experiments (Mode C)
V1 experimented with a multi-agent topology to deliberate on borderline cases. The architecture involved:
1. **Financial Analyst:** Evaluated mathematical feasibility.
2. **Risk Auditor:** Checked for boundary safety violations.
3. **Preference Reviewer:** Ensured the user's lifestyle choices were respected.
4. **Adjudicator:** Acted as a tie-breaker if the three agents disagreed.

While ambitious, this multi-agent debate was computationally expensive and occasionally overrode mathematically optimal decisions, forming the primary motivation for the V2 redesign.
