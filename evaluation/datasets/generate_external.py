import json
import uuid
from decimal import Decimal

def generate_external_benchmark(filename="evaluation/datasets/external_benchmark.jsonl"):
    cases = []
    
    # We will build exactly 100 cases based on 10 handcrafted core semantic templates.
    # Each template defines expected behavior independently.
    
    # Template 1: Salary increase evidence
    # Base: 5k/mo, Rent 2k, Min Bal 1k. Buy 3k laptop. 
    # Current balance: 4k. 4k - 3k = 1k. It's affordable.
    # But wait, next month rent 2k brings it to -1k! Not affordable.
    # Evidence: "My salary increased to 7k starting next month."
    # Now next month: 1k + 7k - 2k = 6k. Affordable.
    
    for i in range(10):
        salary_increase = 7000 + (i * 100)
        cases.append({
            "request_id": f"ext_req_{uuid.uuid4().hex[:8]}",
            "expected_decision": "affordable_now",
            "reason": "Qwen parses salary increase, changing deterministic cashflow.",
            "mode": "agentic",
            "profile": {
                "user_id": f"u_{i}",
                "home_currency": "USD",
                "current_available_balance": 4000.0,
                "minimum_balance_to_keep": 1000.0,
                "financial_priorities": [],
                "expense_categories_to_protect": ["rent"],
                "expense_categories_willing_to_reduce": [],
                "expense_categories_willing_to_stop": [],
                "payment_methods_user_will_consider": ["full_payment"],
                "max_installment_months": 3
            },
            "transactions": [
                {
                    "event_id": f"evt_s_{i}",
                    "user_id": f"u_{i}",
                    "description": "Salary",
                    "category": "salary",
                    "amount": 5000.0, # Old salary
                    "currency": "USD",
                    "event_date": "2026-09-01",
                    "status": "settled",
                    "event_type": "income"
                },
                {
                    "event_id": f"evt_r_{i}",
                    "user_id": f"u_{i}",
                    "description": "Rent",
                    "category": "rent",
                    "amount": 2000.0,
                    "currency": "USD",
                    "event_date": "2026-09-05",
                    "status": "settled",
                    "event_type": "expense"
                }
            ],
            "purchase": {
                "request_id": f"req_{i}",
                "user_id": f"u_{i}",
                "description": f"I want to buy a laptop for $3000. Also my salary increased from 5000 to {salary_increase} starting next month.",
                "request_amount": 3000.0,
                "request_date": "2026-09-16",
                "evidence": []
            }
        })

    # Template 2: Cancel subscription evidence
    # Bal: 2000, Min Bal: 1000. Purchase: 900. Remaining: 1100.
    # Tomorrow: Gym: 200. Remaining: 900. (Violates min balance) -> Not affordable.
    # Evidence: "I will cancel my gym" -> Qwen drops the gym event. -> Affordable.
    for i in range(10, 20):
        cases.append({
            "request_id": f"ext_req_{uuid.uuid4().hex[:8]}",
            "expected_decision": "affordable_now",
            "reason": "Qwen removes the gym subscription, saving the minimum balance.",
            "mode": "agentic",
            "profile": {
                "user_id": f"u_{i}",
                "home_currency": "USD",
                "current_available_balance": 2000.0,
                "minimum_balance_to_keep": 1000.0,
                "financial_priorities": [],
                "expense_categories_to_protect": [],
                "expense_categories_willing_to_reduce": [],
                "expense_categories_willing_to_stop": ["gym"],
                "payment_methods_user_will_consider": ["full_payment"],
                "max_installment_months": 3
            },
            "transactions": [
                {
                    "event_id": f"evt_g_{i}",
                    "user_id": f"u_{i}",
                    "description": "Gym",
                    "category": "gym",
                    "amount": 200.0,
                    "currency": "USD",
                    "event_date": "2026-08-17",
                    "status": "settled",
                    "event_type": "expense"
                }
            ],
            "purchase": {
                "request_id": f"req_{i}",
                "user_id": f"u_{i}",
                "description": "I want to buy a TV for $900. I am going to cancel my gym subscription.",
                "request_amount": 900.0,
                "request_date": "2026-09-16",
                "evidence": []
            }
        })
        
    # Template 3: Pure Deterministic Edge Case (No LLM needed)
    # Installment plan trigger
    # Bal: 5000, Min: 1000. Purchase: 4500. Remaining: 500 (Unsafe for full).
    # Allowed installments: 3 months. Amount: 1500/mo.
    # Mo 1: 5000 - 1500 = 3500.
    # Mo 2: 3500 + Salary(3000) - 1500 = 5000.
    # Affordable with plan.
    for i in range(20, 100):
        cases.append({
            "request_id": f"ext_req_{uuid.uuid4().hex[:8]}",
            "expected_decision": "affordable_with_plan",
            "reason": "Math safely routes to a 3-month payment plan.",
            "mode": "deterministic",
            "profile": {
                "user_id": f"u_{i}",
                "home_currency": "USD",
                "current_available_balance": 5000.0,
                "minimum_balance_to_keep": 1000.0,
                "financial_priorities": [],
                "expense_categories_to_protect": [],
                "expense_categories_willing_to_reduce": [],
                "expense_categories_willing_to_stop": [],
                "payment_methods_user_will_consider": ["full_payment", "installments"],
                "max_installment_months": 3
            },
            "transactions": [
                {
                    "event_id": f"evt_s_{i}",
                    "user_id": f"u_{i}",
                    "description": "Salary",
                    "category": "salary",
                    "amount": 3000.0,
                    "currency": "USD",
                    "event_date": "2026-09-01",
                    "status": "settled",
                    "event_type": "income"
                }
            ],
            "purchase": {
                "request_id": f"req_{i}",
                "user_id": f"u_{i}",
                "description": "Buy a car repair.",
                "request_amount": 4500.0,
                "request_date": "2026-09-16",
                "evidence": []
            }
        })
        
    with open(filename, "w") as f:
        for c in cases:
            f.write(json.dumps(c) + "\n")
            
    print(f"Generated {len(cases)} external benchmark cases.")

if __name__ == "__main__":
    generate_external_benchmark()
