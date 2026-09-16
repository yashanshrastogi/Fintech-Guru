import json
import uuid
from decimal import Decimal
from datetime import date, timedelta
from typing import List, Dict, Any

def generate_reference_safe_amount(
    req_amt: Decimal,
    current_balance: Decimal,
    min_balance: Decimal,
    request_date: date,
    recurring_incomes: List[Dict],
    recurring_expenses: List[Dict],
    forecast_days: int = 90
) -> Decimal:
    """Independent reference model to compute the exact safe amount today."""
    # Day-0 Semantics: The purchase occurs before same-day income clears.
    # Therefore, the absolute max we can spend today is current_balance - min_balance.
    max_day_0_payment = current_balance - min_balance
    if max_day_0_payment <= Decimal("0"):
        return Decimal("0.0")
        
    balance = current_balance
    lowest_projected_eod = Decimal("Infinity")
    
    def get_next_month_date(last_date: date, anchor_day: int) -> date:
        y, m = last_date.year, last_date.month
        m += 1
        if m > 12:
            m = 1
            y += 1
        next_month_1st = date(y + (m // 12), (m % 12) + 1, 1) if m < 12 else date(y + 1, 1, 1)
        max_day = (next_month_1st - timedelta(days=1)).day
        return date(y, m, min(anchor_day, max_day))

    # Precompute monthly recurring dates independently
    monthly_income_dates = {}
    for i, inc in enumerate(recurring_incomes):
        if inc["frequency_days"] == 30:
            dates = set()
            curr = inc["start_date"]
            anchor = curr.day
            while curr <= request_date + timedelta(days=forecast_days):
                if curr >= request_date:
                    dates.add(curr)
                curr = get_next_month_date(curr, anchor)
            monthly_income_dates[i] = dates

    monthly_expense_dates = {}
    for i, exp in enumerate(recurring_expenses):
        if exp["frequency_days"] == 30:
            dates = set()
            curr = exp["start_date"]
            anchor = curr.day
            while curr <= request_date + timedelta(days=forecast_days):
                if curr >= request_date:
                    dates.add(curr)
                curr = get_next_month_date(curr, anchor)
            monthly_expense_dates[i] = dates

    for i in range(0, forecast_days + 1):
        current_day = request_date + timedelta(days=i)
        
        # Add income
        for idx, inc in enumerate(recurring_incomes):
            if inc["frequency_days"] == 30:
                if current_day in monthly_income_dates[idx]:
                    balance += Decimal(str(inc["amount"]))
            elif (current_day - inc["start_date"]).days % inc["frequency_days"] == 0:
                balance += Decimal(str(inc["amount"]))
                
        # Subtract expenses
        for idx, exp in enumerate(recurring_expenses):
            if exp["frequency_days"] == 30:
                if current_day in monthly_expense_dates[idx]:
                    balance -= Decimal(str(exp["amount"]))
            elif (current_day - exp["start_date"]).days % exp["frequency_days"] == 0:
                balance -= Decimal(str(exp["amount"]))
                
        if balance < lowest_projected_eod:
            lowest_projected_eod = balance
            
    # The max we can spend based on EOD balances
    safe_from_eod = lowest_projected_eod - min_balance
    
    # The absolute safe amount must satisfy both the Day-0 intraday bound and the EOD bound
    safe_amount = min(max_day_0_payment, safe_from_eod)
    
    return min(req_amt, max(Decimal("0.0"), safe_amount))

def generate_benchmark():
    records = []
    
    scenarios = [
        # Scenario 1: Plenty of money
        {
            "id": "indep_1",
            "req_amt": 500.0,
            "balance": 2000.0,
            "min_balance": 100.0,
            "incomes": [{"amount": 2000.0, "frequency_days": 30, "start_date": date(2026, 9, 1)}],
            "expenses": [{"amount": 500.0, "frequency_days": 30, "start_date": date(2026, 9, 10)}]
        },
        # Scenario 2: Just barely enough
        {
            "id": "indep_2",
            "req_amt": 900.0,
            "balance": 1000.0,
            "min_balance": 100.0,
            "incomes": [],
            "expenses": []
        },
        # Scenario 3: Expense drops balance too low in the future
        {
            "id": "indep_3",
            "req_amt": 500.0,
            "balance": 1000.0,
            "min_balance": 200.0,
            "incomes": [],
            "expenses": [{"amount": 600.0, "frequency_days": 30, "start_date": date(2026, 9, 20)}]
        },
        # Scenario 4: Income saves it (wait, income before expense)
        {
            "id": "indep_4",
            "req_amt": 500.0,
            "balance": 1000.0,
            "min_balance": 200.0,
            "incomes": [{"amount": 1000.0, "frequency_days": 30, "start_date": date(2026, 9, 18)}],
            "expenses": [{"amount": 600.0, "frequency_days": 30, "start_date": date(2026, 9, 20)}]
        }
    ]
    
    req_date = date(2026, 9, 15)
    
    for s in scenarios:
        safe_amt = generate_reference_safe_amount(
            Decimal(str(s["req_amt"])), Decimal(str(s["balance"])), Decimal(str(s["min_balance"])), req_date,
            s["incomes"], s["expenses"]
        )
        
        # Build transactions to trigger recurring logic in pipeline
        transactions = []
        for inc in s["incomes"]:
            d1 = inc["start_date"] - timedelta(days=inc["frequency_days"])
            d2 = inc["start_date"]
            transactions.append({
                "event_id": str(uuid.uuid4()), "user_id": "u1", "description": "salary", "category": "salary",
                "amount": inc["amount"], "event_date": d1.isoformat(), "status": "settled", "event_type": "income", "is_salary": True, "source": "Emp"
            })
            transactions.append({
                "event_id": str(uuid.uuid4()), "user_id": "u1", "description": "salary", "category": "salary",
                "amount": inc["amount"], "event_date": d2.isoformat(), "status": "settled", "event_type": "income", "is_salary": True, "source": "Emp"
            })
            
        for exp in s["expenses"]:
            d1 = exp["start_date"] - timedelta(days=exp["frequency_days"])
            d2 = exp["start_date"]
            transactions.append({
                "event_id": str(uuid.uuid4()), "user_id": "u1", "description": "rent", "category": "rent",
                "amount": exp["amount"], "event_date": d1.isoformat(), "status": "settled", "event_type": "expense", "flexibility": "fixed"
            })
            transactions.append({
                "event_id": str(uuid.uuid4()), "user_id": "u1", "description": "rent", "category": "rent",
                "amount": exp["amount"], "event_date": d2.isoformat(), "status": "settled", "event_type": "expense", "flexibility": "fixed"
            })
            
        record = {
            "mode": "deterministic",
            "profile": {
                "user_id": "u1",
                "home_currency": "USD",
                "current_available_balance": s["balance"],
                "minimum_balance_to_keep": s["min_balance"],
                "financial_priorities": [],
                "expense_categories_to_protect": [],
                "expense_categories_willing_to_reduce": [],
                "expense_categories_willing_to_stop": [],
                "payment_methods_user_will_consider": [],
                "max_installment_months": 3
            },
            "transactions": transactions,
            "purchase": {
                "request_id": s["id"],
                "user_id": "u1",
                "description": "Indep benchmark",
                "request_amount": s["req_amt"],
                "request_date": req_date.isoformat()
            },
            "expected_safe_amount": float(safe_amt)
        }
        records.append(record)
        
    with open("evaluation/datasets/independent_benchmark.jsonl", "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

if __name__ == "__main__":
    generate_benchmark()
