from decimal import Decimal
from typing import List, Tuple
from datetime import date
from core.state import FinancialState
from forecasting.simulator import simulate_cashflow
from optimization.engine import is_plan_safe

class SafetyViolationError(Exception):
    """
    Exception raised when a proposed payment plan violates the hard mathematical
    safety boundary (minimum_balance_to_keep) on any day in the 90-day horizon.
    """
    pass

def enforce_hard_safety_boundary(state: FinancialState, extra_debits: List[Tuple[date, Decimal]]):
    """
    A final, uncompromising safety check. 
    Runs the chosen plan through the 90-day simulator. 
    If minimum_balance_to_keep is violated on ANY day, it raises an uncatchable SafetyViolationError.
    """
    test_days = simulate_cashflow(state, extra_debits=extra_debits)
    if not is_plan_safe(test_days, state.minimum_balance_to_keep):
        raise SafetyViolationError(
            "CRITICAL: Proposed plan violates the hard safety boundary "
            f"(minimum balance {state.minimum_balance_to_keep}) within the 90-day horizon."
        )
