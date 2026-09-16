import pytest
from datetime import date
from decimal import Decimal
from core.state import FinancialState
from validation.boundary import enforce_hard_safety_boundary, SafetyViolationError

def test_hard_safety_boundary_passes():
    state = FinancialState(
        user_id="u1", request_date=date(2026, 9, 15), home_currency="USD",
        current_available_balance=Decimal("1000"), minimum_balance_to_keep=Decimal("100")
    )
    # Payment of 500 leaves 500, which is >= 100
    try:
        enforce_hard_safety_boundary(state, [(date(2026, 9, 15), Decimal("500"))])
    except SafetyViolationError:
        pytest.fail("SafetyViolationError raised unexpectedly!")

def test_hard_safety_boundary_fails():
    state = FinancialState(
        user_id="u1", request_date=date(2026, 9, 15), home_currency="USD",
        current_available_balance=Decimal("500"), minimum_balance_to_keep=Decimal("100")
    )
    # Payment of 500 leaves 0, which is < 100
    with pytest.raises(SafetyViolationError, match="violates the hard safety boundary"):
        enforce_hard_safety_boundary(state, [(date(2026, 9, 15), Decimal("500"))])
