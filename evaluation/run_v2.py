import json
import argparse
import time
from pathlib import Path
from decimal import Decimal
from datetime import date

from core.models import FinancialProfile, FinancialEvent, RecurringPattern
from core.state import FinancialState
from optimization.engine import find_max_safe_amount
from optimization.planner import generate_payment_plans

def _parse_date(s: str) -> date:
    return date.fromisoformat(s)

def run_v2_engine(dataset_file: Path, output_file: Path):
    with open(dataset_file, "r") as f:
        dataset = [json.loads(line) for line in f]
        
    predictions = []
    
    for record in dataset:
        start_time = time.time()
        
        req_id = record["request_id"]
        inp = record["input"]
        
        # Parse profile
        prof = inp["profile"]
        profile = FinancialProfile(
            user_id="u1", home_currency="USD",
            current_available_balance=Decimal(str(prof["balance"])),
            minimum_balance_to_keep=Decimal(str(prof["min_balance"])),
            financial_priorities=[], expense_categories_to_protect=[],
            expense_categories_willing_to_reduce=[], expense_categories_willing_to_stop=[],
            payment_methods_user_will_consider=[], max_installment_months=3
        )
        
        request_date = date(2026, 9, 15)
        request_amount = Decimal(str(inp["request_amount"]))
        
        # Parse recurring events
        recurring_expenses = []
        recurring_income = []
            
        for e in inp.get("recurring_events", []):
            pattern = RecurringPattern(
                user_id="u1", category=e["category"], direction=e["direction"],
                average_amount=Decimal(str(e["amount"])), currency="USD",
                frequency_days=e["frequency_days"], typical_day_of_month=e.get("typical_day_of_month"),
                flexibility="fixed", minimum_allowed_amount=None, representative_event_id="ex",
                last_date=request_date, next_expected_date=_parse_date(e["next_date"]),
                is_salary=(e["category"] == "salary")
            )
            if e["direction"] == "debit":
                recurring_expenses.append(pattern)
            else:
                recurring_income.append(pattern)
        
        # Build State
        state = FinancialState(
            user_id="u1", request_date=request_date, home_currency="USD",
            current_available_balance=profile.current_available_balance,
            minimum_balance_to_keep=profile.minimum_balance_to_keep,
            recurring_expenses=recurring_expenses,
            recurring_income=recurring_income
        )
        
        # 1. Check max safe amount for single payment
        max_safe = find_max_safe_amount(state, request_amount)
        
        if max_safe >= request_amount:
            # Can pay in full
            status = "affordable_now"
            method = "full_payment"
            plan_amt = float(request_amount)
            plan = [{"date": request_date.isoformat(), "amount": plan_amt}]
        else:
            # Need a payment plan
            plans = generate_payment_plans(state, request_amount, max_months=1)
            if plans:
                best_plan = plans[-1]  # Take the longest (most affordable) plan
                status = "affordable_with_plan"
                method = "payment_plan"
                plan_amt = best_plan["monthly_payment"]
                plan = []
                d = request_date
                for _ in range(best_plan["months"]):
                    plan.append({"date": d.isoformat(), "amount": plan_amt})
                    d = d.replace(month=d.month+1) if d.month < 12 else d.replace(year=d.year+1, month=1)
            else:
                status = "not_affordable"
                method = "none"
                plan_amt = 0.0
                plan = []
                
        latency = (time.time() - start_time) * 1000
        
        predictions.append({
            "request_id": req_id,
            "status": status,
            "method": method,
            "amount": plan_amt,
            "plan": plan,
            "safety_violations": 0,
            "fallback": False,
            "llm_calls": 0,
            "latency_ms": latency
        })
        
    with open(output_file, "w") as f:
        for p in predictions:
            f.write(json.dumps(p) + "\n")
            
    print(f"Generated {len(predictions)} V2 predictions at {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    
    run_v2_engine(args.dataset, args.out)
