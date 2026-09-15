"""
Phase 9: Full 250-request V1 vs V2 benchmark.

Runs the CURRENT codebase (V2 with Phase 1-6 improvements) in deterministic mode
on ALL 250 requests. For V1-equivalent mode, we re-run with V1 settings
(effectively disabling Phase 1 adaptive forecast by setting _FORCE_MEDIAN=true).

Ground-truth accuracy metrics are computed only on the 25 known samples.
Coverage metrics (latency, safety, row count) are computed on all 250.

Output:
  evaluation/v2_full_benchmark/
    v1_equivalent_results.csv      -- V1-mode run on all 250
    v2_results.csv                 -- V2-mode run on all 250
    accuracy_25samples.json        -- Accuracy on 25 known samples (both modes)
    latency_all250.json            -- Latency/safety metrics on all 250 (both modes)
    summary.md                     -- Human-readable comparison report
    traces/v1/                     -- Per-request trace JSONL (V1 mode)
    traces/v2/                     -- Per-request trace JSONL (V2 mode)

Usage:
  python v2/run_phase9.py
"""
import sys
import os
import csv
import json
import time
import statistics
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import date

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "code"))

os.environ["AGENTIC_MODE"] = "false"
os.environ["USE_LLM_EXPLANATIONS"] = "false"
os.environ["USE_LLM_IMAGE_OCR"] = "false"

OUT_DIR = REPO_ROOT / "evaluation" / "v2_full_benchmark"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TRACES_V1 = OUT_DIR / "traces" / "v1"
TRACES_V2 = OUT_DIR / "traces" / "v2"
TRACES_V1.mkdir(parents=True, exist_ok=True)
TRACES_V2.mkdir(parents=True, exist_ok=True)

SAMPLE_CSV = REPO_ROOT / "dataset" / "sample_requests.csv"

OUTPUT_COLS = [
    "request_id", "amount_safe_to_pay", "affordability_status",
    "recommended_payment_method", "payment_plan",
    "earliest_date_for_full_payment", "spending_changes_needed",
    "decision_explanation",
]


def load_samples() -> Dict[str, dict]:
    samples = {}
    with open(SAMPLE_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            samples[row["request_id"]] = row
    return samples


def parse_d(val) -> Optional[Decimal]:
    try:
        return Decimal(str(val).replace(",", "").strip())
    except Exception:
        return None


def compare_amount(exp: str, got: str) -> bool:
    e, g = parse_d(exp), parse_d(got)
    if e is None or g is None:
        return False
    if e == Decimal("0") and g == Decimal("0"):
        return True
    rel = abs(e - g) / abs(e) if e != 0 else (Decimal("1") if g != 0 else Decimal("0"))
    return rel < Decimal("0.005")


def is_safe(row: dict) -> bool:
    """Return False if this row has a safety violation."""
    amt = parse_d(row.get("amount_safe_to_pay", "0"))
    if amt is not None and amt < Decimal("0"):
        return False
    return True


def run_mode(
    store,
    fx,
    requests: list,
    mode_name: str,
    trace_dir: Path,
    force_median: bool = False,
) -> Tuple[List[dict], List[float]]:
    """
    Run the deterministic pipeline on all requests.

    Args:
        force_median: If True, patches reconciliation to use median-only (V1 behavior).
    Returns:
        (results_rows, latencies_ms)
    """
    from main import process_request, format_result_row
    from tracer import Tracer

    # V1-equivalent mode is controlled by the V2_FORCE_MEDIAN env var.
    # It is set by the caller (main()) before calling run_mode().
    # No module patching required — reconciliation.py reads the env var at call time.

    tracer = Tracer(run_id=mode_name, out_dir=trace_dir)

    results = []
    latencies = []

    for i, req in enumerate(requests):
        t0 = time.perf_counter()
        try:
            with tracer.trace(req.request_id, req.user_id, mode_name) as ctx:
                result = process_request(req, store, fx, mode="deterministic")
                row = format_result_row(result)
                ctx.set_result(row)
                results.append(row)
        except Exception as e:
            row = {
                "request_id": req.request_id,
                "amount_safe_to_pay": "0",
                "affordability_status": "not_affordable",
                "recommended_payment_method": "not_recommended",
                "payment_plan": "none",
                "earliest_date_for_full_payment": "",
                "spending_changes_needed": "none",
                "decision_explanation": f"ERROR: {e}",
            }
            results.append(row)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed_ms)

        if (i + 1) % 50 == 0:
            print(f"  [{mode_name}] {i+1}/{len(requests)} done "
                  f"(avg {statistics.mean(latencies):.1f}ms/req)")

    tracer.save_summary(trace_dir / f"summary_{mode_name}.json")
    return results, latencies


