import json
from decimal import Decimal
from typing import List

from app.main import AffordabilityRequest, deterministic_pipeline

def evaluate_amount():
    mae_sum = Decimal("0.0")
    max_ae = Decimal("0.0")
    exact_match = 0
    total = 0
    
    results = []
    
    with open("evaluation/datasets/independent_benchmark.jsonl", "r") as f:
        for line in f:
            record = json.loads(line)
            req = AffordabilityRequest(**record)
            
            # we need the max safe amount from the engine.
            # deterministic_pipeline returns status and explanation containing safe_amount_today
            res = deterministic_pipeline(req)
            safe_amt = res.get("explanation").safe_amount_today
            expected = Decimal(str(record["expected_safe_amount"]))
            
            error = abs(safe_amt - expected)
            mae_sum += error
            max_ae = max(max_ae, error)
            
            if abs(error) < Decimal("0.01"):
                exact_match += 1
                
            total += 1
            
            results.append({
                "req_id": req.purchase.request_id,
                "expected": float(expected),
                "actual": float(safe_amt),
                "error": float(error)
            })
            
    print("=== Independent Amount Accuracy ===")
    print(f"Total scenarios: {total}")
    print(f"MAE: {mae_sum / total:.2f}")
    print(f"Max Absolute Error: {max_ae:.2f}")
    print(f"Exact Agreement: {exact_match}/{total} ({(exact_match/total)*100:.1f}%)")
    
    with open("evaluation/amount_accuracy_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    evaluate_amount()
