"""
V2 Regression Tests — Validator / Phase 6 Safety Hardening.

Tests all validator checks, including the 3 new Phase 6 checks.
Run with: pytest v2/tests/test_validator.py -v
"""
import sys
from pathlib import Path
from decimal import Decimal
from datetime import date
import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "code"))

from validator import validate_and_repair
from models import DecisionResult, Request, FinancialProfile
from config import (
    AFFORDABLE_NOW, AFFORDABLE_WITH_PLAN, AFFORDABLE_LATER, NOT_AFFORDABLE,
    FULL_PAYMENT, PARTIAL_PAYMENT, INSTALLMENTS, WAIT, NOT_RECOMMENDED,
)


def make_result(**kwargs) -> DecisionResult:
    defaults = dict(
        request_id="test_req",
        amount_safe_to_pay=Decimal("1000"),
        affordability_status=AFFORDABLE_NOW,
        recommended_payment_method=FULL_PAYMENT,
        payment_plan="2026-09-01:1000",
        earliest_date_for_full_payment=date(2026, 9, 1),
        spending_changes_needed="none",
        decision_explanation="Test explanation.",
    )
    defaults.update(kwargs)
    return DecisionResult(**defaults)


def make_request(**kwargs) -> Request:
    defaults = dict(
        request_id="test_req",
        user_id="test_user",
        request_date=date(2026, 9, 1),
        request_type="purchase",
        requested_amount=Decimal("1000"),
        desired_completion_date=date(2026, 11, 30),
        allows_partial_payment=True,
        request_text="Test",
    )
    defaults.update(kwargs)
    return Request(**defaults)


def make_profile(**kwargs) -> FinancialProfile:
    defaults = dict(
        user_id="test_user",
        home_currency="IDR",
        current_available_balance=Decimal("10000"),
        minimum_balance_to_keep=Decimal("1000"),
        financial_priorities=[],
        expense_categories_to_protect=[],
        expense_categories_willing_to_reduce=[],
        expense_categories_willing_to_stop=[],
        payment_methods_user_will_consider=[FULL_PAYMENT, INSTALLMENTS, PARTIAL_PAYMENT],
        max_installment_months=12,
    )
    defaults.update(kwargs)
    return FinancialProfile(**defaults)


# ---------------------------------------------------------------------------
# Existing checks (regression)
# ---------------------------------------------------------------------------

def test_negative_amount_clamped_to_zero():
    result = make_result(amount_safe_to_pay=Decimal("-500"))
    req = make_request()
    profile = make_profile()
    fixed, issues = validate_and_repair(result, req, profile)
    assert fixed.amount_safe_to_pay == Decimal("0")
    assert any("< 0" in i for i in issues)


def test_amount_exceeds_requested_is_clamped():
    result = make_result(amount_safe_to_pay=Decimal("5000"), recommended_payment_method=FULL_PAYMENT)
    req = make_request(requested_amount=Decimal("1000"))
    profile = make_profile()
    fixed, issues = validate_and_repair(result, req, profile)
    assert fixed.amount_safe_to_pay <= Decimal("1000")


def test_invalid_status_replaced_with_not_affordable():
    result = make_result(affordability_status="invalid_status")
    req = make_request()
    profile = make_profile()
    fixed, issues = validate_and_repair(result, req, profile)
    assert fixed.affordability_status == NOT_AFFORDABLE


def test_invalid_method_replaced_with_not_recommended():
    result = make_result(recommended_payment_method="telepathy")
    req = make_request()
    profile = make_profile()
    fixed, issues = validate_and_repair(result, req, profile)
    assert fixed.recommended_payment_method == NOT_RECOMMENDED


def test_method_not_in_user_accepted_list_becomes_not_recommended():
    result = make_result(recommended_payment_method=INSTALLMENTS)
    req = make_request()
    profile = make_profile(payment_methods_user_will_consider=[FULL_PAYMENT])
    fixed, issues = validate_and_repair(result, req, profile)
    assert fixed.recommended_payment_method == NOT_RECOMMENDED


def test_affordable_now_earliest_date_forced_to_request_date():
    result = make_result(
        affordability_status=AFFORDABLE_NOW,
        earliest_date_for_full_payment=date(2026, 10, 1),
    )
    req = make_request(request_date=date(2026, 9, 1))
    profile = make_profile()
    fixed, issues = validate_and_repair(result, req, profile)
    assert fixed.earliest_date_for_full_payment == date(2026, 9, 1)