def _safe_str(v, default="") -> str:
    """Convert value to string, treating None/NaN/float-nan as empty string."""
    if v is None:
        return default
    s = str(v).strip()
    return default if s.lower() in ("nan", "none", "") else s


def compute_accuracy(results: List[dict], samples) -> dict:
    """
    Compute accuracy metrics on the 25 sample requests only.

    Args:
        results:  List of result dicts from the pipeline run.
        samples:  Either a dict of {request_id: gt_dict} from CSV,
                  or a dict from store.sample_outputs (same format).
    """
    # Normalize samples to dict-of-dicts
    if hasattr(samples, "items"):
        sample_dict = samples  # already a dict
    else:
        sample_dict = {s["request_id"]: s for s in samples}

    matched = {
        r["request_id"]: r
        for r in results
        if r["request_id"] in sample_dict
    }

    exact_count = status_ok = method_ok = plan_ok = date_ok = spending_ok = 0
    amt_errors = []
    n = len(sample_dict)

    for rid, gt in sample_dict.items():
        det = matched.get(rid)
        if det is None:
            continue

        exp_amt = _safe_str(gt.get("amount_safe_to_pay"))
        exp_status = _safe_str(gt.get("affordability_status"))
        exp_method = _safe_str(gt.get("recommended_payment_method"))
        exp_plan = _safe_str(gt.get("payment_plan"), "none")
        exp_date = _safe_str(gt.get("earliest_date_for_full_payment"))
        exp_spending = _safe_str(gt.get("spending_changes_needed"), "none")

        det_amt = _safe_str(det.get("amount_safe_to_pay"))
        det_status = _safe_str(det.get("affordability_status"))
        det_method = _safe_str(det.get("recommended_payment_method"))
        det_plan = _safe_str(det.get("payment_plan"), "none")
        det_date = _safe_str(det.get("earliest_date_for_full_payment"))
        det_spending = _safe_str(det.get("spending_changes_needed"), "none")

        a_ok = compare_amount(exp_amt, det_amt)
        s_ok = exp_status == det_status
        m_ok = exp_method == det_method
        p_ok = exp_plan == det_plan
        d_ok = exp_date == det_date
        sp_ok = exp_spending == det_spending

        if a_ok and s_ok and m_ok and p_ok and d_ok and sp_ok:
            exact_count += 1
        if s_ok: status_ok += 1
        if m_ok: method_ok += 1
        if p_ok: plan_ok += 1
        if d_ok: date_ok += 1
        if sp_ok: spending_ok += 1

        e_d = parse_d(exp_amt)
        g_d = parse_d(det_amt)
        if e_d is not None and g_d is not None:
            amt_errors.append(abs(e_d - g_d))

    return {
        "n_samples": n,
        "exact_row": exact_count,
        "exact_row_pct": round(exact_count / n * 100, 1) if n else 0,
        "status_correct": status_ok,
        "status_pct": round(status_ok / n * 100, 1) if n else 0,
        "method_correct": method_ok,
        "method_pct": round(method_ok / n * 100, 1) if n else 0,
        "plan_correct": plan_ok,
        "plan_pct": round(plan_ok / n * 100, 1) if n else 0,
        "date_correct": date_ok,
        "date_pct": round(date_ok / n * 100, 1) if n else 0,
        "spending_correct": spending_ok,
        "spending_pct": round(spending_ok / n * 100, 1) if n else 0,
        "amount_mae": round(float(sum(amt_errors) / len(amt_errors)), 2) if amt_errors else None,
        "amount_max_error": round(float(max(amt_errors)), 2) if amt_errors else None,
    }


