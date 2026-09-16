import json
import argparse
from pathlib import Path

def run_baseline(dataset_file: Path, output_file: Path):
    """
    Runs a naive baseline to test the evaluation pipeline.
    It simply checks if current_balance - min_balance >= request_amount.
    """
    with open(dataset_file, "r") as f:
        dataset = [json.loads(line) for line in f]
        
    predictions = []
    for record in dataset:
        req_id = record["request_id"]
        inp = record["input"]
        bal = inp["profile"]["balance"]
        min_bal = inp["profile"]["min_balance"]
        amt = inp["request_amount"]
        
        available = bal - min_bal
        if available >= amt:
            status = "affordable_now"
            method = "full_payment"
            plan_amt = amt
        else:
            status = "not_affordable"
            method = "none"
            plan_amt = 0.0
            
        predictions.append({
            "request_id": req_id,
            "status": status,
            "method": method,
            "amount": plan_amt,
            "plan": [{"date": "2026-09-15", "amount": plan_amt}] if status == "affordable_now" else [],
            "safety_violations": 0,
            "fallback": False,
            "llm_calls": 0,
            "latency_ms": 1.5
        })
        
    with open(output_file, "w") as f:
        for p in predictions:
            f.write(json.dumps(p) + "\n")
            
    print(f"Generated {len(predictions)} baseline predictions at {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    
    run_baseline(args.dataset, args.out)
