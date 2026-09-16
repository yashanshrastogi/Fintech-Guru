import json
import statistics
from decimal import Decimal
import os
import sys

# Ensure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import deterministic_pipeline, AffordabilityRequest
from core.models import PurchaseRequest, UserProfile, IncomeEvent, ExpenseEvent, Balance, Account

def evaluate_dataset(filename):
    filepath = os.path.join('evaluation', 'datasets', filename)
    print(f"\n--- Evaluating {filename} ---")
    
    total = 0
    exact_matches = 0
    errors = []
    
    with open(filepath, 'r') as f:
        for i, line in enumerate(f):
            total += 1
            record = json.loads(line)
            req_data = record
            
            # Convert to AffordabilityRequest
            aff_req = AffordabilityRequest(**req_data)
            
            expected = Decimal(str(record['expected_safe_amount']))
            
            # Run production engine deterministic mode
            res = deterministic_pipeline(aff_req)
            actual = res['explanation'].safe_amount_today
            
            err = abs(actual - expected)
            errors.append(float(err))
            
            if abs(err) < Decimal("0.01"):
                exact_matches += 1
            else:
                print(f"Mismatch: Req {req_data['purchase']['request_id']} | Expected {expected} | Actual {actual} | Diff {err}")
                
            if i % 100 == 0 and i > 0:
                print(f"Processed {i}/{500}...")

    mae = sum(errors) / len(errors)
    sorted_errs = sorted(errors)
    median = statistics.median(sorted_errs)
    p95 = sorted_errs[int(len(sorted_errs) * 0.95)]
    max_err = max(errors)
    
    print(f"Agreement: {exact_matches}/{total} ({exact_matches/total*100:.1f}%)")
    print(f"MAE: ${mae:.2f}")
    print(f"Median AE: ${median:.2f}")
    print(f"P95 AE: ${p95:.2f}")
    print(f"Max AE: ${max_err:.2f}")

if __name__ == "__main__":
    evaluate_dataset("fresh_holdout_benchmark.jsonl")
    evaluate_dataset("anti_overfit_holdout.jsonl")
