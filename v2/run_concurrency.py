"""
Phase 3: Concurrency test harness for Mode D (AUTO routing).

Tests Mode D at 1, 2, and 3 worker threads.
Measures:
  - Wall time, CPU%, RAM MB
  - Per-request latency (avg, p50, p95)
  - Timeout rate (requests exceeding 60s)
  - Inference stability (stdev of latency)
  - Throughput (requests/second)

Output:
  evaluation/phase3_experiment/concurrency_results.json

Usage:
  python v2/run_concurrency.py
"""
import sys
import os
import csv
import json
import time
import threading
import statistics
import psutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from decimal import Decimal
from typing import List, Dict, Tuple, Optional

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "code"))

os.environ["AGENTIC_MODE"] = "auto"
os.environ["USE_LLM_EXPLANATIONS"] = "false"
os.environ["USE_LLM_IMAGE_OCR"] = "false"

SAMPLE_CSV = REPO_ROOT / "dataset" / "sample_requests.csv"
OUT_DIR = REPO_ROOT / "evaluation" / "phase3_experiment"
OUT_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_TIMEOUT_S = 60


def load_samples():
    samples = {}
    with open(SAMPLE_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            samples[row["request_id"]] = row
    return samples


def process_one(req, store, fx, mode: str) -> Tuple[str, dict, float, int, bool]:
    """Process one request. Returns (request_id, row, latency_ms, llm_calls, fallback)."""
    from main import process_request, format_result_row

    t0 = time.perf_counter()
    try:
        result = process_request(req, store, fx, mode=mode)
        row = format_result_row(result)
        elapsed = (time.perf_counter() - t0) * 1000
        return req.request_id, row, elapsed, 0, False
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        return req.request_id, {
            "request_id": req.request_id,
            "amount_safe_to_pay": "0",
            "affordability_status": "not_affordable",
            "recommended_payment_method": "not_recommended",
            "payment_plan": "none",
            "earliest_date_for_full_payment": "",
            "spending_changes_needed": "none",
            "decision_explanation": f"ERROR: {e}",
        }, elapsed, 0, True


def run_concurrent(sample_requests, store, fx, n_workers: int, mode: str) -> dict:
    """Run all sample_requests with n_workers threads. Return timing + resource stats."""
    print(f"\n  Workers={n_workers} | Mode={mode}")

    proc = psutil.Process()
    cpu_samples = []
    ram_samples = []
    stop_monitor = threading.Event()

    def monitor():
        while not stop_monitor.is_set():
            try:
                cpu_samples.append(proc.cpu_percent(interval=0.5))
                ram_samples.append(proc.memory_info().rss / 1024 / 1024)
            except Exception:
                pass

    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()

    latencies = []
    timeout_count = 0
    error_count = 0

    t_wall_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = {
            executor.submit(process_one, req, store, fx, mode): req
            for req in sample_requests
        }
        for future in as_completed(futures, timeout=REQUEST_TIMEOUT_S * len(sample_requests)):
            try:
                rid, row, elapsed, _, fallback = future.result(timeout=REQUEST_TIMEOUT_S)
                latencies.append(elapsed)
                if fallback:
                    error_count += 1
                print(f"    {rid}: {elapsed:.1f}ms")
            except TimeoutError:
                timeout_count += 1
                print(f"    TIMEOUT")
            except Exception as e:
                error_count += 1
                print(f"    ERROR: {e}")

    t_wall = (time.perf_counter() - t_wall_start)
    stop_monitor.set()
    monitor_thread.join(timeout=2.0)

    n = len(latencies)
    lat_sorted = sorted(latencies)

    return {
        "workers": n_workers,
        "mode": mode,
        "total_requests": len(sample_requests),
        "completed": n,
        "timeout_count": timeout_count,
        "error_count": error_count,
        "wall_time_s": round(t_wall, 2),
        "throughput_req_per_s": round(n / t_wall, 2) if t_wall > 0 else 0,
        "latency_ms": {
            "avg": round(statistics.mean(latencies), 2) if latencies else 0,
            "p50": round(lat_sorted[n // 2], 2) if lat_sorted else 0,
            "p95": round(lat_sorted[min(int(n * 0.95), n - 1)], 2) if lat_sorted else 0,
            "max": round(max(latencies), 2) if latencies else 0,
            "stdev": round(statistics.stdev(latencies), 2) if n > 1 else 0,
        },
        "resource": {
            "cpu_pct_avg": round(statistics.mean(cpu_samples), 1) if cpu_samples else None,
            "cpu_pct_max": round(max(cpu_samples), 1) if cpu_samples else None,
            "ram_mb_avg": round(statistics.mean(ram_samples), 1) if ram_samples else None,
            "ram_mb_max": round(max(ram_samples), 1) if ram_samples else None,
        },
    }


def main():
    print("=" * 70)
    print("PHASE 3: CONCURRENCY TEST (Mode D — AUTO routing)")
    print("=" * 70)

    # Check Ollama
    import ollama_client
    ollama_ok, model = ollama_client.check_health()
    print(f"\n  Ollama: {ollama_ok} | model: {model}")
    mode = "auto" if ollama_ok else "deterministic"
    print(f"  Using mode: {mode} (fallback to deterministic if Ollama unavailable)")

    # Load data
    from data_loader import load_all_data
    from fx import get_fx_converter
    print("\nLoading data...")
    store = load_all_data()
    fx = get_fx_converter(store.exchange_rates_df)

    samples = load_samples()
    sample_requests = [r for r in store.sample_requests if r.request_id in samples]
    sample_requests.sort(key=lambda r: r.request_id)
    print(f"  Requests to test: {len(sample_requests)}")

    results = {}
    for n_workers in [1, 2, 3]:
        r = run_concurrent(sample_requests, store, fx, n_workers, mode)
        results[f"workers_{n_workers}"] = r

    # Save
    out_path = OUT_DIR / "concurrency_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved: {out_path}")

    # Summary
    print("\n" + "=" * 70)
    print("CONCURRENCY SUMMARY")
    print("=" * 70)
    print(f"  {'Workers':<10} {'Avg(ms)':<12} {'p50(ms)':<12} {'p95(ms)':<12} {'Throughput(r/s)':<18} {'CPU%':<10} {'RAM(MB)'}")
    print(f"  {'-'*80}")
    for k, r in results.items():
        lat = r["latency_ms"]
        res = r["resource"]
        print(f"  {r['workers']:<10} {lat['avg']:<12} {lat['p50']:<12} {lat['p95']:<12} "
              f"{r['throughput_req_per_s']:<18} {res.get('cpu_pct_avg','?'):<10} {res.get('ram_mb_avg','?')}")

    print("\nDONE.")
    return results


if __name__ == "__main__":
    main()
