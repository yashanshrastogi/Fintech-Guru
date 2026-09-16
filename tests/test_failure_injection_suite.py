import pytest
from decimal import Decimal
from datetime import date
from unittest import mock

from app.engine import deterministic_pipeline, AffordabilityRequest
from core.models import UserProfile, PurchaseRequest, CandidatePlan
from validation.boundary import SafetyViolationError

def create_base_req() -> AffordabilityRequest:
    return AffordabilityRequest(
        mode="deterministic",
        profile=UserProfile(
            user_id="u1", home_currency="USD", current_available_balance=Decimal("1000"),
            minimum_balance_to_keep=Decimal("100")
        ),
        transactions=[],
        purchase=PurchaseRequest(
            request_id="req1", user_id="u1", description="Test", request_amount=Decimal("900"),
            request_date=date(2026, 9, 15)
        )
    )

def test_fault_injection_optimizer():
    # If optimizer falsely claims a high safe amount
    req = create_base_req()
    with mock.patch("app.engine.find_max_safe_amount", return_value=Decimal("5000")):
        req.purchase.request_amount = Decimal("1000")
        res = deterministic_pipeline(req)
        # Boundary should catch it and reject it to not_affordable
        assert res["status"] == "not_affordable"
        # The explanation still carries the optimizer's result, but no plans are valid.

def test_fault_injection_planner():
    # If planner proposes an unsafe plan
    req = create_base_req()
    req.purchase.request_amount = Decimal("1000") # not safe for full payment
    
    # generate_payment_plans returns dicts with 'months' and 'monthly_payment'
    bad_raw_plan = {"months": 1, "monthly_payment": 1000.0, "lowest_projected_balance": 500.0, "limiting_date": "2026-09-15"}
    
    with mock.patch("app.engine.generate_payment_plans", return_value=[bad_raw_plan]):
        res = deterministic_pipeline(req)
        # Boundary should independently simulate this and realize 1000 drops balance to 0 < 100.
        assert res["status"] == "not_affordable"

def test_fault_injection_simulator_boundary():
    # If the boundary's internal simulation fails, it raises an error, caught as rejected.
    req = create_base_req()
    
    with mock.patch("validation.boundary.simulate_cashflow", side_effect=ValueError("Sim crash")):
        res = deterministic_pipeline(req)
        assert res["status"] == "not_affordable"
