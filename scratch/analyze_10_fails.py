import json
from datetime import date
from decimal import Decimal

fails = ['holdout_214', 'holdout_254']
fails_anti = ['holdout_87']

records = []
for line in open('evaluation/datasets/fresh_holdout_benchmark.jsonl'):
    d = json.loads(line)
    req_id = d['purchase']['request_id']
    if req_id in fails:
        records.append(d)

for line in open('evaluation/datasets/anti_overfit_holdout.jsonl'):
    d = json.loads(line)
    req_id = d['purchase']['request_id']
    if req_id in fails_anti:
        records.append(d)

from app.main import deterministic_pipeline, AffordabilityRequest

for r in records:
    req_id = r['purchase']['request_id']
    req_amt = r['purchase']['request_amount']
    expected = Decimal(str(r['expected_safe_amount']))
    
    aff_req = AffordabilityRequest(**r)
    res = deterministic_pipeline(aff_req)
    actual = res['explanation'].safe_amount_today
    
    print(f"\n--- {req_id} ---")
    print(f"Expected: {expected}, Actual: {actual}, Diff: {actual - expected}")
    for p in res['plans']:
        print(f"  Plan: {p.plan_id}, lowest_projected_balance: {p.lowest_projected_balance}")
    
    incomes = [t for t in r['transactions'] if t['event_type'] == 'income']
    if incomes:
        # get unique categories
        cats = set(i['category'] for i in incomes)
        for c in cats:
            c_incs = sorted([i for i in incomes if i['category'] == c], key=lambda x: x['event_date'])
            amts = set(i['amount'] for i in c_incs)
            dates = [i['event_date'] for i in c_incs]
            print(f"  Inc {c}: Amts={amts}, Dates={dates}")
    else:
        print("  No recurring income")
        
    expenses = [t for t in r['transactions'] if t['event_type'] == 'expense']
    if expenses:
        cats = set(i['category'] for i in expenses)
        for c in cats:
            c_exps = sorted([i for i in expenses if i['category'] == c], key=lambda x: x['event_date'])
            amts = set(i['amount'] for i in c_exps)
            dates = [i['event_date'] for i in c_exps]
            print(f"  Exp {c}: Amts={amts}, Dates={dates}")
    else:
        print("  No recurring expenses")
