from decimal import Decimal
from datetime import date, timedelta
import pytest

from core.models import CandidatePlan, RecurringExpense, RecurringIncome, BaseEvent
from core.state import FinancialState
from validation.boundary import enforce_hard_safety_boundary, SafetyViolationError

def create_base_state():
    return FinancialState(
        user_id="u1",
        request_date=date(2026, 9, 15),
        home_currency="USD",
        current_available_balance=Decimal("1000"),
        minimum_balance_to_keep=Decimal("100"),
        recurring_expenses=[
            RecurringExpense(
                user_id="u1", category="rent", direction="debit",
                average_amount=Decimal("500"), currency="USD", frequency_days=30,
                last_date=date(2026, 9, 1), next_expected_date=date(2026, 9, 20)
            )
        ],
        recurring_income=[
            RecurringIncome(
                user_id="u1", category="salary", direction="credit",
                average_amount=Decimal("2000"), currency="USD", frequency_days=30,
                last_date=date(2026, 9, 5), next_expected_date=date(2026, 10, 5),
                is_salary=True, typical_day_of_month=5
            )
        ]
    )

def test_positive_valid_full_payment():
    state = create_base_state()
    # Balance 1000, min 100, rent 500 on 9/20. So max safe is 400.
    req_amt = Decimal("300")
    plan = CandidatePlan(
        plan_id="p1", method="full_payment", amount_today=req_amt,
        schedule=[{"date": date(2026, 9, 15), "amount": req_amt}],
        lowest_projected_balance=Decimal("200"), limiting_date=date(2026, 9, 20),
        safety_margin=Decimal("100"), is_safe=True
    )
    # Should not raise
    enforce_hard_safety_boundary(state, req_amt, plan)

def test_negative_unsafe_full_payment():
    state = create_base_state()
    req_amt = Decimal("500") # Balance 1000, rent 500 -> hits 0 -> violates 100 min
    plan = CandidatePlan(
        plan_id="p1", method="full_payment", amount_today=req_amt,
        schedule=[{"date": date(2026, 9, 15), "amount": req_amt}],
        lowest_projected_balance=Decimal("0"), limiting_date=date(2026, 9, 20),
        safety_margin=Decimal("0"), is_safe=True
    )
    with pytest.raises(SafetyViolationError, match="violates hard safety boundary"):
        enforce_hard_safety_boundary(state, req_amt, plan)

def test_negative_payment_amount():
    state = create_base_state()
    req_amt = Decimal("300")
    plan = CandidatePlan(
        plan_id="p1", method="payment_plan", amount_today=Decimal("-100"),
        schedule=[{"date": date(2026, 9, 15), "amount": Decimal("-100")}],
        lowest_projected_balance=Decimal("200"), limiting_date=date(2026, 9, 20),
        safety_margin=Decimal("100"), is_safe=True
    )
    with pytest.raises(SafetyViolationError, match="cannot be negative"):
        enforce_hard_safety_boundary(state, req_amt, plan)

def test_payment_greater_than_requested():
    state = create_base_state()
    req_amt = Decimal("300")
    plan = CandidatePlan(
        plan_id="p1", method="full_payment", amount_today=Decimal("400"),
        schedule=[{"date": date(2026, 9, 15), "amount": Decimal("400")}],
        lowest_projected_balance=Decimal("100"), limiting_date=date(2026, 9, 20),
        safety_margin=Decimal("0"), is_safe=True
    )
    with pytest.raises(SafetyViolationError, match="cannot exceed requested amount"):
        enforce_hard_safety_boundary(state, req_amt, plan)

def test_minimum_balance_violation():
    state = create_base_state()
    # Artificially raise min balance to force rejection of an otherwise affordable payment
    state.minimum_balance_to_keep = Decimal("900")
    req_amt = Decimal("200")
    plan = CandidatePlan(
        plan_id="p1", method="full_payment", amount_today=req_amt,
        schedule=[{"date": date(2026, 9, 15), "amount": req_amt}],
        lowest_projected_balance=Decimal("300"), limiting_date=date(2026, 9, 20),
        safety_margin=Decimal("0"), is_safe=True
    )
    with pytest.raises(SafetyViolationError, match="violates hard safety boundary"):
        enforce_hard_safety_boundary(state, req_amt, plan)

def test_invalid_installment_schedule():
    state = create_base_state()
    req_amt = Decimal("300")
    plan = CandidatePlan(
        plan_id="p1", method="payment_plan", amount_today=Decimal("150"),
        schedule=[{"date": date(2026, 9, 17), "amount": Decimal("150")},
                  {"date": date(2026, 9, 16), "amount": Decimal("150")}], # Date goes backward
        lowest_projected_balance=Decimal("200"), limiting_date=date(2026, 9, 20),
        safety_margin=Decimal("0"), is_safe=True
    )
    with pytest.raises(SafetyViolationError, match="is not strictly after previous date"):
        enforce_hard_safety_boundary(state, req_amt, plan)

