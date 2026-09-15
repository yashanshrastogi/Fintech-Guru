"""
Forensic comparator: for each of the 21 amount-miss requests,
compare what each forecasting strategy would predict for amount_safe_to_pay
vs the expected ground truth.

This script does NOT modify production code.
It re-runs the cashflow simulation with patched pattern amounts.
"""
import sys, os, csv, json
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
from cashflow import find_amount_safe_to_pay, find_earliest_full_payment_date
from models import FinancialProfile, FinancialEvent
from config import FORECAST_DAYS

SAMPLE_CSV = REPO_ROOT / "dataset" / "sample_requests.csv"
COMPARISON_CSV = REPO_ROOT / "evaluation" / "v2_baseline" / "forecast_strategy_comparison.csv"
OUT_DIR = REPO_ROOT / "evaluation" / "v2_baseline"


def parse_d(v) -> Optional[Decimal]:
    try:
        return Decimal(str(v).replace(",","").strip())
    except:
        return None


def ewma(vals: List[Decimal], alpha=0.3) -> Decimal:
    if not vals: return None
    r = float(vals[0])
    for v in vals[1:]:
        r = alpha * float(v) + (1-alpha) * r
    return Decimal(str(round(r, 2)))


def trimmed_mean(vals: List[Decimal]) -> Decimal:
    if len(vals) < 4:
        return Decimal(str(round(statistics.mean([float(v) for v in vals]), 2)))
    t = sorted(vals)[1:-1]
    return Decimal(str(round(statistics.mean([float(v) for v in t]), 2)))


def patch_pattern_amounts(patterns: List[dict], strategy: str) -> List[dict]:
    """Return a copy of patterns with avg_amount replaced by the given strategy."""
    import copy
    patched = copy.deepcopy(patterns)
    for p in patched:
        # We stored amounts in the pattern; need to re-derive
        # Patterns only store avg_amount, so we need to use the raw amounts
        # The analysis script stores amounts_str per (request, category, direction)
        # We'll attach raw_amounts to each pattern in collect_patterns()
        raw = p.get("_raw_amounts", [])
        if not raw:
            continue
        if strategy == "median":
            p["avg_amount"] = Decimal(str(round(statistics.median([float(a) for a in raw]), 2)))
        elif strategy == "most_recent":
            p["avg_amount"] = raw[-1]
        elif strategy == "mean":
            p["avg_amount"] = Decimal(str(round(statistics.mean([float(a) for a in raw]), 2)))
        elif strategy == "ewma":
            p["avg_amount"] = ewma(raw, 0.3)
        elif strategy == "trimmed":
            p["avg_amount"] = trimmed_mean(raw)
    return patched


def collect_patterns_with_raw(reconciled, profile, req_date):
    """Run detect_recurring_patterns but also attach raw amounts to each pattern."""
    from datetime import timedelta
    patterns = detect_recurring_patterns(reconciled, profile, req_date)
    
    # Rebuild raw amounts from settled events
    settled = [
        e for e in reconciled
        if e.status in {"settled", "confirmed", "scheduled"}
        and e.event_date is not None
        and (e.amount_home_currency or e.amount) is not None
    ]
    groups = defaultdict(list)
    for e in settled:
        groups[(e.category, e.direction)].append(e)

    for p in patterns:
        key = (p["category"], p["direction"])
        group = groups.get(key, [])
        cutoff = req_date - timedelta(days=365)
        recent = [e for e in group if e.event_date >= cutoff] or group[-6:]
        raw = [
            (e.amount_home_currency or e.amount)
            for e in recent
            if (e.amount_home_currency or e.amount) is not None
            and (e.amount_home_currency or e.amount) > Decimal("0")
        ]
        p["_raw_amounts"] = raw

    return patterns


