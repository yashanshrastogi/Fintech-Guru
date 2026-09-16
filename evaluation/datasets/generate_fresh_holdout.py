import json
import uuid
import random
from decimal import Decimal
from datetime import date, timedelta
from typing import List, Dict

# Reuse the independent reference solver
from generate_independent_benchmark import generate_reference_safe_amount

def generate_holdout_dataset(num_cases=500, seed=42, output_file="fresh_holdout_benchmark.jsonl"):
    random.seed(seed) # Deterministic seed for reproducibility
    records = []
    
    req_date = date(2026, 9, 15)
    
    for i in range(num_cases):
        req_amt = random.randint(50, 5000)
        balance = random.randint(100, 10000)
        min_balance = random.randint(0, min(balance, 1000))
        
        num_incomes = random.randint(0, 2)
        incomes = []
        for _ in range(num_incomes):
            incomes.append({
                "amount": random.randint(1000, 5000),
                "frequency_days": random.choice([14, 15, 30]),
                "start_date": req_date - timedelta(days=random.randint(0, 30))
            })
            
        num_expenses = random.randint(0, 5)
        expenses = []
        for _ in range(num_expenses):
            expenses.append({
                "amount": random.randint(100, 1500),
                "frequency_days": random.choice([7, 14, 30, 365]),
                "start_date": req_date - timedelta(days=random.randint(0, 365))
            })
            
        safe_amt = generate_reference_safe_amount(
            Decimal(str(req_amt)), Decimal(str(balance)), Decimal(str(min_balance)), req_date,
            incomes, expenses
        )
        
        def get_prev_month_date(last_date: date, anchor_day: int) -> date:
            y, m = last_date.year, last_date.month
            m -= 1
            if m < 1:
                m = 12
                y -= 1
            next_month_1st = date(y + (m // 12), (m % 12) + 1, 1) if m < 12 else date(y + 1, 1, 1)
            max_day = (next_month_1st - timedelta(days=1)).day
            return date(y, m, min(anchor_day, max_day))

        transactions = []
        # Build 3 history periods for incomes
        for idx, inc in enumerate(incomes):
            d = inc["start_date"]
            anchor = d.day
            for j in range(3):
                transactions.append({
                    "event_id": str(uuid.uuid4()), "user_id": "u1", "description": "salary", "category": f"salary_{idx}",
                    "amount": inc["amount"], "event_date": d.isoformat(), "status": "settled", "event_type": "income", "is_salary": True, "source": "Emp"
                })
                if inc["frequency_days"] == 30:
                    d = get_prev_month_date(d, anchor)
                else:
                    d = d - timedelta(days=inc["frequency_days"])
        
        # Build 3 history periods for expenses
        for idx, exp in enumerate(expenses):
            d = exp["start_date"]
            anchor = d.day
            for j in range(3):
                transactions.append({
                    "event_id": str(uuid.uuid4()), "user_id": "u1", "description": "bill", "category": f"bill_{idx}",
                    "amount": exp["amount"], "event_date": d.isoformat(), "status": "settled", "event_type": "expense", "flexibility": "fixed"
                })
                if exp["frequency_days"] == 30:
                    d = get_prev_month_date(d, anchor)
                else:
                    d = d - timedelta(days=exp["frequency_days"])
                
        record = {
            "mode": "deterministic",
            "profile": {
                "user_id": "u1",
                "home_currency": "USD",
                "current_available_balance": balance,
                "minimum_balance_to_keep": min_balance,
                "financial_priorities": [],
                "expense_categories_to_protect": [],
                "expense_categories_willing_to_reduce": [],
                "expense_categories_willing_to_stop": [],
                "payment_methods_user_will_consider": [],
                "max_installment_months": 3
            },
            "transactions": transactions,
            "purchase": {
                "request_id": f"holdout_{i}",
                "user_id": "u1",
                "description": "Holdout benchmark",
                "request_amount": req_amt,
                "request_date": req_date.isoformat()
            },
            "expected_safe_amount": float(safe_amt)
        }
        records.append(record)
        
    import os
    out_path = os.path.join(os.path.dirname(__file__), output_file)
    with open(out_path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"Generated {output_file}")

if __name__ == "__main__":
    generate_holdout_dataset(500, seed=42, output_file="fresh_holdout_benchmark.jsonl")
    generate_holdout_dataset(500, seed=999, output_file="anti_overfit_holdout.jsonl")
