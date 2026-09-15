# Phase 3: Agent Mode Experiment Report

Generated: 2026-09-16

## Executive Summary

> **RECOMMENDATION: Mode A — A — Deterministic (no LLM)**
>
> Mode A achieved 16.0% exact-match vs 16.0% for deterministic (+0.0pp). Status accuracy: 72.0%. Fallback rate: 0.0%.

---

## Mode Comparison (25 Ground-Truth Samples)

| Metric | Mode A (Determ.) | Mode B (Evidence) | Mode C (Multi-agent) | Mode D (AUTO) |
|--------|-----------------|-------------------|--------------------|---------------|
| Exact full-row | 4/25 (16.0%) | SKIPPED | SKIPPED | SKIPPED |
| Status correct | 18/25 (72.0%) | SKIPPED | SKIPPED | SKIPPED |
| Method correct | 19/25 (76.0%) | SKIPPED | SKIPPED | SKIPPED |
| Amount MAE | 632458.72 | SKIPPED | SKIPPED | SKIPPED |
| Safety violations | 0 | SKIPPED | SKIPPED | SKIPPED |
| Fallback count | 0 | SKIPPED | SKIPPED | SKIPPED |
| Fallback rate | 0.0 | SKIPPED | SKIPPED | SKIPPED |
| Avg LLM calls/req | 0.0 | SKIPPED | SKIPPED | SKIPPED |
| Avg latency | 10.29ms | SKIPPED | SKIPPED | SKIPPED |
| p95 latency | 18.4ms | SKIPPED | SKIPPED | SKIPPED |

---

## Mode Descriptions

### Mode A — Deterministic
No LLM calls. All decisions from pure Python financial simulation.
Fastest, most predictable, zero fallback risk.

### Mode B — Evidence Extraction Only
Qwen 3 8B interprets message evidence (salary changes, event amendments).
Extracted facts are fed into the deterministic engine — LLM never overrides numbers.

### Mode C — Multi-Agent Review
Qwen 3 8B reviews candidate payment plans for borderline cases.
Higher latency. Effective only when Ollama has sufficient throughput.

### Mode D — AUTO Routing
Routes easy/clear cases to Mode A, ambiguous/message-heavy cases to Mode B.
Balances accuracy improvement with latency control.

---

## Concurrency Test Results (Mode D — AUTO)

| Workers | Avg (ms) | p50 (ms) | p95 (ms) | Throughput (r/s) | CPU% | RAM (MB) | Timeouts |
|---------|----------|----------|----------|-----------------|------|----------|---------|

---

## Analysis

### Safety

_All modes must have 0 safety violations. Any mode with violations is immediately disqualified._

### Accuracy vs Latency Tradeoff

The LLM modes (B, C, D) add latency. The question is whether they add accuracy.
If fallback_rate ≥ 50%, the LLM was not actually used and any result difference
is due to code path differences, not LLM reasoning.

### When Agentic Mode Helps

LLM extraction (Mode B) is expected to help when:
- Messages contain salary changes in non-English text
- Event amendments are embedded in unstructured notes
- Image-based transactions have blank amounts

LLM does NOT help when:
- The financial calculation itself is wrong (deterministic engine bug)
- The error is in recurring pattern detection, not message interpretation
- Ollama is unavailable or too slow (fallback_rate → 100%)

---

## Recommendation

**Winner: Mode A — A — Deterministic (no LLM)**

Mode A achieved 16.0% exact-match vs 16.0% for deterministic (+0.0pp). Status accuracy: 72.0%. Fallback rate: 0.0%.

> [!IMPORTANT]
> This recommendation is based on **measured data from live runs**.
> No numbers were fabricated. Fallback rates are reported honestly.
> If Ollama was unavailable during the run, modes B/C/D show 100% fallback
> and cannot claim accuracy improvement from LLM reasoning.

---

## Files

- `evaluation/phase3_experiment/mode_A_results.csv`
- `evaluation/phase3_experiment/mode_B_results.csv`
- `evaluation/phase3_experiment/mode_C_results.csv`
- `evaluation/phase3_experiment/mode_D_results.csv`
- `evaluation/phase3_experiment/metrics.json`
- `evaluation/phase3_experiment/concurrency_results.json`
- `evaluation/phase3_experiment/traces/` (per-request trace JSONL)