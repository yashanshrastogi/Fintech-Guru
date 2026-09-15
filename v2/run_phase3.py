"""
Phase 3: Four-mode agent experiment on 25 ground-truth samples.

Modes:
  A = deterministic (no LLM)
  B = evidence_only  (Qwen extracts message facts → deterministic engine)
  C = multi_agent    (Qwen reviews borderline candidates)
  D = auto           (easy → A, hard/ambiguous → B)

Measures per mode:
  - exact-match rate, status accuracy, amount MAE, method accuracy
  - safety violations (must be 0)
  - fallback rate
  - avg latency, p95 latency
  - model calls/request

Output:
  evaluation/phase3_experiment/
    mode_A_results.csv
    mode_B_results.csv
    mode_C_results.csv
    mode_D_results.csv
    metrics.json
    traces/

Usage:
  python v2/run_phase3.py
  python v2/run_phase3.py --skip-llm   (runs only mode A if Ollama unavailable)
"""
import sys
import os
import csv
import json
import time
import argparse
import statistics
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "code"))

os.environ["USE_LLM_EXPLANATIONS"] = "false"
os.environ["USE_LLM_IMAGE_OCR"] = "false"

SAMPLE_CSV = REPO_ROOT / "dataset" / "sample_requests.csv"
OUT_DIR = REPO_ROOT / "evaluation" / "phase3_experiment"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TRACES_DIR = OUT_DIR / "traces"
TRACES_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_COLS = [
    "request_id", "amount_safe_to_pay", "affordability_status",
    "recommended_payment_method", "payment_plan",
    "earliest_date_for_full_payment", "spending_changes_needed",
    "decision_explanation",
]


def _check_ollama() -> tuple:
    """Check if Ollama is available. Returns (ok: bool, model: str)."""
    from ollama_client import ollama_client as oc
    return oc.check_health()


# ---------------------------------------------------------------------------
# Helpers shared with Phase 9
# ---------------------------------------------------------------------------

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
    amt = parse_d(row.get("amount_safe_to_pay", "0"))
    return amt is not None and amt >= Decimal("0")


