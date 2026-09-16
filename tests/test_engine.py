from datetime import date
from decimal import Decimal
from core.state import FinancialState
from core.models import RecurringPattern
from optimization.engine import find_max_safe_amount

def test_find_max_safe_amount_full():
    state = FinancialState(
        user_id="u1", request_date=date(2026, 9, 15), home_currency="USD",
        current_available_balance=Decimal("1000"), minimum_balance_to_keep=Decimal("100")
    )
    # Requested 500, balance 1000, min keep 100. Should allow full 500.
    safe = find_max_safe_amount(state, Decimal("500"))
    assert safe == Decimal("500")

def test_find_max_safe_amount_bounded_by_balance():
    state = FinancialState(
        user_id="u1", request_date=date(2026, 9, 15), home_currency="USD",
        current_available_balance=Decimal("600"), minimum_balance_to_keep=Decimal("100")
    )
    # Requested 800, balance 600, min keep 100. Max safe is 500.
    safe = find_max_safe_amount(state, Decimal("800"))
    assert safe == Decimal("500")

def test_find_max_safe_amount_with_upcoming_expense():
    state = FinancialState(
        user_id="u1", request_date=date(2026, 9, 15), home_currency="USD",
        current_available_balance=Decimal("600"), minimum_balance_to_keep=Decimal("100"),
        recurring_expenses=[
            RecurringPattern(
                user_id="u1", category="rent", direction="debit", average_amount=Decimal("300"),
                currency="USD", frequency_days=100, typical_day_of_month=None, flexibility="fixed",
                minimum_allowed_amount=None, representative_event_id="e1", 
                last_date=date(2026, 8, 16), next_expected_date=date(2026, 9, 16), is_salary=False
            )
        ]
    )
    # Requested 500, balance 600. Rent 300 hits tomorrow. Min balance is 100.
    # Opening 600. Pay X today. Balance: 600 - X.
    # Tomorrow: Rent 300. Balance: 600 - X - 300 = 300 - X.
    # Must keep 100: 300 - X >= 100 => X <= 200.
    safe = find_max_safe_amount(state, Decimal("500"))
    assert safe == Decimal("200.00")

def test_baseline_unsafe():
    state = FinancialState(
        user_id="u1", request_date=date(2026, 9, 15), home_currency="USD",
        current_available_balance=Decimal("200"), minimum_balance_to_keep=Decimal("100"),
        recurring_expenses=[
            RecurringPattern(
                user_id="u1", category="rent", direction="debit", average_amount=Decimal("300"),
                currency="USD", frequency_days=30, typical_day_of_month=None, flexibility="fixed",
                minimum_allowed_amount=None, representative_event_id="e1", 
                last_date=date(2026, 8, 16), next_expected_date=date(2026, 9, 16), is_salary=False
            )
        ]
    )
    # Balance 200, rent 300 hits tomorrow. Baseline is already unsafe.
    safe = find_max_safe_amount(state, Decimal("100"))
    assert safe == Decimal("0")
