import json
from datetime import date, timedelta
from decimal import Decimal
from app.main import deterministic_pipeline, AffordabilityRequest
from evaluation.datasets.generate_independent_benchmark import generate_reference_safe_amount

def debug_holdout(req_id="holdout_5"):
    with open("evaluation/datasets/fresh_holdout_benchmark.jsonl") as f:
        for line in f:
            data = json.loads(line)
            if data["purchase"]["request_id"] == req_id:
                break
                
    req = AffordabilityRequest(**data)
    res = deterministic_pipeline(req)
    state = res.get("explanation")
    actual = state.safe_amount_today
    expected = data["expected_safe_amount"]
    
    print(f"ID: {req_id}")
    print(f"Expected: {expected}, Actual: {actual}")
    
    print("\n--- Simulator Ledger ---")
    balance = data["profile"]["current_available_balance"]
    min_bal = data["profile"]["minimum_balance_to_keep"]
    lowest_sim = balance
    
    from forecasting.simulator import simulate_cashflow
    state = res.get("state")
    
    print("\n--- Recurring Incomes ---")
    for inc in state.recurring_income:
        print(f"Cat: {inc.category}, Amount: {inc.average_amount}, Freq: {inc.frequency_days}, Next: {inc.next_expected_date}")
        
    ledger = simulate_cashflow(state)
    
    for d in ledger:
        balance = d.closing_balance
        if balance < lowest_sim:
            lowest_sim = balance
        if d.credits > 0 or d.debits > 0:
            print(f"{d.date}: +{d.credits} -{d.debits} = {balance}")
            
    print(f"Simulator lowest: {lowest_sim}")
    
    from optimization.engine import is_plan_safe
    full_days = simulate_cashflow(res.get("state"), extra_debits=[(res.get("state").request_date, Decimal("1233"))])
    print(f"Is safe with 1233 debit? {is_plan_safe(full_days, res.get('state').minimum_balance_to_keep)}")
    print(f"Lowest with 1233 debit: {min(d.closing_balance for d in full_days)}")
    
    print("\n--- Independent Ledger ---")
    current_day = date.fromisoformat(data["purchase"]["request_date"])
    balance = Decimal(str(data["profile"]["current_available_balance"]))
    lowest_indep = balance
    
    # We must extract the actual incomes and expenses generated.
    # We don't have them in the payload directly (only transactions).
    # But we can reverse engineer them from transactions.
    incomes = {}
    expenses = {}
    for t in data["transactions"]:
        cat = t["category"]
        if t["event_type"] == "income":
            if cat not in incomes: incomes[cat] = []
            incomes[cat].append((date.fromisoformat(t["event_date"]), Decimal(str(t["amount"]))))
        else:
            if cat not in expenses: expenses[cat] = []
            expenses[cat].append((date.fromisoformat(t["event_date"]), Decimal(str(t["amount"]))))
            
    indep_incomes = []
    for cat, evs in incomes.items():
        evs.sort()
        freq = (evs[-1][0] - evs[-2][0]).days
        indep_incomes.append({"start_date": evs[-1][0], "frequency_days": freq, "amount": evs[-1][1], "cat": cat})
        
    indep_expenses = []
    for cat, evs in expenses.items():
        evs.sort()
        freq = (evs[-1][0] - evs[-2][0]).days
        indep_expenses.append({"start_date": evs[-1][0], "frequency_days": freq, "amount": evs[-1][1], "cat": cat})
        
    for i in range(1, 91):
        d = current_day + timedelta(days=i)
        creds = Decimal("0")
        debs = Decimal("0")
        
        for inc in indep_incomes:
            if (d - inc["start_date"]).days % inc["frequency_days"] == 0:
                creds += inc["amount"]
                
        for exp in indep_expenses:
            if (d - exp["start_date"]).days % exp["frequency_days"] == 0:
                debs += exp["amount"]
                
        balance += creds - debs
        if balance < lowest_indep:
            lowest_indep = balance
        if creds > 0 or debs > 0:
            print(f"{d}: +{creds} -{debs} = {balance}")
            
    print(f"Independent lowest: {lowest_indep}")
    
if __name__ == "__main__":
    debug_holdout("holdout_192")
