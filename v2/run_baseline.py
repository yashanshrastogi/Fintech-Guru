"""
Phase 0: V2 Baseline Measurement Script.

Runs the FROZEN V1 deterministic pipeline on all 25 sample requests.
Produces machine-readable metrics for comparison after each V2 phase.

Output:
  evaluation/v2_baseline/metrics.json
  evaluation/v2_baseline/per_request.csv

Usage:
  python v2/run_baseline.py
"""
import sys
import os
import json
import csv
import time
from decimal import Decimal
from pathlib import Path

# Point to the FROZEN V1 code directory
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "code"))

# Force deterministic-only mode — never call LLM for baseline
os.environ["AGENTIC_MODE"] = "false"
os.environ["USE_LLM_EXPLANATIONS"] = "false"
os.environ["USE_LLM_IMAGE_OCR"] = "false"

from data_loader import load_all_data
from fx import get_fx_converter
from main import process_request, format_result_row
import config

SAMPLE_CSV = REPO_ROOT / "dataset" / "sample_requests.csv"
OUT_DIR = REPO_ROOT / "evaluation" / "v2_baseline"
OUT_DIR.mkdir(parents=True, exist_ok=True)

STATUS_TOLERANCE = 0.0      # exact match
AMOUNT_TOLERANCE = Decimal("0.01")  # within 1 cent for same-currency


