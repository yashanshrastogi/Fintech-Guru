"""
90-day deterministic cash flow simulation engine.
Simulates daily balance for each request, respecting all financial events,
recurring patterns, and candidate payment plans.
Uses Decimal arithmetic throughout to avoid floating-point errors.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from typing import List, Optional, Dict, Tuple
import logging
from collections import defaultdict

from models import FinancialEvent, FinancialProfile, PaymentOption, CashFlowDay
from config import FORECAST_DAYS

logger = logging.getLogger(__name__)

ZERO = Decimal("0")
CENT = Decimal("0.01")


def simulate_cashflow(
    profile: FinancialProfile,
    events: List[FinancialEvent],
    patterns: List[dict],
    request_date: date,
    extra_debits: Optional[List[Tuple[date, Decimal]]] = None,
    spending_overrides: Optional[Dict[str, dict]] = None,  # event_id -> {action, new_amount}
    salary_updates: Optional[Dict[str, Decimal]] = None,   # category -> new_amount
) -> List[CashFlowDay]:
    """
    Run a 90-day daily cash flow simulation.
    
    Args:
        profile: User's financial profile
        events: Reconciled future events (settlement_date >= request_date or event_date >= request_date)
        patterns: Recurring patterns projected into the future
        request_date: Start date of simulation
        extra_debits: Additional payment debits to include (e.g. candidate plan payments)
        spending_overrides: Changes to apply to recurring expenses
        salary_updates: Updated salary amounts from messages
    
    Returns:
        List of CashFlowDay objects for each day in the forecast period
    """
    end_date = request_date + timedelta(days=FORECAST_DAYS)
    
    # Build a day-indexed ledger
    # ledger[day] = list of (amount, description, is_debit)
    ledger: Dict[date, List[Tuple[Decimal, str, bool]]] = defaultdict(list)
    
    # Step 1: Add confirmed future events (those with dates in the forecast window)
    # Track which (date, category, direction) combos have confirmed events
    # to prevent double-counting with recurring pattern projections
    confirmed_event_dates: Dict[Tuple[date, str, str], bool] = {}
    
    for event in events:
        # Use settlement_date if available, else event_date
        effective_date = event.settlement_date or event.event_date
        if effective_date is None:
            continue
        
        # Only include future events
        if effective_date < request_date or effective_date > end_date:
            continue
        
        # Skip if no amount
        amount = event.amount_home_currency or event.amount
        if amount is None or amount <= ZERO:
            continue
        
        is_debit = (event.direction == "debit")
        ledger[effective_date].append((amount, f"{event.event_id}:{event.description}", is_debit))
        
        # Mark this (date, category, direction) as having a confirmed event
        confirmed_event_dates[(effective_date, event.category, event.direction)] = True
    
    # Step 2: Project recurring patterns into future
    for pattern in patterns:
        category = pattern["category"]
        direction = pattern["direction"]
        flexibility = pattern["flexibility"]
        event_type = pattern["event_type"]
        freq_days = pattern["frequency_days"]
        next_date = pattern["next_date"]
        avg_amount = pattern["avg_amount"]
        is_debit = (direction == "debit")
        last_event_id = pattern["last_event_id"]
        typical_dom = pattern.get("typical_dom")
        
        # Apply spending overrides
        actual_amount = avg_amount
        skip_this_pattern = False
        
        if spending_overrides:
            for override_event_id, override in spending_overrides.items():
                if override_event_id == last_event_id:
                    if override["action"] == "stop":
                        skip_this_pattern = True
                        break
                    elif override["action"] == "reduce_to":
                        actual_amount = override["new_amount"]
        
        if skip_this_pattern:
            continue
        
        # Apply salary updates
        if event_type == "income" and category == "salary" and salary_updates:
            if "salary" in salary_updates:
                actual_amount = salary_updates["salary"]
        
        # Project forward
        if event_type == "income" and category == "salary" and typical_dom is not None:
            # Salary: project monthly on the correct day-of-month
            import calendar
            proj_date = next_date
            while proj_date <= end_date:
                # Skip if a confirmed event already covers this date+category
                if (proj_date, category, direction) not in confirmed_event_dates:
                    ledger[proj_date].append((
                        actual_amount,
                        f"recurring:{category}:{pattern['last_event_id']}",
                        is_debit
                    ))
                # Next salary is next month on the same day
                next_month = proj_date.month + 1
                next_year = proj_date.year
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                max_day = calendar.monthrange(next_year, next_month)[1]
                actual_dom = min(typical_dom, max_day)
                proj_date = date(next_year, next_month, actual_dom)
        else:
            # Regular fixed interval projection
            proj_date = next_date
            while proj_date <= end_date:
                # Skip if a confirmed event already covers this date+category
                if (proj_date, category, direction) not in confirmed_event_dates:
                    ledger[proj_date].append((
                        actual_amount,
                        f"recurring:{category}:{pattern['last_event_id']}",
                        is_debit
                    ))
                proj_date += timedelta(days=freq_days)
    
    # Step 3: Add extra debits (candidate plan payments)
    if extra_debits:
        for pay_date, pay_amount in extra_debits:
            if request_date <= pay_date <= end_date and pay_amount > ZERO:
                ledger[pay_date].append((pay_amount, "candidate_payment", True))
    
    # Step 4: Simulate day by day
    balance = profile.current_available_balance
    days = []
    
    current_date = request_date
    while current_date <= end_date:
        income = ZERO
        expenses = ZERO
        event_refs = []
        
        for amount, ref, is_debit in ledger.get(current_date, []):
            if is_debit:
                expenses += amount
            else:
                income += amount
            event_refs.append(ref)
        
        opening = balance
        balance = opening + income - expenses
        
        day = CashFlowDay(
            day=current_date,
            opening_balance=opening,
            income=income,
            expenses=expenses,
            closing_balance=balance,
            events=event_refs,
        )
        days.append(day)
        current_date += timedelta(days=1)
    
    return days


def get_minimum_balance_in_period(days: List[CashFlowDay]) -> Decimal:
    """Return the minimum closing balance across all simulated days."""
    if not days:
        return ZERO
    return min(d.closing_balance for d in days)


def is_plan_safe(
    days: List[CashFlowDay],
    minimum_balance: Decimal,
) -> bool:
    """Check if the plan keeps balance >= minimum_balance throughout the period."""
    return get_minimum_balance_in_period(days) >= minimum_balance


def find_amount_safe_to_pay(
    profile: FinancialProfile,
    events: List[FinancialEvent],
    patterns: List[dict],
    request_date: date,
    requested_amount: Decimal,
    salary_updates: Optional[Dict[str, Decimal]] = None,
) -> Decimal:
    """
    Find the maximum amount safe to pay today (on request_date) without
    violating minimum_balance over the 90-day period.
    
    Uses binary search over the payment amount since the safety predicate
    is monotonically decreasing (larger payment → lower balance → less safe).
    
    Returns 0 ≤ amount ≤ requested_amount
    """
    # First check if paying nothing is safe (baseline)
    baseline_days = simulate_cashflow(
        profile=profile,
        events=events,
        patterns=patterns,
        request_date=request_date,
        extra_debits=None,
        salary_updates=salary_updates,
    )
    
    # Check if baseline already violates minimum balance
    # (This can happen if scheduled expenses already put them below minimum)
    
    # Binary search for max safe amount
    low = ZERO
    high = min(requested_amount, profile.current_available_balance)
    
    if high <= ZERO:
        return ZERO
    
    # Check if paying the full high amount is safe
    test_days = simulate_cashflow(
        profile=profile,
        events=events,
        patterns=patterns,
        request_date=request_date,
        extra_debits=[(request_date, high)],
        salary_updates=salary_updates,
    )
    
    if is_plan_safe(test_days, profile.minimum_balance_to_keep):
        return high
    
    # Binary search
    precision = Decimal("0.01")
    iterations = 0
    max_iterations = 30
    
    while (high - low) > precision and iterations < max_iterations:
        mid = (low + high) / 2
        mid = mid.quantize(precision, rounding=ROUND_HALF_UP)
        
        test_days = simulate_cashflow(
            profile=profile,
            events=events,
            patterns=patterns,
            request_date=request_date,
            extra_debits=[(request_date, mid)],
            salary_updates=salary_updates,
        )
        
        if is_plan_safe(test_days, profile.minimum_balance_to_keep):
            low = mid
        else:
            high = mid
        
        iterations += 1
    
    result = low.quantize(precision, rounding=ROUND_HALF_UP)
    return max(ZERO, min(result, requested_amount))


def find_earliest_full_payment_date(
    profile: FinancialProfile,
    events: List[FinancialEvent],
    patterns: List[dict],
    request_date: date,
    requested_amount: Decimal,
    desired_completion_date: date,
    salary_updates: Optional[Dict[str, Decimal]] = None,
    spending_overrides: Optional[Dict[str, dict]] = None,
) -> Optional[date]:
    """
    Find the earliest date within the 90-day forecast when the full
    requested_amount can be paid as a single payment safely.
    
    Returns None if no such date exists within the forecast period.
    """
    end_date = request_date + timedelta(days=FORECAST_DAYS)
    
    # Check each day starting from request_date
    current_date = request_date
    while current_date <= end_date:
        # Would paying requested_amount on current_date be safe?
        test_days = simulate_cashflow(
            profile=profile,
            events=events,
            patterns=patterns,
            request_date=request_date,
            extra_debits=[(current_date, requested_amount)],
            spending_overrides=spending_overrides,
            salary_updates=salary_updates,
        )
        
        # Only check days from payment date onwards (payment is made on current_date)
        relevant_days = [d for d in test_days if d.day >= current_date]
        if relevant_days and get_minimum_balance_in_period(relevant_days) >= profile.minimum_balance_to_keep:
            return current_date
        
        current_date += timedelta(days=1)
    
    return None


def simulate_installment_plan(
    profile: FinancialProfile,
    events: List[FinancialEvent],
    patterns: List[dict],
    request_date: date,
    payment_option: PaymentOption,
    salary_updates: Optional[Dict[str, Decimal]] = None,
    spending_overrides: Optional[Dict[str, dict]] = None,
) -> Tuple[bool, Decimal, List[Tuple[date, Decimal]]]:
    """
    Simulate an installment plan and check if it's safe.
    
    Returns:
        (is_safe, min_balance, payment_schedule)
    """
    # Build payment schedule from the installment option
    schedule = _build_payment_schedule(payment_option)
    
    # Convert schedule to extra_debits format
    extra_debits = [(pay_date, amount) for pay_date, amount in schedule]
    
    days = simulate_cashflow(
        profile=profile,
        events=events,
        patterns=patterns,
        request_date=request_date,
        extra_debits=extra_debits,
        spending_overrides=spending_overrides,
        salary_updates=salary_updates,
    )
    
    min_balance = get_minimum_balance_in_period(days)
    safe = min_balance >= profile.minimum_balance_to_keep
    
    return safe, min_balance, schedule


def _build_payment_schedule(payment_option: PaymentOption) -> List[Tuple[date, Decimal]]:
    """Build the exact payment schedule for a payment option."""
    schedule = []
    
    if payment_option.payment_method == "full_payment":
        schedule.append((payment_option.first_payment_date, payment_option.payment_amount))
        return schedule
    
    # Installments
    current_date = payment_option.first_payment_date
    freq = payment_option.payment_frequency_days or 30
    
    for i in range(payment_option.number_of_payments):
        if i == 0:
            pay_date = payment_option.first_payment_date
        else:
            pay_date = current_date
        
        schedule.append((pay_date, payment_option.payment_amount))
        
        if i < payment_option.number_of_payments - 1:
            current_date = pay_date + timedelta(days=freq)
    
    return schedule