def compute_metrics(results: List[dict], latencies: List[float],
                    llm_calls_list: List[int], fallback_list: List[bool],
                    samples: Dict[str, dict]) -> dict:
    n = len(results)
    result_map = {r["request_id"]: r for r in results}

    exact = status_ok = method_ok = 0
    amt_errors = []

    for rid, gt in samples.items():
        det = result_map.get(rid, {})
        if not det:
            continue

        exp_amt = gt.get("amount_safe_to_pay", "")
        exp_status = gt.get("affordability_status", "").strip()
        exp_method = gt.get("recommended_payment_method", "").strip()

        det_amt = det.get("amount_safe_to_pay", "")
        det_status = det.get("affordability_status", "").strip()
        det_method = det.get("recommended_payment_method", "").strip()

        a_ok = compare_amount(exp_amt, det_amt)
        s_ok = exp_status == det_status
        m_ok = exp_method == det_method

        if s_ok:
            status_ok += 1
        if m_ok:
            method_ok += 1

        e_d = parse_d(exp_amt)
        g_d = parse_d(det_amt)
        if e_d is not None and g_d is not None:
            amt_errors.append(abs(e_d - g_d))

        # Exact full row
        exp_plan = (gt.get("payment_plan") or "none").strip()
        exp_date = (gt.get("earliest_date_for_full_payment") or "").strip()
        exp_spending = (gt.get("spending_changes_needed") or "none").strip()
        det_plan = (det.get("payment_plan") or "none").strip()
        det_date = (det.get("earliest_date_for_full_payment") or "").strip()
        det_spending = (det.get("spending_changes_needed") or "none").strip()

        if (a_ok and s_ok and m_ok and
                exp_plan == det_plan and
                exp_date == det_date and
                exp_spending == det_spending):
            exact += 1

    safety_violations = sum(1 for r in results if not is_safe(r))
    fallback_count = sum(1 for f in fallback_list if f)
    lat_sorted = sorted(latencies)

    return {
        "n": n,
        "exact_row": exact,
        "exact_row_pct": round(exact / n * 100, 1) if n else 0,
        "status_correct": status_ok,
        "status_pct": round(status_ok / n * 100, 1) if n else 0,
        "method_correct": method_ok,
        "method_pct": round(method_ok / n * 100, 1) if n else 0,
        "amount_mae": round(float(sum(amt_errors) / len(amt_errors)), 2) if amt_errors else None,
        "amount_max_error": round(float(max(amt_errors)), 2) if amt_errors else None,
        "safety_violations": safety_violations,
        "fallback_count": fallback_count,
        "fallback_rate": round(fallback_count / n, 4) if n else 0,
        "avg_llm_calls_per_req": round(sum(llm_calls_list) / n, 3) if n else 0,
        "latency_ms": {
            "avg": round(statistics.mean(latencies), 2) if latencies else 0,
            "p50": round(lat_sorted[n // 2], 2) if lat_sorted else 0,
            "p95": round(lat_sorted[min(int(n * 0.95), n - 1)], 2) if lat_sorted else 0,
            "max": round(max(latencies), 2) if latencies else 0,
        },
    }


def write_csv(results: List[dict], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_COLS)
        w.writeheader()
        for row in results:
            w.writerow({k: row.get(k, "") for k in OUTPUT_COLS})


# ---------------------------------------------------------------------------
# Mode A: Deterministic
# ---------------------------------------------------------------------------

def run_mode_a(sample_requests, store, fx, samples) -> Tuple[dict, List[dict]]:
    """Mode A: Pure deterministic, no LLM. AGENTIC_MODE=false."""
    from main import process_request, format_result_row
    from tracer import Tracer

    os.environ["AGENTIC_MODE"] = "false"
    tracer = Tracer("mode_A", TRACES_DIR)
    results, latencies, llm_calls_list, fallback_list = [], [], [], []

    for req in sample_requests:
        t0 = time.perf_counter()
        with tracer.trace(req.request_id, req.user_id, "deterministic") as ctx:
            result = process_request(req, store, fx, mode="deterministic")
            row = format_result_row(result)
            ctx.set_result(row)
        elapsed = (time.perf_counter() - t0) * 1000
        results.append(row)
        latencies.append(elapsed)
        llm_calls_list.append(0)
        fallback_list.append(False)
        print(f"  [A] {req.request_id}: {row['affordability_status']} | {elapsed:.1f}ms")

    metrics = compute_metrics(results, latencies, llm_calls_list, fallback_list, samples)
    metrics["mode"] = "A_deterministic"
    write_csv(results, OUT_DIR / "mode_A_results.csv")
    tracer.save_summary(OUT_DIR / "traces" / "mode_A_summary.json")
    return metrics, results


# ---------------------------------------------------------------------------
# Mode B: Evidence extraction only (Qwen message facts → deterministic engine)
# ---------------------------------------------------------------------------

def run_mode_b(sample_requests, store, fx, samples, ollama_ok: bool) -> Tuple[dict, List[dict]]:
    """Mode B: LLM interprets messages → structured facts → deterministic calculation."""
    from main import process_request, format_result_row
    from tracer import Tracer

    # Mode B: use auto mode so the pipeline runs Qwen message interpretation
    # when Ollama is available. When unavailable, falls back deterministically
    # and fallback_rate is reported honestly.
    os.environ["AGENTIC_MODE"] = "auto" if ollama_ok else "false"
    os.environ["USE_LLM_EXPLANATIONS"] = "false"

    tracer = Tracer("mode_B", TRACES_DIR)
    results, latencies, llm_calls_list, fallback_list = [], [], [], []

    for req in sample_requests:
        t0 = time.perf_counter()
        call_count = 0
        fallback = False
        try:
            with tracer.trace(req.request_id, req.user_id, "evidence_only") as ctx:
                result = process_request(req, store, fx, mode="auto")
                row = format_result_row(result)
                ctx.set_result(row)
                # Count LLM calls from tracer
                call_count = len(ctx.record.llm_calls)
                fallback = ctx.record.fallback_triggered
        except Exception as e:
            from main import format_result_row as fmt
            from models import DecisionResult
            from config import NOT_AFFORDABLE, NOT_RECOMMENDED
            row = {
                "request_id": req.request_id,
                "amount_safe_to_pay": "0",
                "affordability_status": NOT_AFFORDABLE,
                "recommended_payment_method": NOT_RECOMMENDED,
                "payment_plan": "none",
                "earliest_date_for_full_payment": "",
                "spending_changes_needed": "none",
                "decision_explanation": f"ERROR: {e}",
            }
            fallback = True

        elapsed = (time.perf_counter() - t0) * 1000
        results.append(row)
        latencies.append(elapsed)
        llm_calls_list.append(call_count)
        fallback_list.append(fallback or not ollama_ok)
        print(f"  [B] {req.request_id}: {row['affordability_status']} | {elapsed:.1f}ms "
              f"| llm_calls={call_count} | fallback={fallback}")

    os.environ["AGENTIC_MODE"] = "false"
    metrics = compute_metrics(results, latencies, llm_calls_list, fallback_list, samples)
    metrics["mode"] = "B_evidence_only"
    metrics["ollama_available"] = ollama_ok
    write_csv(results, OUT_DIR / "mode_B_results.csv")
    tracer.save_summary(OUT_DIR / "traces" / "mode_B_summary.json")
    return metrics, results


# ---------------------------------------------------------------------------
# Mode C: Multi-agent review (Qwen reviews borderline candidates)
# ---------------------------------------------------------------------------

def run_mode_c(sample_requests, store, fx, samples, ollama_ok: bool) -> Tuple[dict, List[dict]]:
    """Mode C: LLM reviews candidate plans for borderline/ambiguous cases."""
    from main import process_request, format_result_row
    from tracer import Tracer

    if ollama_ok:
        os.environ["AGENTIC_MODE"] = "agentic"
    else:
        os.environ["AGENTIC_MODE"] = "false"

    tracer = Tracer("mode_C", TRACES_DIR)
    results, latencies, llm_calls_list, fallback_list = [], [], [], []

    for req in sample_requests:
        t0 = time.perf_counter()
        call_count = 0
        fallback = not ollama_ok
        try:
            with tracer.trace(req.request_id, req.user_id, "multi_agent") as ctx:
                result = process_request(req, store, fx, mode="agentic" if ollama_ok else "deterministic")
                row = format_result_row(result)
                ctx.set_result(row)
                call_count = len(ctx.record.llm_calls)
                fallback = ctx.record.fallback_triggered or not ollama_ok
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
            fallback = True

        elapsed = (time.perf_counter() - t0) * 1000
        results.append(row)
        latencies.append(elapsed)
        llm_calls_list.append(call_count)
        fallback_list.append(fallback)
        print(f"  [C] {req.request_id}: {row['affordability_status']} | {elapsed:.1f}ms "
              f"| llm_calls={call_count} | fallback={fallback}")

    os.environ["AGENTIC_MODE"] = "false"
    metrics = compute_metrics(results, latencies, llm_calls_list, fallback_list, samples)
    metrics["mode"] = "C_multi_agent"
    metrics["ollama_available"] = ollama_ok
    write_csv(results, OUT_DIR / "mode_C_results.csv")
    tracer.save_summary(OUT_DIR / "traces" / "mode_C_summary.json")
    return metrics, results


# ---------------------------------------------------------------------------
# Mode D: AUTO routing (easy → A, hard → B)
# ---------------------------------------------------------------------------

def run_mode_d(sample_requests, store, fx, samples, ollama_ok: bool) -> Tuple[dict, List[dict]]:
    """Mode D: Auto routing — easy cases deterministic, ambiguous cases use evidence extraction."""
    from main import process_request, format_result_row
    from tracer import Tracer

    os.environ["AGENTIC_MODE"] = "auto"
    tracer = Tracer("mode_D", TRACES_DIR)
    results, latencies, llm_calls_list, fallback_list = [], [], [], []

    for req in sample_requests:
        t0 = time.perf_counter()
        call_count = 0
        fallback = False
        try:
            with tracer.trace(req.request_id, req.user_id, "auto") as ctx:
                result = process_request(req, store, fx, mode="auto")
                row = format_result_row(result)
                ctx.set_result(row)
                call_count = len(ctx.record.llm_calls)
                fallback = ctx.record.fallback_triggered or not ollama_ok
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
            fallback = True

        elapsed = (time.perf_counter() - t0) * 1000
        results.append(row)
        latencies.append(elapsed)
        llm_calls_list.append(call_count)
        fallback_list.append(fallback)
        print(f"  [D] {req.request_id}: {row['affordability_status']} | {elapsed:.1f}ms "
              f"| llm_calls={call_count} | fallback={fallback}")

    os.environ["AGENTIC_MODE"] = "false"
    metrics = compute_metrics(results, latencies, llm_calls_list, fallback_list, samples)
    metrics["mode"] = "D_auto"
    metrics["ollama_available"] = ollama_ok
    write_csv(results, OUT_DIR / "mode_D_results.csv")
    tracer.save_summary(OUT_DIR / "traces" / "mode_D_summary.json")
    return metrics, results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-llm", action="store_true",
                        help="Skip modes B/C/D if Ollama is unavailable")
    args = parser.parse_args()

    print("=" * 70)
    print("PHASE 3: FOUR-MODE AGENT EXPERIMENT ON 25 GROUND-TRUTH SAMPLES")
    print("=" * 70)

    # Check Ollama
    ollama_ok, detected_model = _check_ollama()
    print(f"\n  Ollama available: {ollama_ok}")
    print(f"  Detected model:   {detected_model}")
    if not ollama_ok:
        print("  WARNING: Ollama unavailable. Modes B/C/D will run with 100% fallback.")
        if args.skip_llm:
            print("  --skip-llm set: will only run Mode A.")

    # Load data
    from data_loader import load_all_data
    from fx import get_fx_converter
    print("\nLoading data...")
    store = load_all_data()
    fx = get_fx_converter(store.exchange_rates_df)

    samples = load_samples()
    # store.sample_requests = the 25 ground-truth sample requests (request_01..request_25)
    # store.requests = the 250 competition requests (request_26..request_275, no ground truth)
    sample_requests = list(store.sample_requests)
    sample_requests.sort(key=lambda r: r.request_id)
    print(f"  Sample requests: {len(sample_requests)}")

    all_metrics = {}

    # --- MODE A ---
    print(f"\n{'='*60}")
    print("MODE A: DETERMINISTIC (no LLM)")
    print(f"{'='*60}")
    m_a, r_a = run_mode_a(sample_requests, store, fx, samples)
    all_metrics["A_deterministic"] = m_a
    _print_mode_summary("A", m_a)

    if not args.skip_llm or ollama_ok:
        # --- MODE B ---
        print(f"\n{'='*60}")
        print(f"MODE B: EVIDENCE EXTRACTION ONLY (ollama={ollama_ok})")
        print(f"{'='*60}")
        m_b, r_b = run_mode_b(sample_requests, store, fx, samples, ollama_ok)
        all_metrics["B_evidence_only"] = m_b
        _print_mode_summary("B", m_b)

        # --- MODE C ---
        print(f"\n{'='*60}")
        print(f"MODE C: MULTI-AGENT REVIEW (ollama={ollama_ok})")
        print(f"{'='*60}")
        m_c, r_c = run_mode_c(sample_requests, store, fx, samples, ollama_ok)
        all_metrics["C_multi_agent"] = m_c
        _print_mode_summary("C", m_c)

        # --- MODE D ---
        print(f"\n{'='*60}")
        print(f"MODE D: AUTO ROUTING (ollama={ollama_ok})")
        print(f"{'='*60}")
        m_d, r_d = run_mode_d(sample_requests, store, fx, samples, ollama_ok)
        all_metrics["D_auto"] = m_d
        _print_mode_summary("D", m_d)
    else:
        print("\n  --skip-llm: Skipping modes B, C, D.")
        for mode in ["B_evidence_only", "C_multi_agent", "D_auto"]:
            all_metrics[mode] = {"skipped": True, "reason": "skip_llm_flag_and_ollama_unavailable"}

    # Save metrics
    metrics_path = OUT_DIR / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, indent=2, default=str)
    print(f"\n  Saved: {metrics_path}")

    print("\n" + "=" * 70)
    print("PHASE 3 COMPLETE — See evaluation/phase3_agent_experiment.md for report")
    print("=" * 70)
    return all_metrics


def _print_mode_summary(label: str, m: dict) -> None:
    if m.get("skipped"):
        print(f"\n  [Mode {label}] SKIPPED: {m.get('reason', '?')}")
        return
    print(f"\n  [Mode {label}] Results:")
    print(f"    Exact row:    {m.get('exact_row', '?')}/25 ({m.get('exact_row_pct', '?')}%)")
    print(f"    Status:       {m.get('status_correct', '?')}/25 ({m.get('status_pct', '?')}%)")
    print(f"    Method:       {m.get('method_correct', '?')}/25 ({m.get('method_pct', '?')}%)")
    print(f"    Amount MAE:   {m.get('amount_mae', '?')}")
    print(f"    Safety viol:  {m.get('safety_violations', '?')}")
    print(f"    Fallback:     {m.get('fallback_count', '?')}/{m.get('n', '?')} ({m.get('fallback_rate', '?')*100:.1f}%)")
    print(f"    LLM calls/r:  {m.get('avg_llm_calls_per_req', '?')}")
    lat = m.get("latency_ms", {})
    print(f"    Latency avg:  {lat.get('avg', '?')}ms  p95={lat.get('p95', '?')}ms")


if __name__ == "__main__":
    main()