def compute_coverage(results: List[dict], latencies: List[float]) -> dict:
    safety_violations = sum(1 for r in results if not is_safe(r))
    lat_sorted = sorted(latencies)
    n = len(lat_sorted)
    return {
        "total_requests": n,
        "safety_violations": safety_violations,
        "row_count_ok": n == 250,
        "latency_ms": {
            "avg": round(statistics.mean(latencies), 2),
            "p50": round(lat_sorted[n // 2], 2),
            "p95": round(lat_sorted[min(int(n * 0.95), n - 1)], 2),
            "min": round(min(latencies), 2),
            "max": round(max(latencies), 2),
            "stdev": round(statistics.stdev(latencies), 2) if n > 1 else 0.0,
        },
    }


def write_csv(results: List[dict], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_COLS)
        w.writeheader()
        for row in results:
            w.writerow({k: row.get(k, "") for k in OUTPUT_COLS})


def build_summary_md(v1_acc, v2_acc, v1_cov, v2_cov) -> str:
    def pct(d, k): return f"{d.get(k+'_pct', '?')}%"
    def val(d, k): return d.get(k, "?")

    lines = [
        "# Phase 9 — Full 250-Request Benchmark",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## Accuracy on 25 Ground-Truth Samples",
        "",
        "| Metric | V1-mode | V2-mode | Δ |",
        "|--------|---------|---------|---|",
    ]

    metrics = [
        ("Exact full-row", "exact_row", "exact_row_pct"),
        ("Status correct", "status_correct", "status_pct"),
        ("Method correct", "method_correct", "method_pct"),
        ("Plan correct", "plan_correct", "plan_pct"),
        ("Date correct", "date_correct", "date_pct"),
        ("Spending correct", "spending_correct", "spending_pct"),
    ]
    for label, key, pct_key in metrics:
        v1v = v1_acc.get(key, 0)
        v2v = v2_acc.get(key, 0)
        v1p = v1_acc.get(pct_key, 0)
        v2p = v2_acc.get(pct_key, 0)
        delta = f"{'+'if v2v >= v1v else ''}{v2v - v1v}"
        lines.append(f"| {label} | {v1v}/25 ({v1p}%) | {v2v}/25 ({v2p}%) | {delta} |")

    v1_mae = v1_acc.get("amount_mae", "?")
    v2_mae = v2_acc.get("amount_mae", "?")
    v1_max = v1_acc.get("amount_max_error", "?")
    v2_max = v2_acc.get("amount_max_error", "?")
    lines += [
        f"| Amount MAE | {v1_mae} | {v2_mae} | — |",
        f"| Amount Max Error | {v1_max} | {v2_max} | — |",
        "",
        "## Coverage on All 250 Requests",
        "",
        "| Metric | V1-mode | V2-mode |",
        "|--------|---------|---------|",
        f"| Safety violations | {v1_cov.get('safety_violations', '?')} | {v2_cov.get('safety_violations', '?')} |",
        f"| Row count | {v1_cov.get('total_requests', '?')} | {v2_cov.get('total_requests', '?')} |",
    ]

    for stat in ["avg", "p50", "p95"]:
        v1l = v1_cov.get("latency_ms", {}).get(stat, "?")
        v2l = v2_cov.get("latency_ms", {}).get(stat, "?")
        lines.append(f"| Latency {stat} (ms) | {v1l} | {v2l} |")

    lines += [
        "",
        "## Notes",
        "",
        "- V1-mode: deterministic pipeline with median-only forecast (V1 behavior)",
        "- V2-mode: deterministic pipeline with adaptive CV-based forecast (Phase 1 improvement)",
        "- No LLM calls in either mode (AGENTIC_MODE=false)",
        "- Safety violations = 0 in both modes is expected and required",
    ]

    return "\n".join(lines)


def main():
    print("=" * 70)
    print("PHASE 9: FULL 250-REQUEST V1 vs V2 BENCHMARK")
    print("=" * 70)

    # Load data (once)
    print("\nLoading data...")
    from data_loader import load_all_data
    from fx import get_fx_converter
    t0 = time.time()
    store = load_all_data()
    fx = get_fx_converter(store.exchange_rates_df)
    print(f"  Data loaded in {time.time()-t0:.1f}s")

    # The 250 competition requests (no ground truth — for coverage/latency only)
    all_250 = list(store.requests)
    # The 25 ground-truth sample requests (separate from the 250)
    sample_reqs = list(store.sample_requests)
    # Ground truth from store.sample_outputs (dict of request_id → output row)
    samples = getattr(store, "sample_outputs", {})
    if not samples:
        # Fallback: load from CSV
        samples = load_samples()
    print(f"  Total competition requests: {len(all_250)}")
    print(f"  Sample requests (ground truth): {len(sample_reqs)}")
    print(f"  Ground-truth entries: {len(samples)}")

    # --- V1-EQUIVALENT RUN (250 requests) ---
    print(f"\n[1/4] Running V1-equivalent mode on 250 requests (coverage metrics)...")
    os.environ["V2_FORCE_MEDIAN"] = "true"
    v1_results, v1_latencies = run_mode(
        store, fx, all_250,
        mode_name="v1_equivalent",
        trace_dir=TRACES_V1,
        force_median=False,
    )
    del os.environ["V2_FORCE_MEDIAN"]

    # --- V2 RUN (250 requests) ---
    print(f"\n[2/4] Running V2 mode on 250 requests (coverage metrics)...")
    v2_results, v2_latencies = run_mode(
        store, fx, all_250,
        mode_name="v2_deterministic",
        trace_dir=TRACES_V2,
        force_median=False,
    )

    # --- V1-EQUIVALENT RUN (25 samples) ---
    print(f"\n[3/4] Running V1-equivalent mode on 25 sample requests (accuracy metrics)...")
    os.environ["V2_FORCE_MEDIAN"] = "true"
    v1_sample_results, _ = run_mode(
        store, fx, sample_reqs,
        mode_name="v1_sample",
        trace_dir=TRACES_V1,
        force_median=False,
    )
    del os.environ["V2_FORCE_MEDIAN"]

    # --- V2 RUN (25 samples) ---
    print(f"\n[4/4] Running V2 mode on 25 sample requests (accuracy metrics)...")
    v2_sample_results, _ = run_mode(
        store, fx, sample_reqs,
        mode_name="v2_sample",
        trace_dir=TRACES_V2,
        force_median=False,
    )

    # --- SAVE CSVs ---
    v1_csv = OUT_DIR / "v1_equivalent_results.csv"
    v2_csv = OUT_DIR / "v2_results.csv"
    write_csv(v1_results, v1_csv)
    write_csv(v2_results, v2_csv)
    write_csv(v1_sample_results, OUT_DIR / "v1_sample_results.csv")
    write_csv(v2_sample_results, OUT_DIR / "v2_sample_results.csv")
    print(f"\n  Saved: {v1_csv}")
    print(f"  Saved: {v2_csv}")

    # --- ACCURACY (25 samples) ---
    v1_acc = compute_accuracy(v1_sample_results, samples)
    v2_acc = compute_accuracy(v2_sample_results, samples)

    accuracy = {"v1_equivalent": v1_acc, "v2_deterministic": v2_acc}
    acc_path = OUT_DIR / "accuracy_25samples.json"
    with open(acc_path, "w") as f:
        json.dump(accuracy, f, indent=2)
    print(f"  Saved: {acc_path}")

    # --- COVERAGE (250 requests) ---
    v1_cov = compute_coverage(v1_results, v1_latencies)
    v2_cov = compute_coverage(v2_results, v2_latencies)

    coverage = {"v1_equivalent": v1_cov, "v2_deterministic": v2_cov}
    cov_path = OUT_DIR / "latency_all250.json"
    with open(cov_path, "w") as f:
        json.dump(coverage, f, indent=2)
    print(f"  Saved: {cov_path}")

    # --- SUMMARY REPORT ---
    summary_md = build_summary_md(v1_acc, v2_acc, v1_cov, v2_cov)
    md_path = OUT_DIR / "summary.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(summary_md)
    print(f"  Saved: {md_path}")

    # --- PRINT SUMMARY ---
    print("\n" + "=" * 70)
    print("PHASE 9 RESULTS")
    print("=" * 70)
    print(f"\nACCURACY (25 samples):")
    print(f"  {'Metric':<25} {'V1-mode':>12} {'V2-mode':>12}")
    print(f"  {'-'*50}")
    for label, k, pk in [
        ("Exact full-row", "exact_row", "exact_row_pct"),
        ("Status correct", "status_correct", "status_pct"),
        ("Method correct", "method_correct", "method_pct"),
        ("Amount MAE", "amount_mae", None),
        ("Amount Max Error", "amount_max_error", None),
    ]:
        v1v = v1_acc.get(k, "?")
        v2v = v2_acc.get(k, "?")
        if pk:
            print(f"  {label:<25} {str(v1v)+'/25':>12} {str(v2v)+'/25':>12}")
        else:
            print(f"  {label:<25} {str(v1v):>12} {str(v2v):>12}")

    print(f"\nCOVERAGE (250 competition requests):")
    print(f"  Safety violations V1: {v1_cov['safety_violations']}")
    print(f"  Safety violations V2: {v2_cov['safety_violations']}")
    print(f"  Latency avg V1: {v1_cov['latency_ms']['avg']}ms")
    print(f"  Latency avg V2: {v2_cov['latency_ms']['avg']}ms")
    print(f"  Latency p95 V1: {v1_cov['latency_ms']['p95']}ms")
    print(f"  Latency p95 V2: {v2_cov['latency_ms']['p95']}ms")

    print("\nDONE.")


if __name__ == "__main__":
    main()
