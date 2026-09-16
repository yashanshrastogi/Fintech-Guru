import pytest
from datetime import date
from decimal import Decimal

from core.models import UserProfile, PurchaseRequest, IncomeEvent, ExpenseEvent
from core.state import FinancialState
from optimization.engine import find_max_safe_amount

# 1. Day-0 Semantics Tests
def test_purchase_before_same_day_salary():
    """If salary hits today, it is assumed to hit AFTER the purchase."""
    state = FinancialState(
        user_id="u1",
        request_date=date(2026, 9, 15),
        home_currency="USD",
        current_available_balance=Decimal("1000"),
        minimum_balance_to_keep=Decimal("200"),
        reconciled_events=[
            IncomeEvent(event_id="inc1", user_id="u1", description="Salary", category="salary", amount=Decimal("5000"), event_date=date(2026, 9, 15), status="settled", source="Emp")
        ],
        recurring_income=[],
        recurring_expenses=[],
        evidence_overrides={}
    )
    # The max spend should be limited by the initial headroom: 1000 - 200 = 800
    safe_amt = find_max_safe_amount(state, Decimal("1000"))
    assert safe_amt == Decimal("800")

def test_purchase_exactly_at_minimum_reserve():
    """If balance == min_balance, safe amount is 0."""
    state = FinancialState(
        user_id="u1",
        request_date=date(2026, 9, 15),
        home_currency="USD",
        current_available_balance=Decimal("500"),
        minimum_balance_to_keep=Decimal("500"),
        reconciled_events=[], recurring_income=[], recurring_expenses=[], evidence_overrides={}
    )
    safe_amt = find_max_safe_amount(state, Decimal("1000"))
    assert safe_amt == Decimal("0")

def test_zero_starting_headroom():
    """If balance < min_balance, safe amount is 0."""
    state = FinancialState(
        user_id="u1",
        request_date=date(2026, 9, 15),
        home_currency="USD",
        current_available_balance=Decimal("400"),
        minimum_balance_to_keep=Decimal("500"),
        reconciled_events=[], recurring_income=[], recurring_expenses=[], evidence_overrides={}
    )
    safe_amt = find_max_safe_amount(state, Decimal("1000"))
    assert safe_amt == Decimal("0")

# 2. Recurrence Semantics Tests
from forecasting.income import project_next_salary_date

def test_month_end_clamping_31_to_30():
    # Anchor is 31st, but next month only has 30 days
    # Jan 31 -> Feb 28
    d = project_next_salary_date(date(2025, 1, 31), 31, date(2025, 1, 31))
    assert d == date(2025, 2, 28)

def test_month_end_clamping_leap_year():
    # Jan 31 -> Feb 29
    d = project_next_salary_date(date(2024, 1, 31), 31, date(2024, 1, 31))
    assert d == date(2024, 2, 29)

def test_month_aware_feb_to_mar():
    # If the anchor is 30, but it fired on Feb 28, the next one should go back to Mar 30!
    # project_next_salary_date explicitly takes the anchor day
    d = project_next_salary_date(date(2025, 2, 28), 30, date(2025, 2, 28))
    assert d == date(2025, 3, 30)

def test_month_aware_30_to_31():
    d = project_next_salary_date(date(2025, 4, 30), 31, date(2025, 4, 30))
    assert d == date(2025, 5, 31)

