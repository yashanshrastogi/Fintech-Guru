from datetime import date
from decimal import Decimal
from core.state import FinancialState
from forecasting.simulator import simulate_cashflow
from core.models import RecurringExpense, BaseEvent

def test_simulate_cashflow_basic():
    state = FinancialState(
        user_id="u1", request_date=date(2026, 9, 15), home_currency="USD",
        current_available_balance=Decimal("1000"), minimum_balance_to_keep=Decimal("100")
    )
    
    days = simulate_cashflow(state)
    assert len(days) == 91  # request_date + 90 days
    assert days[0].date == date(2026, 9, 15)
    assert days[0].opening_balance == Decimal("1000")
    assert days[0].closing_balance == Decimal("1000")
    assert days[-1].closing_balance == Decimal("1000")

def test_simulate_cashflow_with_recurring_expense():
    state = FinancialState(
        user_id="u1", request_date=date(2026, 9, 15), home_currency="USD",
        current_available_balance=Decimal("1000"), minimum_balance_to_keep=Decimal("100"),
        recurring_expenses=[
            RecurringExpense(
                user_id="u1", category="rent", direction="debit", average_amount=Decimal("500"),
                currency="USD", frequency_days=30, typical_day_of_month=None, flexibility="fixed",
                minimum_allowed_amount=None, 
                last_date=date(2026, 8, 16), next_expected_date=date(2026, 9, 15)
            )
        ]
    )
    
    days = simulate_cashflow(state)
    assert days[0].debits == Decimal("500")
    assert days[0].closing_balance == Decimal("500")
    
    # Next should be 30 days later: 2026-10-15
    assert days[30].date == date(2026, 10, 15)
    assert days[30].debits == Decimal("500")
    assert days[30].closing_balance == Decimal("0")
