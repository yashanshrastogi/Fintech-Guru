import json
import uuid
import random

def generate_realistic_dataset(filename="evaluation/datasets/holdout.jsonl", num_cases=100):
    cases = []
    
    # Base profiles
    profiles = [
        {
            "home_currency": "USD",
            "minimum_balance_to_keep": 1000.0,
            "financial_priorities": ["savings"],
            "expense_categories_to_protect": ["rent", "groceries"],
            "expense_categories_willing_to_reduce": ["dining"],
            "expense_categories_willing_to_stop": ["subscriptions"],
            "payment_methods_user_will_consider": ["full_payment", "installments"],
            "max_installment_months": 6
        },
        {
            "home_currency": "INR",
            "minimum_balance_to_keep": 10000.0,
            "financial_priorities": ["debt_repayment"],
            "expense_categories_to_protect": ["rent", "medical"],
            "expense_categories_willing_to_reduce": ["travel", "dining"],
            "expense_categories_willing_to_stop": ["entertainment"],
            "payment_methods_user_will_consider": ["full_payment"],
            "max_installment_months": 3
        }
    ]

    for _ in range(num_cases):
        prof = random.choice(profiles)
        currency = prof["home_currency"]
        multiplier = 1.0 if currency == "USD" else 80.0
        
        base_balance = random.uniform(2000, 5000) * multiplier
        salary = random.uniform(3000, 8000) * multiplier
        rent = random.uniform(800, 2000) * multiplier
        groceries = random.uniform(200, 600) * multiplier
        dining = random.uniform(100, 400) * multiplier
        
        user_id = f"usr_{uuid.uuid4().hex[:8]}"
        
        events = [
            {
                "event_id": f"evt_{uuid.uuid4().hex[:8]}",
                "user_id": user_id,
                "description": "Salary",
                "category": "salary",
                "amount": salary,
                "currency": currency,
                "event_date": "2023-10-01",
                "status": "settled",
                "event_type": "income"
            },
            {
                "event_id": f"evt_{uuid.uuid4().hex[:8]}",
                "user_id": user_id,
                "description": "Rent",
                "category": "rent",
                "amount": rent,
                "currency": currency,
                "event_date": "2023-10-05",
                "status": "settled",
                "event_type": "expense"
            },
            {
                "event_id": f"evt_{uuid.uuid4().hex[:8]}",
                "user_id": user_id,
                "description": "Groceries",
                "category": "groceries",
                "amount": groceries,
                "currency": currency,
                "event_date": "2023-10-10",
                "status": "settled",
                "event_type": "expense"
            },
            {
                "event_id": f"evt_{uuid.uuid4().hex[:8]}",
                "user_id": user_id,
                "description": "Dining",
                "category": "dining",
                "amount": dining,
                "currency": currency,
                "event_date": "2023-10-12",
                "status": "settled",
                "event_type": "expense"
            }
        ]
        
        purchase_amt = random.uniform(500, 3000) * multiplier
        
        req = {
            "mode": "agentic",
            "profile": {
                "user_id": user_id,
                **prof
            },
            "transactions": events,
            "purchase": {
                "request_id": f"req_{uuid.uuid4().hex[:8]}",
                "user_id": user_id,
                "description": "Realistic synthetic purchase",
                "request_amount": purchase_amt,
                "request_date": "2023-10-15",
                "evidence": []
            }
        }
        
        cases.append(req)
        
    with open(filename, "w") as f:
        for c in cases:
            f.write(json.dumps(c) + "\n")
            
    print(f"Generated {num_cases} cases in {filename}")

if __name__ == "__main__":
    generate_realistic_dataset()
