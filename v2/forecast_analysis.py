"""
Phase 1: Forecast Calibration Analysis.

For each recurring expense/income pattern involved in an amount miss,
compares multiple forecasting strategies against the expected sample output.

Produces: evaluation/forecast_calibration_report.md

Usage:
  python v2/forecast_analysis.py

Does NOT modify any production code. Read-only analysis.
"""
import sys
import os
import csv
import json
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict
import statistics

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "code"))

os.environ["AGENTIC_MODE"] = "false"
os.environ["USE_LLM_EXPLANATIONS"] = "false"

from data_loader import load_all_data
from fx import get_fx_converter
from reconciliation import reconcile_events, detect_recurring_patterns
from models import FinancialEvent, FinancialProfile
from config import FORECAST_DAYS

SAMPLE_CSV = REPO_ROOT / "dataset" / "sample_requests.csv"
EVAL_DIR = REPO_ROOT / "evaluation"
OUT_DIR = EVAL_DIR / "v2_baseline"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_samples() -> Dict[str, dict]:
    samples = {}
    with open(SAMPLE_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            samples[row["request_id"]] = row
    return samples


def parse_decimal(val) -> Optional[Decimal]:
    try:
        return Decimal(str(val).replace(",", "").strip())
    except Exception:
        return None


def ewma(values: List[Decimal], alpha: float = 0.3) -> Optional[Decimal]:
    """Exponentially weighted moving average, oldest to newest."""
    if not values:
        return None
    result = float(values[0])
    for v in values[1:]:
        result = alpha * float(v) + (1 - alpha) * result
    return Decimal(str(round(result, 2)))


def trimmed_mean(values: List[Decimal]) -> Optional[Decimal]:
    """Mean after removing min and max, if >= 4 observations."""
    if len(values) < 4:
        return Decimal(str(round(statistics.mean([float(v) for v in values]), 2)))
    trimmed = sorted(values)[1:-1]
    return Decimal(str(round(statistics.mean([float(v) for v in trimmed]), 2)))


def analyze_patterns_for_request(request_id, sample_row, store, fx):
    """For one sample request, compute all pattern amount strategies."""
    from main import process_request
    import config as cfg

    uid = sample_row["user_id"]
    req_date_str = sample_row["request_date"]
    from datetime import date
    req_date = date.fromisoformat(req_date_str)

    profile = store.profiles.get(uid)
    if not profile:
        return None

    raw_events = store.events_by_user.get(uid, [])
    messages = list({
        m.message_id: m
        for m in store.messages_by_user.get(uid, []) + store.messages_by_request.get(request_id, [])
    }.values())

    reconciled, _ = reconcile_events(raw_events, profile, req_date, messages, fx)

    settled = [
        e for e in reconciled
        if e.status in {"settled", "confirmed", "scheduled"}
        and e.event_date is not None
        and (e.amount_home_currency or e.amount) is not None
    ]

    groups = defaultdict(list)
    for e in settled:
        groups[(e.category, e.direction, e.flexibility, e.event_type)].append(e)

    pattern_rows = []
    for (category, direction, flexibility, event_type), group in groups.items():
        if len(group) < 2:
            continue

        group_sorted = sorted(group, key=lambda e: e.event_date)

        # Get amounts in home currency
        from datetime import timedelta
        cutoff = req_date - timedelta(days=365)
        recent = [e for e in group_sorted if e.event_date >= cutoff] or group_sorted[-6:]
        amounts = [
            (e.amount_home_currency or e.amount)
            for e in recent
            if (e.amount_home_currency or e.amount) is not None
            and (e.amount_home_currency or e.amount) > Decimal("0")
        ]

        if not amounts:
            continue

        # Compute all strategies
        strat_median = Decimal(str(round(statistics.median([float(a) for a in amounts]), 2)))
        strat_most_recent = amounts[-1]
        strat_mean = Decimal(str(round(statistics.mean([float(a) for a in amounts]), 2)))
        strat_ewma = ewma(amounts, alpha=0.3)
        strat_trimmed = trimmed_mean(amounts)

        # What does current code use?
        current_forecast = strat_median

        pattern_rows.append({
            "request_id": request_id,
            "user_id": uid,
            "category": category,
            "direction": direction,
            "event_type": event_type,
            "flexibility": flexibility,
            "n_observations": len(group),
            "n_recent": len(recent),
            "amounts_str": "|".join(str(round(float(a), 2)) for a in amounts),
            "strat_median": strat_median,
            "strat_most_recent": strat_most_recent,
            "strat_mean": strat_mean,
            "strat_ewma": strat_ewma,
            "strat_trimmed": strat_trimmed,
            "current_forecast": current_forecast,
        })

    return pattern_rows


def run_forecast_analysis():
    print("=" * 70)
    print("PHASE 1: FORECAST CALIBRATION ANALYSIS")
    print("=" * 70)

    store = load_all_data()
    fx = get_fx_converter(store.exchange_rates_df)
    samples = load_samples()

    request_map = {r.request_id: r for r in store.requests}

    # Load existing baseline per_request.csv to know which requests have amount misses
    baseline_csv = OUT_DIR / "per_request.csv"
    amount_miss_rids = set()
    if baseline_csv.exists():
        with open(baseline_csv, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("amt_ok") == "False":
                    amount_miss_rids.add(row["request_id"])
        print(f"  Amount miss requests from baseline: {len(amount_miss_rids)}")
    else:
        # Analyze all if baseline not ready
        amount_miss_rids = set(samples.keys())
        print("  (Baseline CSV not found — analyzing all samples)")

    all_pattern_rows = []

    for rid in sorted(samples.keys()):
        sample = samples[rid]
        pattern_rows = analyze_patterns_for_request(rid, sample, store, fx)
        if pattern_rows:
            all_pattern_rows.extend(pattern_rows)

    # Save detailed CSV
    detail_csv = OUT_DIR / "forecast_strategy_comparison.csv"
    if all_pattern_rows:
        fields = list(all_pattern_rows[0].keys())
        with open(detail_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in all_pattern_rows:
                w.writerow({k: str(v) for k, v in r.items()})
        print(f"\n  Saved strategy comparison: {detail_csv}")

    # Now produce the markdown report
    report_path = EVAL_DIR / "forecast_calibration_report.md"
    lines = [
        "# Forecast Calibration Report",
        "",
        "## Summary",
        "",
        f"- Total patterns analyzed: {len(all_pattern_rows)}",
        f"- Requests with amount misses: {len(amount_miss_rids)}",
        "",
        "## Strategy Definitions",
        "",
        "| Strategy | Description |",
        "|----------|-------------|",
        "| median | Median of recent (≤1yr or last 6) amounts — **current production** |",
        "| most_recent | The most recent observed amount |",
        "| mean | Arithmetic mean of recent amounts |",
        "| ewma_0.3 | Exponentially weighted moving average (α=0.3) |",
        "| trimmed_mean | Mean with min/max removed (when ≥4 observations) |",
        "",
        "## Per-Request Pattern Detail",
        "",
    ]

    for rid in sorted(amount_miss_rids):
        if rid not in samples:
            continue
        sample = samples[rid]
        exp_amount = sample.get("amount_safe_to_pay", "?")
        exp_status = sample.get("affordability_status", "?")
        rows = [r for r in all_pattern_rows if r["request_id"] == rid]

        lines.append(f"### {rid}")
        lines.append(f"- Expected amount: `{exp_amount}` | Status: `{exp_status}`")
        lines.append(f"- User: `{sample.get('user_id', '?')}`")
        lines.append("")

        if not rows:
            lines.append("_No recurring patterns detected for this user._")
            lines.append("")
            continue

        lines.append("| Category | Dir | N | Median | MostRecent | Mean | EWMA(0.3) | Trimmed |")
        lines.append("|----------|-----|---|--------|------------|------|-----------|---------|")
        for r in rows:
            lines.append(
                f"| {r['category']} | {r['direction']} | {r['n_observations']} | "
                f"{r['strat_median']} | {r['strat_most_recent']} | "
                f"{r['strat_mean']} | {r['strat_ewma']} | {r['strat_trimmed']} |"
            )
        lines.append("")
        lines.append(f"**Amount history (recent):** `{rows[0]['amounts_str'] if rows else 'N/A'}`")
        lines.append("")
        lines.append("**Analysis:** TODO — fill in after reviewing numbers.")
        lines.append("")

    lines.append("## Conclusion")
    lines.append("")
    lines.append("_To be filled after reviewing per-request analysis._")
    lines.append("")
    lines.append("**Recommended strategy:** ")
    lines.append("")
    lines.append("**Expected improvement:** ")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  Saved calibration report: {report_path}")
    print("\nDONE — Forecast calibration analysis complete.")
    print("Next step: Review evaluation/forecast_calibration_report.md")
    print("           then implement the winning strategy in reconciliation.py")


if __name__ == "__main__":
    run_forecast_analysis()
