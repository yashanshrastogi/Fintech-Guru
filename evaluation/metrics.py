import json
import argparse
from pathlib import Path

def generate_telemetry(predictions_file: Path):
    with open(predictions_file, "r") as f:
        predictions = [json.loads(line) for line in f]
        
    total = len(predictions)
    safety_violations = 0
    affordable_now = 0
    affordable_with_plan = 0
    not_affordable = 0
    fallback_count = 0 # In this version, all multi_agent falls back to deterministic, so 100%
    latencies = []
    
    correct = 0
    total_with_expected = 0
    
    for p in predictions:
        status = p["decision"]["status"]
        expected = p.get("expected_decision", "unknown")
        
        # Check if the fallback meta was injected
        meta = p["decision"].get("explanation", {}).get("_meta", {})
        if isinstance(meta, dict) and meta.get("executed_as") == "deterministic_fallback":
            fallback_count += 1
            
        if expected != "unknown":
            total_with_expected += 1
            if status == expected:
                correct += 1
                
        if status == "affordable_now":
            affordable_now += 1
        elif status == "affordable_with_plan":
            affordable_with_plan += 1
        elif status == "not_affordable":
            not_affordable += 1
            
        latencies.append(p["latency_ms"])
        
        # Check safety violations (e.g. if status is affordable but safety margin < 0)
        margin = p["decision"]["safety_margin"]
        is_affordable = p["decision"]["is_affordable"]
        if is_affordable and margin < 0:
            safety_violations += 1
            
    latencies.sort()
    p50 = latencies[int(total * 0.5)] if total > 0 else 0
    p95 = latencies[int(total * 0.95)] if total > 0 else 0
    
    fallback_rate = (fallback_count / total * 100) if total > 0 else 0.0
    
    print("========================================")
    print("HOLDOUT EVALUATION METRICS")
    print("========================================")
    print(f"Total Requests: {total}")
    print(f"Safety Violations: {safety_violations}")
    print(f"Status Distribution: ")
    print(f"  - Affordable Now: {affordable_now} ({(affordable_now/total)*100:.1f}%)")
    print(f"  - Affordable with Plan: {affordable_with_plan} ({(affordable_with_plan/total)*100:.1f}%)")
    print(f"  - Not Affordable: {not_affordable} ({(not_affordable/total)*100:.1f}%)")
    print(f"p50 Latency: {p50:.2f} ms")
    print(f"p95 Latency: {p95:.2f} ms")
    print(f"Fallback Rate (Agentic -> Deterministic): {fallback_rate:.1f}%")
    if total_with_expected > 0:
        print(f"External Benchmark Accuracy: {correct}/{total_with_expected} ({(correct/total_with_expected)*100:.1f}%)")
    print("========================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True, type=Path)
    args = parser.parse_args()
    
    generate_telemetry(args.predictions)
