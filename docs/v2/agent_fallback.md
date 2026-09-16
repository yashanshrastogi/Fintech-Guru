# Agent Fallback Policy (V2)

## Background
In the V1 HackerRank competition, a 3-agent "debate" architecture was designed for Mode C (Agentic). It intended to route through a Financial Analyst, a Risk & Evidence Auditor, and a Plan Reviewer before finalizing a decision.

However, forensic audits of V1 revealed that this multi-agent debate:
1. Failed to reliably execute due to routing bugs (`mode="agentic"` was not caught).
2. Was extremely slow and expensive in terms of token usage.
3. Often resulted in hallucinations that bypassed strict mathematical safety boundaries.

## V2 Decision
For the V2 production rebuild, we are **explicitly preventing the expensive multi-agent debate from running during standard requests**. 

Instead of an LLM debate, we have built a highly rigorous, mathematical **Deterministic Pipeline** (Amount-Safe Optimization). 

If a request explicitly routes to `multi_agent` (or `agentic`), the LLM Router will intercept it and immediately pass it to a fallback deterministic method. This ensures that the user still gets a mathematically safe response without invoking an unsafe and expensive LLM debate.

## Implementation
The fallback is implemented in `llm/fallback.py` as `mock_multi_agent_pipeline`. It explicitly logs that the multi-agent debate is disabled and executes the deterministic engine instead.