def run():
    print("=" * 70)
    print("PHASE 1: FORECASTING STRATEGY FORENSIC COMPARISON")
    print("=" * 70)

    store = load_all_data()
    fx = get_fx_converter(store.exchange_rates_df)

    # Load sample ground truth
    samples = {}
    with open(SAMPLE_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            samples[row["request_id"]] = row

    # Load baseline misses
    baseline_csv = OUT_DIR / "per_request.csv"
    amount_miss_rids = []
    with open(baseline_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["amt_ok"] == "False":
                amount_miss_rids.append(row["request_id"])

    request_map = {r.request_id: r for r in store.sample_requests}

    strategies = ["median", "most_recent", "mean", "ewma", "trimmed"]
    results = []

    for rid in sorted(amount_miss_rids):
        if rid not in samples or rid not in request_map:
            continue

        sample = samples[rid]
        req = request_map[rid]
        exp_amount = parse_d(sample.get("amount_safe_to_pay", ""))
        if exp_amount is None:
            continue

        uid = req.user_id
        profile = store.profiles.get(uid)
        if not profile:
            continue

        raw_events = store.events_by_user.get(uid, [])
        messages = list({
            m.message_id: m
            for m in store.messages_by_user.get(uid, []) + store.messages_by_request.get(rid, [])
        }.values())

        reconciled, _ = reconcile_events(raw_events, profile, req.request_date, messages, fx)
        base_patterns = collect_patterns_with_raw(reconciled, profile, req.request_date)

        row_data = {
            "request_id": rid,
            "exp_amount": str(exp_amount),
        }

        best_strategy = None
        best_error = None

        for strat in strategies:
            patched = patch_pattern_amounts(base_patterns, strat)
            try:
                det_amount = find_amount_safe_to_pay(
                    profile=profile,
                    events=reconciled,
                    patterns=patched,
                    request_date=req.request_date,
                    requested_amount=req.requested_amount,
                )
                error = abs(exp_amount - det_amount)
                row_data[f"det_{strat}"] = str(det_amount.quantize(Decimal("0.01")))
                row_data[f"err_{strat}"] = str(round(float(error), 2))

                if best_error is None or error < best_error:
                    best_error = error
                    best_strategy = strat
            except Exception as e:
                row_data[f"det_{strat}"] = f"ERROR:{e}"
                row_data[f"err_{strat}"] = "N/A"

        row_data["best_strategy"] = best_strategy
        row_data["best_error"] = str(round(float(best_error), 2)) if best_error else "N/A"
        results.append(row_data)

        print(f"  {rid}: exp={exp_amount}")
        for s in strategies:
            print(f"    {s:12s}: det={row_data.get(f'det_{s}','?'):>16}  err={row_data.get(f'err_{s}','?')}")
        print(f"    → BEST: {best_strategy} (err={row_data['best_error']})")

    # Aggregate: which strategy wins most often?
    win_counts = defaultdict(int)
    for r in results:
        if r.get("best_strategy"):
            win_counts[r["best_strategy"]] += 1

    print("\n" + "=" * 70)
    print("STRATEGY WIN COUNTS (most often gives smallest error):")
    for s, c in sorted(win_counts.items(), key=lambda x: -x[1]):
        print(f"  {s:15s}: {c}/{len(results)}")

    # MAE per strategy
    print("\nMAE PER STRATEGY:")
    for s in strategies:
        errors = []
        for r in results:
            v = r.get(f"err_{s}")
            if v and v != "N/A" and not v.startswith("ERROR"):
                try:
                    errors.append(float(v))
                except:
                    pass
        mae = round(sum(errors)/len(errors), 2) if errors else None
        print(f"  {s:15s}: MAE = {mae}")

    # Save
    if results:
        fields = list(results[0].keys())
        out_csv = OUT_DIR / "strategy_forensic.csv"
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(results)
        print(f"\n  Saved: {out_csv}")

    # Save recommendation
    overall_winner = max(win_counts, key=win_counts.get) if win_counts else "most_recent"
    rec = {
        "recommended_strategy": overall_winner,
        "win_counts": dict(win_counts),
        "notes": "Choose strategy that minimizes MAE across all 21 amount-miss requests."
    }
    with open(OUT_DIR / "strategy_recommendation.json", "w") as f:
        json.dump(rec, f, indent=2)

    print(f"\n  RECOMMENDATION: {overall_winner}")
    print("DONE")


if __name__ == "__main__":
    run()
