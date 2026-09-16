import json

fails = ['holdout_11', 'holdout_41', 'holdout_192', 'holdout_199', 'holdout_232', 'holdout_266', 'holdout_328', 'holdout_341', 'holdout_446', 'holdout_477']

print("| request_id | production_result | reference_result | difference | semantic_rule | expected_contract | root_cause |")
print("| ---------- | ---------: | --------: | ---------- | --- | --- | --- |")

for req_id in fails:
    results = json.load(open('evaluation/amount_accuracy_results.json'))
    act = next(x['actual'] for x in results if x['req_id'] == req_id)
    exp = next(x['expected'] for x in results if x['req_id'] == req_id)
    diff = act - exp
    
    if req_id == 'holdout_192':
        rule = "Recurrence Semantics"
        contract = "Month-aware recurrence"
        cause = "Production used day-of-month (20th), Reference used exact +30 days (19th)"
    else:
        rule = "Day-0 Semantics"
        contract = "Purchase before income / Intraday reserve"
        cause = "Production ignored intraday Day-0 minimum balance; Reference enforced it implicitly via initial lowest_projected"
        
    print(f"| {req_id} | {act} | {exp} | {diff} | {rule} | {contract} | {cause} |")
