from decimal import Decimal
from typing import List
from datetime import date
from core.state import FinancialState
from forecasting.simulator import simulate_cashflow
from core.models import ForecastDay

ZERO = Decimal("0")

def is_plan_safe(days: List[ForecastDay], minimum_balance: Decimal) -> bool:
    """Checks if the minimum closing balance across all days is >= minimum_balance."""
    if not days:
        return True
    return min(d.closing_balance for d in days) >= minimum_balance

def find_max_safe_amount(state: FinancialState, requested_amount: Decimal) -> Decimal:
    """
    Binary search for the maximum safe payment amount today (state.request_date) 
    that never violates state.minimum_balance_to_keep over the 90-day forecast.
    
    Search bounds: [0, min(requested_amount, current_available_balance)]
    Returns: 0 <= safe_amount <= requested_amount
    """
    if requested_amount <= ZERO:
        return ZERO
        
    # Baseline check: is it safe if we pay nothing?
    # If the baseline is unsafe (due to upcoming expenses), then we can't pay anything
    baseline_days = simulate_cashflow(state)
    if not is_plan_safe(baseline_days, state.minimum_balance_to_keep):
        return ZERO
        
    # Day-0 Semantics: The purchase occurs before same-day income clears.
    # The intraday balance must not drop below minimum_balance_to_keep.
    # Therefore, the maximum payment today cannot exceed this initial headroom.
    max_day_0_payment = state.current_available_balance - state.minimum_balance_to_keep
    if max_day_0_payment <= ZERO:
        return ZERO
        
    low = ZERO
    high = min(requested_amount, max_day_0_payment)
    
    if high <= ZERO:
        return ZERO
        
    # Check if paying the full max bound is safe
    full_days = simulate_cashflow(state, extra_debits=[(state.request_date, high)])
    if is_plan_safe(full_days, state.minimum_balance_to_keep):
        return high
        
    # Binary search
    best_safe = ZERO
    epsilon = Decimal("0.01")
    
    while high - low >= epsilon:
        mid = (low + high) / Decimal("2")
        # Quantize to 2 decimals to prevent infinite loop on floats
        mid = mid.quantize(Decimal("0.01"))
        
        # If mid didn't move from low or high (due to quantize), break
        if mid == low or mid == high:
            break
            
        test_days = simulate_cashflow(state, extra_debits=[(state.request_date, mid)])
        if is_plan_safe(test_days, state.minimum_balance_to_keep):
            best_safe = mid
            low = mid
        else:
            high = mid
            
    return best_safe