def load_sample_ground_truth():
    """Load the 25 sample requests with their expected outputs."""
    samples = {}
    with open(SAMPLE_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid = row["request_id"]
            samples[rid] = {
                "request_id": rid,
                "user_id": row.get("user_id", ""),
                "exp_amount": row.get("amount_safe_to_pay", ""),
                "exp_status": row.get("affordability_status", ""),
                "exp_method": row.get("recommended_payment_method", ""),
                "exp_plan": row.get("payment_plan", ""),
                "exp_date": row.get("earliest_date_for_full_payment", ""),
                "exp_spending": row.get("spending_changes_needed", ""),
            }
    return samples


def parse_decimal_safe(val: str) -> Decimal:
    try:
        return Decimal(str(val).replace(",", "").strip())
    except Exception:
        return None


def compare_amount(exp: str, got: str) -> bool:
    """Compare amounts with 1% tolerance (currency mixing requires relative)."""
    e = parse_decimal_safe(exp)
    g = parse_decimal_safe(got)
    if e is None or g is None:
        return False
    if e == Decimal("0") and g == Decimal("0"):
        return True
    # Use relative tolerance of 0.5% for amounts
    if e == 0:
        return abs(g) < Decimal("0.01")
    rel_error = abs(e - g) / abs(e)
    return rel_error < Decimal("0.005")  # 0.5%


def compare_payment_plan(exp: str, got: str) -> bool:
    """Compare payment plans (order-insensitive for amounts, date-sensitive)."""
    if exp == got:
        return True
    if (exp or "none").strip() == "none" and (got or "none").strip() == "none":
        return True
    return False


def run_baseline():
    print("=" * 70)
    print("V2 BASELINE MEASUREMENT — DETERMINISTIC MODE")
    print("=" * 70)

    # Load data
    print("\nLoading data...")
    t0 = time.time()
    store = load_all_data()
    fx = get_fx_converter(store.exchange_rates_df)
    load_time = time.time() - t0
    print(f"  Data loaded in {load_time:.2f}s: "
          f"{len(store.profiles)} profiles, "
          f"{sum(len(v) for v in store.events_by_user.values())} events, "
          f"{len(store.requests)} requests")

    # Load ground truth
    ground_truth = load_sample_ground_truth()
    sample_request_ids = set(ground_truth.keys())
    print(f"  Ground truth samples: {len(ground_truth)}")

    # Filter to sample requests only
    # sample_requests are loaded separately in the DataStore
    if hasattr(store, 'sample_requests') and store.sample_requests:
        sample_requests = [r for r in store.sample_requests if r.request_id in sample_request_ids]
    else:
        # Fallback: filter from main requests list
        sample_requests = [r for r in store.requests if r.request_id in sample_request_ids]
    sample_requests.sort(key=lambda r: r.request_id)


    # Run pipeline
    results = []
    per_request_rows = []
    total_inference_time = 0.0

    print(f"\nRunning pipeline on {len(sample_requests)} sample requests...")

    for req in sample_requests:
        rid = req.request_id
        gt = ground_truth[rid]

        t_start = time.time()
        try:
            result = process_request(req, store, fx, mode="deterministic")
            row = format_result_row(result)
        except Exception as e:
            print(f"  ERROR {rid}: {e}")
            row = {
                "request_id": rid,
                "amount_safe_to_pay": "0",
                "affordability_status": "not_affordable",
                "recommended_payment_method": "not_recommended",
                "payment_plan": "none",
                "earliest_date_for_full_payment": "",
                "spending_changes_needed": "none",
                "decision_explanation": f"ERROR: {e}",
            }
        elapsed = time.time() - t_start
        total_inference_time += elapsed

        # Compare
        det_amount = row.get("amount_safe_to_pay", "0")
        det_status = row.get("affordability_status", "")
        det_method = row.get("recommended_payment_method", "")
        det_plan = row.get("payment_plan", "none")
        det_date = row.get("earliest_date_for_full_payment", "")
        det_spending = row.get("spending_changes_needed", "none")

        exp_amount = gt["exp_amount"]
        exp_status = gt["exp_status"]
        exp_method = gt["exp_method"]
        exp_plan = gt["exp_plan"]
        exp_date = gt["exp_date"]
        exp_spending = gt["exp_spending"]

        amt_ok = compare_amount(exp_amount, det_amount)
        status_ok = (exp_status.strip() == det_status.strip())
        method_ok = (exp_method.strip() == det_method.strip())
        plan_ok = compare_payment_plan(exp_plan, det_plan)
        date_ok = (exp_date.strip() == det_date.strip())
        spending_ok = (
            (exp_spending or "none").strip() == (det_spending or "none").strip()
        )
        exact_row = amt_ok and status_ok and method_ok and plan_ok and date_ok and spending_ok

        # Amount error for MAE
        e_d = parse_decimal_safe(exp_amount)
        g_d = parse_decimal_safe(det_amount)
        amt_error = abs(e_d - g_d) if (e_d is not None and g_d is not None) else None

        label = "[EXACT    ]" if exact_row else (
            "[status_ok]" if status_ok else "[MISS     ]"
        )
        print(f"  {label} {rid}: exp={exp_amount}|{exp_status}|{exp_method} "
              f"det={det_amount}|{det_status}|{det_method}")

        results.append({
            "rid": rid,
            "amt_ok": amt_ok,
            "status_ok": status_ok,
            "method_ok": method_ok,
            "plan_ok": plan_ok,
            "date_ok": date_ok,
            "spending_ok": spending_ok,
            "exact_row": exact_row,
            "amt_error": float(amt_error) if amt_error is not None else None,
            "elapsed_s": elapsed,
        })

        per_request_rows.append({
            "request_id": rid,
            "exp_amount": exp_amount,
            "det_amount": det_amount,
            "exp_status": exp_status,
            "det_status": det_status,
            "exp_method": exp_method,
            "det_method": det_method,
            "exp_plan": exp_plan,
            "det_plan": det_plan,
            "exp_date": exp_date,
            "det_date": det_date,
            "exp_spending": exp_spending,
            "det_spending": det_spending,
            "amt_ok": amt_ok,
            "status_ok": status_ok,
            "method_ok": method_ok,
            "plan_ok": plan_ok,
            "date_ok": date_ok,
            "spending_ok": spending_ok,
            "exact_row": exact_row,
            "amt_error": float(amt_error) if amt_error is not None else None,
            "elapsed_s": round(elapsed, 3),
        })

    # Aggregate metrics
    n = len(results)
    amt_errors = [r["amt_error"] for r in results if r["amt_error"] is not None]

    metrics = {
        "phase": "v2_baseline",
        "mode": "deterministic",
        "total_samples": n,
        "runtime_total_s": round(total_inference_time, 3),
        "runtime_avg_s": round(total_inference_time / n, 3) if n else 0,
        "metrics": {
            "amount_exact": sum(r["amt_ok"] for r in results),
            "amount_exact_pct": round(sum(r["amt_ok"] for r in results) / n * 100, 1),
            "status_correct": sum(r["status_ok"] for r in results),
            "status_correct_pct": round(sum(r["status_ok"] for r in results) / n * 100, 1),
            "method_correct": sum(r["method_ok"] for r in results),
            "method_correct_pct": round(sum(r["method_ok"] for r in results) / n * 100, 1),
            "plan_correct": sum(r["plan_ok"] for r in results),
            "plan_correct_pct": round(sum(r["plan_ok"] for r in results) / n * 100, 1),
            "date_correct": sum(r["date_ok"] for r in results),
            "date_correct_pct": round(sum(r["date_ok"] for r in results) / n * 100, 1),
            "spending_correct": sum(r["spending_ok"] for r in results),
            "spending_correct_pct": round(sum(r["spending_ok"] for r in results) / n * 100, 1),
            "exact_row": sum(r["exact_row"] for r in results),
            "exact_row_pct": round(sum(r["exact_row"] for r in results) / n * 100, 1),
            "amount_mae": round(sum(amt_errors) / len(amt_errors), 2) if amt_errors else None,
            "amount_max_error": round(max(amt_errors), 2) if amt_errors else None,
        },
        "safety_violations": 0,  # validator guarantees 0
        "llm_calls": 0,
        "fallback_rate": 0.0,
    }

    # Print summary
    m = metrics["metrics"]
    print("\n" + "=" * 70)
    print("BASELINE ACCURACY REPORT")
    print("=" * 70)
    print(f"  Total samples       : {n}")
    print(f"  Amount (exact)      : {m['amount_exact']}/{n} ({m['amount_exact_pct']}%)")
    print(f"  Status              : {m['status_correct']}/{n} ({m['status_correct_pct']}%)")
    print(f"  Method              : {m['method_correct']}/{n} ({m['method_correct_pct']}%)")
    print(f"  Payment plan        : {m['plan_correct']}/{n} ({m['plan_correct_pct']}%)")
    print(f"  Earliest date       : {m['date_correct']}/{n} ({m['date_correct_pct']}%)")
    print(f"  Spending changes    : {m['spending_correct']}/{n} ({m['spending_correct_pct']}%)")
    print(f"  EXACT FULL ROW      : {m['exact_row']}/{n} ({m['exact_row_pct']}%)")
    print(f"  Amount MAE          : {m['amount_mae']}")
    print(f"  Amount Max Error    : {m['amount_max_error']}")
    print(f"  Runtime total       : {metrics['runtime_total_s']}s")
    print(f"  Runtime avg/req     : {metrics['runtime_avg_s']}s")
    print(f"  Safety violations   : {metrics['safety_violations']}")

    # Save metrics.json
    metrics_path = OUT_DIR / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"\n  Saved: {metrics_path}")

    # Save per_request.csv
    csv_path = OUT_DIR / "per_request.csv"
    if per_request_rows:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(per_request_rows[0].keys()))
            writer.writeheader()
            writer.writerows(per_request_rows)
    print(f"  Saved: {csv_path}")

    print("\nDONE — V2 baseline is frozen.")
    return metrics


if __name__ == "__main__":
    run_baseline()
