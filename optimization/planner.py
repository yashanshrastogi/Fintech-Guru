from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional

from core.state import FinancialState
from forecasting.simulator import simulate_cashflow
from optimization.engine import is_plan_safe

ZERO = Decimal("0")

def generate_payment_plans(state: FinancialState, total_amount: Decimal, max_months: Optional[int]) -> List[Dict[str, Any]]:
    """
    Generate safe payment plan options for a given total amount.
    Iterates from 1 month up to max_months (or a default cap if not provided).
    A plan is only returned if all its installments can be safely paid without 
    violating the minimum balance across the 90-day forecast.
    """
    if total_amount <= ZERO:
        return []
        
    plans = []
    
    # Cap iterations to a reasonable maximum if user didn't specify
    max_iterations = max_months if (max_months and max_months > 0) else 12
    # We only forecast 90 days, so plans beyond 3-4 months can only be partially simulated.
    # We will simulate up to the 90-day horizon.
    
    for months in range(1, max_iterations + 1):
        # Divide amount evenly
        monthly_payment = (total_amount / Decimal(str(months))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # Adjust last payment for rounding errors
        installments = [monthly_payment] * months
        total_installments = sum(installments)
        if total_installments != total_amount:
            installments[-1] += (total_amount - total_installments)
            
        # Create schedule
        schedule = []
        current_date = state.request_date
        for amt in installments:
            schedule.append((current_date, amt))
            # Next month approx
            current_date += timedelta(days=30)
            
        # Simulate to check safety
        # Only pass debits that fall within the 90-day horizon (handled by simulate_cashflow)
        test_days = simulate_cashflow(state, extra_debits=schedule)
        
        if is_plan_safe(test_days, state.minimum_balance_to_keep):
            plans.append({
                "months": months,
                "monthly_payment": float(monthly_payment),
                "total_amount": float(total_amount),
                "is_safe": True
            })
            
    return plans
