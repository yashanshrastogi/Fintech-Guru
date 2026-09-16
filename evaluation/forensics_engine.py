import json
import logging
from decimal import Decimal
from typing import Dict, Any, List
from datetime import date

from app.main import build_canonical_state, multi_agent_fallback_handler, AffordabilityRequest
from llm.router import route_request
from forecasting.simulator import simulate_cashflow
from optimization.engine import find_max_safe_amount
from optimization.planner import generate_payment_plans
from validation.boundary import enforce_hard_safety_boundary, SafetyViolationError

def run_forensics(dataset_path: str, output_path: str):
    results = []
    
    with open(dataset_path, "r") as f:
        for line in f:
            record = json.loads(line)
            req = AffordabilityRequest(**record)
            
            forensics: Dict[str, Any] = {
                "input": {
                    "request_id": req.purchase.request_id,
                    "request_amount": float(req.purchase.request_amount),
                    "currency": req.profile.home_currency,
                    "current_balance": float(req.profile.current_available_balance),
                    "minimum_balance": float(req.profile.minimum_balance_to_keep)
                },
                "ground_truth": {
                    "expected_decision": record.get("expected_decision")
                },
                "routing": {},
                "state": {},
                "prediction": {},
                "validation": {},
                "taxonomy": []
            }
            
            # ROUTING
            def dummy_det(**kwargs): return "deterministic"
            def dummy_agent(**kwargs): return "agentic"
            path = route_request(req.mode, dummy_det, dummy_agent, req=req)
            is_agentic = (path == "agentic")
            forensics["routing"]["path"] = path
            
            # We don't actually invoke the LLM to save time/cost during massive forensic scans,
            # unless we specifically want to evaluate the LLM accuracy. Since the benchmark
            # was already run, we could mock it, but let's assume we run the full logic.
            # However, for speed, let's just trace the deterministic flow unless agentic is forced.
            
            # STATE RECONSTRUCTION
            try:
                state = build_canonical_state(req)
                forensics["state"] = {
                    "reconciled_events": len(state.reconciled_events),
                    "recurring_expenses": len(state.recurring_expenses),
                    "recurring_income": len(state.recurring_income),
                    "effective_salary": float(state.get_effective_salary()) if state.get_effective_salary() else None
                }
            except Exception as e:
                forensics["taxonomy"].append("canonical-state construction error")
                forensics["state"]["error"] = str(e)
                continue
                
            # SIMULATION (BASELINE)
            try:
                days = simulate_cashflow(state)
                sim_min = min((d.closing_balance for d in days), default=state.current_available_balance)
                forensics["validation"]["simulator_minimum_balance"] = float(sim_min)
            except Exception as e:
                forensics["taxonomy"].append("simulator error")
                
            # OPTIMIZER
            req_amt = req.purchase.request_amount
            try:
                max_safe = find_max_safe_amount(state, req_amt)
                forensics["validation"]["optimizer_max_safe"] = float(max_safe)
            except Exception as e:
                forensics["taxonomy"].append("safe-amount optimizer error")
                max_safe = Decimal("-1")
                
            # PLANNER & BOUNDARY
            status = "not_affordable"
            plans = []
            if max_safe >= req_amt:
                status = "affordable_now"
                # Mock full plan for boundary
                from core.models import CandidatePlan
                plans.append(CandidatePlan(
                    plan_id="full_payment", method="full_payment", amount_today=req_amt,
                    schedule=[{"date": req.purchase.request_date, "amount": float(req_amt)}],
                    lowest_projected_balance=Decimal("0"), limiting_date=req.purchase.request_date,
                    safety_margin=max_safe - req_amt, is_safe=True
                ))
            else:
                try:
                    raw_plans = generate_payment_plans(state, req_amt, max_months=req.profile.max_installment_months or 3)
                    if raw_plans:
                        status = "affordable_with_plan"
                        best = raw_plans[-1]
                        from core.models import CandidatePlan
                        d = req.purchase.request_date
                        schedule = []
                        for _ in range(best["months"]):
                            schedule.append({"date": d, "amount": float(best["monthly_payment"])})
                            d = d.replace(month=d.month % 12 + 1, year=d.year + (1 if d.month == 12 else 0))
                        plans.append(CandidatePlan(
                            plan_id="inst", method="payment_plan", amount_today=best["monthly_payment"],
                            schedule=schedule, lowest_projected_balance=Decimal("0"),
                            limiting_date=req.purchase.request_date, safety_margin=Decimal("0"), is_safe=True
                        ))
                except Exception as e:
                    forensics["taxonomy"].append("payment-plan optimizer error")
                    
            # VALIDATION
            boundary_result = "passed"
            boundary_reason = None
            valid_plans = []
            for p in plans:
                try:
                    enforce_hard_safety_boundary(state, req_amt, p)
                    valid_plans.append(p)
                except SafetyViolationError as e:
                    boundary_result = "rejected"
                    boundary_reason = str(e)
                    forensics["taxonomy"].append("safety-boundary rejection")
            
            if not valid_plans:
                status = "not_affordable"
                
            forensics["prediction"]["status"] = status
            forensics["validation"]["boundary_result"] = boundary_result
            forensics["validation"]["boundary_reason"] = boundary_reason
            
            # GROUND TRUTH DIFF
            if "expected_decision" in forensics["ground_truth"]:
                if status != forensics["ground_truth"]["expected_decision"]:
                    forensics["taxonomy"].append("status decision-rule error")
                    
            results.append(forensics)
            
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
        
if __name__ == "__main__":
    run_forensics("evaluation/datasets/external_benchmark.jsonl", "evaluation/forensics_output.json")
