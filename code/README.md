# Buy or Wait? — Financial Decision Agent

## Architecture

This solution implements a **Hybrid Deterministic Financial Engine + Selective LLM Layer** for the HackerRank Orchestrate September 2026 challenge.

### Design Philosophy

The LLM is **never** the source of truth for financial calculations. All monetary arithmetic uses Python's `Decimal` module for exact precision. The LLM is called selectively for:
- Message interpretation (salary changes, event amendments)  
- Explanation generation
- Image OCR for blank event amounts (via vision API)

### System Components

```
code/
├── main.py              # Orchestration pipeline (16 phases per request)
├── config.py            # Configuration and paths
├── models.py            # Data models (using Decimal for all monetary values)
├── data_loader.py       # CSV ingestion with in-memory indexing
├── fx.py                # Deterministic FX conversion (static dated rates)
├── reconciliation.py    # Event lifecycle resolution + recurring pattern detection
├── cashflow.py          # 90-day daily balance simulation engine
├── candidate_plans.py   # Payment plan generation and ranking
├── optimizer.py         # Spending change search (minimum intervention)
├── image_extractor.py   # Vision API for blank event amounts
├── agents.py            # Selective LLM calls (message interpretation, explanations)
├── validator.py         # Output validation and constraint repair
└── evaluation/
    ├── usage_report.md
    └── validation_report.md
```

### Processing Pipeline (per request)

1. **Data Loading**: Load profile, events, messages, payment options
2. **Image Resolution**: Extract blank amounts from PNG images via vision API
3. **Event Reconciliation**: Cancel/confirm/amend events based on status and messages
4. **Message Interpretation**: LLM extracts salary changes and event amendments (selective)
5. **Pattern Detection**: Detect recurring income/expense patterns from history
6. **amount_safe_to_pay**: Binary search for max amount payable today (90-day safety check)
7. **Earliest Full Date**: Find earliest date when full amount is safe
8. **Spending Optimizer**: Find minimal spending changes that unlock payment
9. **Candidate Generation**: All eligible payment plans generated
10. **Plan Ranking**: Sort per problem spec (deadline > no changes > min cost > earlier > fewer)
11. **Status Determination**: Map best candidate to affordability_status
12. **Explanation Generation**: LLM generates or template provides explanation
13. **Validation**: Deterministic constraint validation and auto-repair
14. **Output**: Formatted CSV row

### Key Technical Decisions

#### Deterministic Core
- All balance calculations use `decimal.Decimal` (no floating-point errors)
- Binary search (30 iterations) for `amount_safe_to_pay`
- Pattern detection uses `statistics.median` for robustness
- Salary projected on correct day-of-month (not fixed 28-day interval)

#### Event Handling
- Skip: cancelled, failed, reversed, pending credits, unrealized investments
- Include: settled, scheduled, confirmed debits
- Message amendments override status (cancellation, confirmation)
- Blank amounts resolved via image extraction

#### 90-Day Simulation
- Daily granularity (91 days including request_date)
- Recurring patterns projected from last occurrence + detected interval
- Salary uses day-of-month projection for accuracy
- All foreign currency amounts converted to home_currency via static FX rates

#### Plan Generation
- Full payment: check each available option + direct payment
- Partial payment: exactly 2 payments summing to requested_amount
- Installments: must match exactly a supplied payment option
- Wait: full payment on earliest_date_for_full_payment
- Not recommended: fallback when no safe plan exists

## Setup

### Requirements

```bash
pip install pandas google-generativeai
```

For optional OpenAI/Anthropic support:
```bash
pip install openai anthropic
```

### Environment Variables

```bash
# Choose provider
export LLM_PROVIDER=google        # or: openai, anthropic, none
export LLM_MODEL=gemini-2.0-flash

# API keys (only the chosen provider needs a key)
export GOOGLE_API_KEY=your_key
export OPENAI_API_KEY=your_key
export ANTHROPIC_API_KEY=your_key

# Disable LLM for deterministic-only run
export USE_LLM_EXPLANATIONS=false
export USE_LLM_IMAGE_OCR=false
```

### Running

```bash
cd /path/to/repo
python code/main.py
```

Outputs:
- `output.csv` — predictions for all 250 requests
- `code/evaluation/usage_report.md` — token usage and cost report
- `code/evaluation/validation_report.md` — validation issues and auto-repairs
- `log.txt` — session log (per AGENTS.md requirements)

## Performance

- Data loading: ~35s (financial_events.csv has 25,343 rows)
- Request processing: ~0.1s per request (deterministic engine)
- LLM calls: 0-2 per request when enabled, ~37-45s total with LLM
- Total runtime: ~40-50s for 250 requests

## Scoring Approach

Optimized for the evaluation criteria:
1. `amount_safe_to_pay` — Binary search with 30 iterations → precision to cents
2. `affordability_status` — Derived from best candidate method
3. `recommended_payment_method` + `payment_plan` — Ranked per problem spec
4. `earliest_date_for_full_payment` — Day-by-day search through 90-day window
5. `spending_changes_needed` — Minimum-intervention search through flexible expenses
6. `decision_explanation` — LLM or deterministic template