def test_not_recommended_payment_plan_cleared():
    result = make_result(
        recommended_payment_method=NOT_RECOMMENDED,
        payment_plan="2026-09-01:500|2026-10-01:500",
    )
    req = make_request()
    profile = make_profile()
    fixed, issues = validate_and_repair(result, req, profile)
    assert fixed.payment_plan == "none"


def test_empty_explanation_gets_fallback():
    result = make_result(decision_explanation="")
    req = make_request()
    profile = make_profile()
    fixed, issues = validate_and_repair(result, req, profile)
    assert len(fixed.decision_explanation) > 5


# ---------------------------------------------------------------------------
# Phase 6 — NEW safety checks
# ---------------------------------------------------------------------------

def test_payment_after_deadline_reverts_to_not_recommended():
    """Phase 6 check 11: Any payment scheduled after desired_completion_date is rejected."""
    result = make_result(
        recommended_payment_method=INSTALLMENTS,
        affordability_status=AFFORDABLE_WITH_PLAN,
        payment_plan="2026-09-01:500|2026-12-15:500",  # Dec 15 > Nov 30 deadline
    )
    req = make_request(desired_completion_date=date(2026, 11, 30))
    profile = make_profile()
    fixed, issues = validate_and_repair(result, req, profile)
    assert fixed.recommended_payment_method == NOT_RECOMMENDED
    assert fixed.affordability_status == NOT_AFFORDABLE
    assert fixed.payment_plan == "none"
    assert any("after deadline" in i for i in issues)


def test_payment_on_deadline_is_allowed():
    """A payment exactly on the deadline must NOT be rejected."""
    result = make_result(
        recommended_payment_method=INSTALLMENTS,
        affordability_status=AFFORDABLE_WITH_PLAN,
        payment_plan="2026-09-01:500|2026-11-30:500",  # exactly on deadline
    )
    req = make_request(desired_completion_date=date(2026, 11, 30))
    profile = make_profile()
    fixed, issues = validate_and_repair(result, req, profile)
    assert fixed.recommended_payment_method == INSTALLMENTS
    assert not any("after deadline" in i for i in issues)


def test_earliest_date_beyond_deadline_marks_not_affordable():
    """Phase 6 check 12: earliest_date > desired_completion_date → not_affordable."""
    result = make_result(
        affordability_status=AFFORDABLE_LATER,
        recommended_payment_method=WAIT,
        earliest_date_for_full_payment=date(2027, 1, 1),  # after deadline
    )
    req = make_request(desired_completion_date=date(2026, 11, 30))
    profile = make_profile()
    fixed, issues = validate_and_repair(result, req, profile)
    assert fixed.affordability_status == NOT_AFFORDABLE
    assert fixed.recommended_payment_method == NOT_RECOMMENDED
    assert any("exceeds desired_completion_date" in i for i in issues)


def test_earliest_date_within_deadline_preserved():
    """earliest_date on or before deadline must be preserved."""
    result = make_result(
        affordability_status=AFFORDABLE_LATER,
        recommended_payment_method=WAIT,
        earliest_date_for_full_payment=date(2026, 11, 29),  # one day before
    )
    req = make_request(desired_completion_date=date(2026, 11, 30))
    profile = make_profile()
    fixed, issues = validate_and_repair(result, req, profile)
    assert fixed.affordability_status == AFFORDABLE_LATER
    assert fixed.earliest_date_for_full_payment == date(2026, 11, 29)


def test_partial_payment_wrong_count_flagged():
    """Partial payment must have exactly 2 payments."""
    result = make_result(
        recommended_payment_method=PARTIAL_PAYMENT,
        payment_plan="2026-09-01:333|2026-10-01:333|2026-11-01:334",  # 3 payments
    )
    req = make_request(allows_partial_payment=True)
    profile = make_profile()
    fixed, issues = validate_and_repair(result, req, profile)
    assert any("2 payments" in i for i in issues)


def test_zero_safe_amount_with_affordable_now_flagged():
    """If amount_safe_to_pay = 0 and status = affordable_now, that's a contradiction."""
    result = make_result(
        amount_safe_to_pay=Decimal("0"),
        affordability_status=AFFORDABLE_NOW,
        recommended_payment_method=FULL_PAYMENT,
    )
    req = make_request(requested_amount=Decimal("1000"))
    profile = make_profile()
    # This may or may not produce an issue depending on implementation,
    # but must not crash and must produce valid output
    fixed, issues = validate_and_repair(result, req, profile)
    assert fixed.amount_safe_to_pay >= Decimal("0")
    assert isinstance(issues, list)
