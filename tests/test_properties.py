import pytest
from hypothesis import given, strategies as st
from decimal import Decimal
from datetime import date, timedelta
from typing import List

from core.state import FinancialState
from core.models import RecurringExpense, RecurringIncome
from optimization.engine import find_max_safe_amount, is_plan_safe
from forecasting.simulator import simulate_cashflow

# Custom strategy for generating Decimal amounts
def dec_strategy(min_val=0, max_val=10000):
    return st.integers(min_value=min_val*100, max_value=max_val*100).map(lambda x: Decimal(str(x)) / Decimal("100"))

# Strategy for dates within a 90 day window
def date_strategy():
    base_date = date(2026, 9, 15)
    return st.integers(min_value=0, max_value=89).map(lambda x: base_date + timedelta(days=x))

# Strategy for recurring expenses
@st.composite
def recurring_expense_strategy(draw):
    freq = draw(st.integers(min_value=1, max_value=90))
    amt = draw(dec_strategy(min_val=10, max_val=2000))
    next_date = draw(date_strategy())
    
    return RecurringExpense(
        user_id="u1", category="random", 
        direction="debit",
        average_amount=amt, currency="USD", frequency_days=freq,
        flexibility="fixed", minimum_allowed_amount=None,
        last_date=date(2026, 9, 1),
        next_expected_date=next_date
    )

# Strategy for recurring income
@st.composite
def recurring_income_strategy(draw):
    freq = draw(st.integers(min_value=1, max_value=90))
    amt = draw(dec_strategy(min_val=10, max_val=2000))
    next_date = draw(date_strategy())
    
    return RecurringIncome(
        user_id="u1", category="random", 
        direction="credit",
        average_amount=amt, currency="USD", frequency_days=freq,
        typical_day_of_month=next_date.day,
        last_date=date(2026, 9, 1),
        next_expected_date=next_date, is_salary=True, source="Employer"
    )

# Strategy for FinancialState
@st.composite
def state_strategy(draw):
    balance = draw(dec_strategy(min_val=0, max_val=5000))
    min_keep = draw(dec_strategy(min_val=0, max_val=1000))
    
    num_expenses = draw(st.integers(min_value=0, max_value=5))
    expenses = [draw(recurring_expense_strategy()) for _ in range(num_expenses)]
    
    num_incomes = draw(st.integers(min_value=0, max_value=2))
    incomes = [draw(recurring_income_strategy()) for _ in range(num_incomes)]
    
    return FinancialState(
        user_id="u1", request_date=date(2026, 9, 15), home_currency="USD",
        current_available_balance=balance, minimum_balance_to_keep=min_keep,
        recurring_expenses=expenses, recurring_income=incomes
    )

@given(state=state_strategy(), req_amt=dec_strategy(min_val=10, max_val=3000))
def test_universal_safety_property(state: FinancialState, req_amt: Decimal):
    """
    Universal Property:
    For ANY random financial state, find_max_safe_amount must return a safe_amount
    such that:
    1. 0 <= safe_amount <= requested_amount
    2. If safe_amount > 0, simulating cashflow with this payment MUST NOT violate the minimum_balance_to_keep.
    """
    safe_amount = find_max_safe_amount(state, req_amt)
    
    assert Decimal("0") <= safe_amount <= req_amt
    
    if safe_amount > Decimal("0"):
        test_days = simulate_cashflow(state, extra_debits=[(state.request_date, safe_amount)])
        assert is_plan_safe(test_days, state.minimum_balance_to_keep)
