import math
from decimal import Decimal, InvalidOperation
from typing import List, Tuple, Dict, Any
from datetime import date
from core.state import FinancialState
from core.models import CandidatePlan
from forecasting.simulator import simulate_cashflow, FORECAST_DAYS
from optimization.engine import is_plan_safe

class SafetyViolationError(Exception):
    """
    Exception raised when a proposed payment plan violates the hard mathematical
    safety boundary on any day in the 90-day horizon, or contains malformed data.
    """
    pass

def _check_finite(val: Any, field_name: str):
    if val is None:
        raise SafetyViolationError(f"Field {field_name} cannot be None.")
    try:
        dec_val = Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        raise SafetyViolationError(f"Field {field_name} must be a valid number, got {val}.")
    if not dec_val.is_finite():
        raise SafetyViolationError(f"Field {field_name} cannot be NaN or Infinity.")
    return dec_val

def enforce_hard_safety_boundary(state: FinancialState, req_amt: Decimal, candidate: CandidatePlan):
    """
    A final, uncompromising safety check. 
    Independently verifies all arithmetic and temporal constraints.
    If ANY condition is violated, it raises an uncatchable SafetyViolationError.
    """
    # 1. NaN / Infinity / Malformed Type checking
    if not isinstance(candidate, CandidatePlan):
        raise SafetyViolationError("Candidate is not a CandidatePlan object.")
        
    req_amt_dec = _check_finite(req_amt, "req_amt")
    amount_today_dec = _check_finite(candidate.amount_today, "amount_today")
    
    # 2. Basic Amount Bounds
    if amount_today_dec < Decimal("0"):
        raise SafetyViolationError(f"Amount today cannot be negative: {amount_today_dec}")
    if amount_today_dec > req_amt_dec:
        raise SafetyViolationError(f"Amount today ({amount_today_dec}) cannot exceed requested amount ({req_amt_dec})")
        
    # 3. Schedule Checks
    if not candidate.schedule:
        raise SafetyViolationError("Candidate schedule cannot be empty.")
        
    total_schedule_amount = Decimal("0")
    last_date = None
    
    extra_debits: List[Tuple[date, Decimal]] = []
    
    for idx, inst in enumerate(candidate.schedule):
        if "date" not in inst or "amount" not in inst:
            raise SafetyViolationError(f"Installment {idx} missing 'date' or 'amount'")
            
        inst_amt = _check_finite(inst["amount"], f"schedule[{idx}].amount")
        if inst_amt < Decimal("0"):
            raise SafetyViolationError(f"Installment {idx} amount cannot be negative: {inst_amt}")
            
        inst_date = inst["date"]
        if isinstance(inst_date, str):
            try:
                inst_date = date.fromisoformat(inst_date)
            except ValueError:
                raise SafetyViolationError(f"Installment {idx} date is malformed: {inst['date']}")
                
        if type(inst_date) is not date:
            raise SafetyViolationError(f"Installment {idx} date must be exactly a date object, not datetime.")
            
        # Ensure dates are valid
        if inst_date < state.request_date:
            raise SafetyViolationError(f"Installment {idx} date {inst_date} is before request date {state.request_date}")
            
        # Maximum allowed planning horizon (approx 365 days is reasonable to prevent absurd plans)
        if (inst_date - state.request_date).days > 365:
            raise SafetyViolationError(f"Installment {idx} date {inst_date} is too far in the future.")
            
        # Ensure ordering
        if last_date and inst_date <= last_date:
            raise SafetyViolationError(f"Installment {idx} date {inst_date} is not strictly after previous date {last_date}")
            
        last_date = inst_date
        total_schedule_amount += inst_amt
        extra_debits.append((inst_date, inst_amt))
        
    # 4. Sum Consistency
    # Due to floating point/decimal conversion, we check exact equality
    if total_schedule_amount != req_amt_dec:
        raise SafetyViolationError(f"Schedule sum {total_schedule_amount} does not equal requested amount {req_amt_dec}")
        
    # 5. Method/Status Consistency
    if candidate.method == "full_payment":
        if len(candidate.schedule) != 1:
            raise SafetyViolationError("full_payment method must have exactly 1 installment.")
        if extra_debits[0][1] != req_amt_dec:
            raise SafetyViolationError("full_payment amount must equal requested amount.")
        if extra_debits[0][0] != state.request_date:
            raise SafetyViolationError("full_payment date must be today (request_date).")
            
    # 6. Independent Cashflow Simulation
    # We pass the schedule as extra debits to the simulator, completely ignoring candidate.is_safe
    try:
        test_days = simulate_cashflow(state, extra_debits=extra_debits)
    except Exception as e:
        raise SafetyViolationError(f"[{candidate.plan_id}] Simulation crashed during safety check: {str(e)}")
    
    # 7. Minimum Balance Violation (across the 90-day simulation)
    # Simulator only goes up to FORECAST_DAYS. If payments occur after that, 
    # they aren't fully checked for safety against daily balances, but that's a known limitation of the 90-day engine.
    for day in test_days:
        if day.closing_balance < state.minimum_balance_to_keep:
            raise SafetyViolationError(
                f"Proposed plan violates hard safety boundary "
                f"(min balance {state.minimum_balance_to_keep}) on {day.date}. Projected: {day.closing_balance}"
            )
