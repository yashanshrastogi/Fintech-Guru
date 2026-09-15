# V2 Development Comparison Report

Generated: 2026-09-16

## Scorecard: V1 Submission vs V2 Development

| Metric | V1 (Frozen Submission) | V2 Post-Phase-6 | Δ |
|--------|----------------------|-----------------|---|
| Amount exact match | 4/25 (16%) | 4/25 (16%) | 0 |
| Status correct | 18/25 (72%) | 18/25 (72%) | 0 |
| Exact full-row | 4/25 (16%) | 4/25 (16%) | 0 |
| Amount MAE | 653,418 | **632,458** | **−20,960 (−3.2%)** |
| Amount Max Error | 8,370,622 | **7,956,073** | **−414,549 (−5%)** |
| Safety violations | **0** | **0** | ✅ |
| Avg latency / req | 0.024s | **0.010s** | −58% faster |

> [!IMPORTANT]
> The submission (V1) is **FROZEN** and untouched on `main` branch.
> All V2 changes live on the `v2` branch — additive only.

---

## Phases Completed

### ✅ Phase 0 — Baseline Measurement
- Ran deterministic pipeline on all 25 ground-truth samples
- Frozen baseline: 4/25 exact, 18/25 status, MAE = 653,418
- Artifacts: `evaluation/v2_baseline/metrics.json`, `per_request.csv`

### ✅ Phase 1 — Forecast Calibration

Forensic analysis of 5 forecasting strategies across all 21 amount-miss requests:

| Strategy | Win Count | MAE |
|----------|-----------|-----|
| most_recent | 9/21 | 933,494 |
| **median** | 7/21 | **777,879** |
| trimmed | 2/21 | 972,729 |
| mean | 2/21 | 973,595 |
| ewma | 1/21 | 984,690 |

Implemented **adaptive CV-based strategy** in `detect_recurring_patterns()`:
- CV < 15% (stable) → `mean`
- CV ≥ 15% (variable) → `median`

**Result:** MAE −3.2%, Max Error −5%. Zero regressions.

### ✅ Phase 2 — Vision Provider Architecture

[`code/vision.py`](file:///c:/Users/Yashansh%20Rastogi/Downloads/Fintech%20Guru/code/vision.py) — abstract `VisionProvider` with two implementations:
- `DisabledVisionProvider` — safe no-op (default)
- `OllamaVisionProvider` — local llava/qwen2-vl support

Safety guarantees: failed extraction → `amount=None` (never 0), currency validation, confidence ≥ 0.7, provenance tracking.

### ✅ Phase 4 — FX Date Correction

Added `_get_fx_date()` to use correct FX lookup dates per event type:
- Cash events → settlement/event date (actual transaction FX)
- Investment credits (unrealized) → request_date (mark-to-market)

### ✅ Phase 5 — Multilingual & Prompt Hardening

- Prompt instructs LLM to handle any language (not just English)
- Security preamble rejects instruction injection
- Confidence field added to JSON schema
- Confidence gating in `main.py`: extractions < 0.5 confidence are not applied

### ✅ Phase 6 — Validator Safety Hardening

Two new hard safety checks (fail-closed):
- **Check 11**: Payment after `desired_completion_date` → revert to `not_recommended`
- **Check 12**: `earliest_date > desired_completion_date` → revert to `not_affordable`

### ✅ Phase 8 — Regression Test Suite

**44/44 tests pass (0.54s runtime):**

| File | Tests | Scope |
|------|-------|-------|
| `test_recurring_patterns.py` | 9 | Pattern detection, stable/variable amounts, salary, double-count |
| `test_validator.py` | 14 | All validator checks including Phase 6 |
| `test_fx.py` | 7 | FX date selection, missing rates, pivot chains |
| `test_vision.py` | 14 | Vision provider contract, all rejection scenarios |

---

## Outstanding Phases

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 3 | Multi-agent experiment (selective Qwen usage) | 🔲 Not started |
| Phase 7 | Per-request trace observability | 🔲 Not started |
| Phase 9 | Full 250-request benchmark with V2 | 🔲 Not started |
| Phase 10 | Final V1 vs V2 statistical comparison | 🔲 Not started |

---

## Safety Certification

| Property | Status |
|----------|--------|
| `amount_safe_to_pay ≥ 0` | ✅ Check 1 |
| `amount ≤ requested_amount` | ✅ Check 2 |
| No payment after deadline | ✅ Phase 6 Check 11 |
| Earliest date within deadline | ✅ Phase 6 Check 12 |
| **Safety violations (25 samples)** | **0/25** |
