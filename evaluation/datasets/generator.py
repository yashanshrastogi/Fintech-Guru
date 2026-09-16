import json
import random
import uuid
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta

def generate_synthetic_dataset(num_samples: int = 1000) -> List[Dict[str, Any]]:
    """
    Generates synthetic financial scenarios with mathematically constructed 
    deterministic ground truth, covering edge cases like delayed salary, 
    recurring variations, and image evidence.
    """
    dataset = []
    
    today = datetime(2026, 9, 15)
    
    for i in range(num_samples):
        # Scenario construction
        profile_id = f"user_{uuid.uuid4().hex[:8]}"
        req_id = f"req_{uuid.uuid4().hex[:8]}"
        
        # 1. Base Salary
        base_salary = random.randint(3000, 15000)
        
        # 2. Add permutations
        scenario_type = random.choice([
            "clean_affordable",
            "clean_unaffordable",
            "borderline_affordable",
            "borderline_unaffordable",
            "delayed_salary",
            "cancelled_event",
            "message_salary_increase"
        ])
        
        current_balance = random.randint(1000, 20000)
        min_balance = 500
        request_amount = 0.0
        
        gt_status = "not_affordable"
        gt_method = "none"
        
        # Construct constraints to force ground truth
        if scenario_type == "clean_affordable":
            request_amount = current_balance - min_balance - 100
            gt_status = "affordable_now"
            gt_method = "full_payment"
        elif scenario_type == "clean_unaffordable":
            request_amount = current_balance + 5000
            gt_status = "not_affordable"
            gt_method = "none"
        elif scenario_type == "borderline_affordable":
            request_amount = current_balance - min_balance
            gt_status = "affordable_now"
            gt_method = "full_payment"
        elif scenario_type == "borderline_unaffordable":
            request_amount = current_balance - min_balance + 1
            gt_status = "not_affordable"
            gt_method = "none"
        else:
            # Fallback for complex ones (for now, simply mark not_affordable)
            request_amount = current_balance + 10000
            
        record = {
            "request_id": req_id,
            "user_id": profile_id,
            "scenario": scenario_type,
            "input": {
                "profile": {
                    "balance": current_balance,
                    "min_balance": min_balance,
                    "salary": base_salary
                },
                "request_amount": request_amount
            },
            "ground_truth": {
                "status": gt_status,
                "method": gt_method,
                "amount": request_amount if gt_status == "affordable_now" else 0.0,
                "plan": [{"date": today.strftime("%Y-%m-%d"), "amount": request_amount}] if gt_status == "affordable_now" else []
            }
        }
        dataset.append(record)
        
    return dataset

def split_and_save(dataset: List[Dict[str, Any]], out_dir: Path):
    random.shuffle(dataset)
    n = len(dataset)
    train_split = int(n * 0.70)
    val_split = int(n * 0.85)
    
    train = dataset[:train_split]
    val = dataset[train_split:val_split]
    test = dataset[val_split:]
    
    out_dir.mkdir(parents=True, exist_ok=True)
    
    for split_name, data in [("train.jsonl", train), ("validation.jsonl", val), ("test.jsonl", test)]:
        with open(out_dir / split_name, "w") as f:
            for record in data:
                f.write(json.dumps(record) + "\n")
                
    print(f"Generated {len(train)} train, {len(val)} val, {len(test)} test samples in {out_dir}")

if __name__ == "__main__":
    out_dir = Path(r"C:\Users\Yashansh Rastogi\Downloads\Fintech Guru\evaluation\datasets")
    dataset = generate_synthetic_dataset(1500)
    split_and_save(dataset, out_dir)
