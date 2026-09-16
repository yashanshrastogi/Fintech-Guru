from datetime import date
from decimal import Decimal
from core.state import FinancialState
from core.models import RecurringPattern
from optimization.planner import generate_payment_plans

def test_planner_one_month_safe():
    state = FinancialState(
        user_id="u1", request_date=date(2026, 9, 15), home_currency="USD",
        current_available_balance=Decimal("1000"), minimum_balance_to_keep=Decimal("100")
    )
    # Requested 500, balance 1000. 1-month plan is 500. Should be safe.
    plans = generate_payment_plans(state, Decimal("500"), max_months=3)
    assert len(plans) == 3
    assert plans[0]["months"] == 1
    assert plans[0]["monthly_payment"] == 500.0

def test_planner_rejects_unsafe_one_month_but_accepts_multi():
    state = FinancialState(
        user_id="u1", request_date=date(2026, 9, 15), home_currency="USD",
        current_available_balance=Decimal("600"), minimum_balance_to_keep=Decimal("100"),
        recurring_income=[
            RecurringPattern(
                user_id="u1", category="salary", direction="credit", average_amount=Decimal("1000"),
                currency="USD", frequency_days=30, typical_day_of_month=1, flexibility="fixed",
                minimum_allowed_amount=None, representative_event_id="e2",
                last_date=date(2026, 9, 1), next_expected_date=date(2026, 10, 1), is_salary=True
            )
        ],
        recurring_expenses=[
            RecurringPattern(
                user_id="u1", category="rent", direction="debit", average_amount=Decimal("300"),
                currency="USD", frequency_days=100, typical_day_of_month=None, flexibility="fixed",
                minimum_allowed_amount=None, representative_event_id="e1", 
                last_date=date(2026, 8, 16), next_expected_date=date(2026, 9, 16), is_salary=False
            )
        ]
    )
    # Requested 500. Balance 600. Rent 300 hits tomorrow.
    # 1-month plan: pay 500 today. Balance 100. Rent hits tomorrow: balance -200 (unsafe).
    # 2-month plan: pay 250 today. Balance 350. Rent hits: balance 50 (unsafe).
    # 3-month plan: pay 166.67 today. Balance 433.33. Rent hits: balance 133.33 (safe).
    plans = generate_payment_plans(state, Decimal("500"), max_months=3)
    assert len(plans) == 1
    assert plans[0]["months"] == 3
    assert plans[0]["monthly_payment"] == 166.67