def test_installment_sum_mismatch():
    state = create_base_state()
    req_amt = Decimal("300")
    plan = CandidatePlan(
        plan_id="p1", method="payment_plan", amount_today=Decimal("150"),
        schedule=[{"date": date(2026, 9, 15), "amount": Decimal("150")},
                  {"date": date(2026, 10, 15), "amount": Decimal("100")}], # Sum is 250 != 300
        lowest_projected_balance=Decimal("200"), limiting_date=date(2026, 9, 20),
        safety_margin=Decimal("0"), is_safe=True
    )
    with pytest.raises(SafetyViolationError, match="does not equal requested amount"):
        enforce_hard_safety_boundary(state, req_amt, plan)

def test_deadline_violation():
    state = create_base_state()
    req_amt = Decimal("300")
    plan = CandidatePlan(
        plan_id="p1", method="payment_plan", amount_today=Decimal("150"),
        schedule=[{"date": date(2026, 9, 15), "amount": Decimal("150")},
                  {"date": date(2027, 9, 20), "amount": Decimal("150")}], # Too far in future
        lowest_projected_balance=Decimal("200"), limiting_date=date(2026, 9, 20),
        safety_margin=Decimal("0"), is_safe=True
    )
    with pytest.raises(SafetyViolationError, match="is too far in the future"):
        enforce_hard_safety_boundary(state, req_amt, plan)

def test_cancelled_transaction_safely_ignored():
    state = create_base_state()
    # Overriding with cancellation request
    state.evidence_overrides = {"cancellation_request": True, "cancelled_categories": ["rent"]}
    # If rent (500) is cancelled, we have 1000 balance. We can safely pay 800 without breaching min 100.
    req_amt = Decimal("800")
    plan = CandidatePlan(
        plan_id="p1", method="full_payment", amount_today=req_amt,
        schedule=[{"date": date(2026, 9, 15), "amount": req_amt}],
        lowest_projected_balance=Decimal("200"), limiting_date=date(2026, 9, 20),
        safety_margin=Decimal("100"), is_safe=True
    )
    # Should not raise
    enforce_hard_safety_boundary(state, req_amt, plan)

def test_malformed_candidate():
    state = create_base_state()
    with pytest.raises(SafetyViolationError, match="is not a CandidatePlan object"):
        enforce_hard_safety_boundary(state, Decimal("300"), {"amount_today": 300}) # Passing dict instead of object

def test_invalid_date_format():
    state = create_base_state()
    req_amt = Decimal("300")
    plan = CandidatePlan(
        plan_id="p1", method="full_payment", amount_today=req_amt,
        schedule=[{"date": "2026/09/15", "amount": req_amt}], # Invalid ISO format
        lowest_projected_balance=Decimal("200"), limiting_date=date(2026, 9, 20),
        safety_margin=Decimal("100"), is_safe=True
    )
    with pytest.raises(SafetyViolationError, match="date is malformed"):
        enforce_hard_safety_boundary(state, req_amt, plan)

def test_nan_infinity():
    state = create_base_state()
    req_amt = Decimal("300")
    plan = CandidatePlan.model_construct(
        plan_id="p1", method="full_payment", amount_today=Decimal("NaN"),
        schedule=[{"date": date(2026, 9, 15), "amount": Decimal("NaN")}],
        lowest_projected_balance=Decimal("200"), limiting_date=date(2026, 9, 20),
        safety_margin=Decimal("100"), is_safe=True
    )
    with pytest.raises(SafetyViolationError, match="cannot be NaN or Infinity"):
        enforce_hard_safety_boundary(state, req_amt, plan)

def test_inconsistent_status_method():
    state = create_base_state()
    req_amt = Decimal("300")
    plan = CandidatePlan(
        plan_id="p1", method="full_payment", amount_today=req_amt,
        schedule=[{"date": date(2026, 9, 15), "amount": Decimal("150")},
                  {"date": date(2026, 10, 15), "amount": Decimal("150")}], # full_payment but 2 installments
        lowest_projected_balance=Decimal("200"), limiting_date=date(2026, 9, 20),
        safety_margin=Decimal("100"), is_safe=True
    )
    with pytest.raises(SafetyViolationError, match="must have exactly 1 installment"):
        enforce_hard_safety_boundary(state, req_amt, plan)

def test_failure_injection():
    # Generate a valid candidate and then corrupt it
    state = create_base_state()
    req_amt = Decimal("300")
    plan = CandidatePlan(
        plan_id="p1", method="payment_plan", amount_today=Decimal("150"),
        schedule=[{"date": date(2026, 9, 15), "amount": Decimal("150")},
                  {"date": date(2026, 10, 15), "amount": Decimal("150")}], 
        lowest_projected_balance=Decimal("200"), limiting_date=date(2026, 9, 20),
        safety_margin=Decimal("100"), is_safe=True
    )
    
    # Intentionally corrupt the amount to violate safety
    plan.schedule[0]["amount"] = Decimal("900")
    plan.schedule[1]["amount"] = Decimal("-600") # Sum is 300, but amount is negative!
    
    with pytest.raises(SafetyViolationError, match="cannot be negative"):
        enforce_hard_safety_boundary(state, req_amt, plan)
