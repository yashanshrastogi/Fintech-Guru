from datetime import date
from decimal import Decimal
from core.state import FinancialState
from core.models import RecurringPattern

def test_effective_salary_override():
    state = FinancialState(
        user_id="user_1",
        request_date=date(2026, 9, 15),
        home_currency="USD",
        current_available_balance=Decimal("1000"),
        minimum_balance_to_keep=Decimal("100"),
        recurring_income=[
            RecurringPattern(
                user_id="user_1", category="salary", direction="credit",
                average_amount=Decimal("5000"), currency="USD", frequency_days=30,
                typical_day_of_month=15, flexibility="fixed", minimum_allowed_amount=None,
                representative_event_id="e1", last_date=date(2026, 8, 15), next_expected_date=date(2026, 9, 15),
                is_salary=True
            )
        ],
        evidence_overrides={
            "extracted_salary": 5500.0,
            "cancellation_request": False
        }
    )
    
    # The evidence override should take precedence
    assert state.get_effective_salary() == Decimal("5500.0")

def test_effective_salary_fallback():
    state = FinancialState(
        user_id="user_1",
        request_date=date(2026, 9, 15),
        home_currency="USD",
        current_available_balance=Decimal("1000"),
        minimum_balance_to_keep=Decimal("100"),
        recurring_income=[
            RecurringPattern(
                user_id="user_1", category="salary", direction="credit",
                average_amount=Decimal("5000"), currency="USD", frequency_days=30,
                typical_day_of_month=15, flexibility="fixed", minimum_allowed_amount=None,
                representative_event_id="e1", last_date=date(2026, 8, 15), next_expected_date=date(2026, 9, 15),
                is_salary=True
            )
        ],
        evidence_overrides={
            "extracted_salary": None, # Failed to extract
            "cancellation_request": False
        }
    )
    
    # Should fallback to recurring income pattern
    assert state.get_effective_salary() == Decimal("5000")
