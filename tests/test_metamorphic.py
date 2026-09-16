from decimal import Decimal
from datetime import date, timedelta
import pytest
import copy
from typing import Dict, Any

from core.models import UserProfile, PurchaseRequest, ExpenseEvent, IncomeEvent
from app.engine import deterministic_pipeline, AffordabilityRequest

def create_base_req(balance="2000", min_balance="100", req_amt="500") -> AffordabilityRequest:
    return AffordabilityRequest(
        mode="deterministic",
        profile=UserProfile(
            user_id="u1", home_currency="USD", current_available_balance=Decimal(balance),
            minimum_balance_to_keep=Decimal(min_balance)
        ),
        transactions=[],
        purchase=PurchaseRequest(
            request_id="req1", user_id="u1", description="Test", request_amount=Decimal(req_amt),
            request_date=date(2026, 9, 15)
        )
    )

def get_safe_amt(req: AffordabilityRequest) -> Decimal:
    res = deterministic_pipeline(req)
    return res["explanation"].safe_amount_today

# A. Increase current balance -> safe amount must not decrease.
def test_metamorphic_a_increase_balance():
    req1 = create_base_req(balance="1000")
    req2 = create_base_req(balance="1500")
    assert get_safe_amt(req2) >= get_safe_amt(req1)

# B. Increase minimum required balance -> safe amount must not increase.
def test_metamorphic_b_increase_min_balance():
    req1 = create_base_req(min_balance="100")
    req2 = create_base_req(min_balance="500")
    assert get_safe_amt(req2) <= get_safe_amt(req1)

# C. Remove a legitimate expense -> safe amount should not become lower solely because of that removal.
def test_metamorphic_c_remove_expense():
    req1 = create_base_req()
    req1.transactions.append(ExpenseEvent(
        event_id="exp1", user_id="u1", description="rent", category="rent",
        amount=Decimal("500"), event_date=date(2026, 9, 16), status="settled" # It's a one off in the future? Wait, reconciled_events uses settlement_date
    ))
    
    req2 = create_base_req()
    
    assert get_safe_amt(req2) >= get_safe_amt(req1)

# D. Add a future mandatory expense -> safe amount cannot increase solely due to that addition.
def test_metamorphic_d_add_future_expense():
    req1 = create_base_req()
    req2 = create_base_req()
    req2.transactions.append(ExpenseEvent(
        event_id="exp1", user_id="u1", description="rent", category="rent",
        amount=Decimal("500"), event_date=date(2026, 9, 16), status="settled"
    ))
    
    assert get_safe_amt(req2) <= get_safe_amt(req1)

# E. Increase purchase amount while state is fixed -> affordability cannot become easier.
def test_metamorphic_e_increase_purchase_amount():
    req1 = create_base_req(req_amt="500")
    req2 = create_base_req(req_amt="1000")
    
    res1 = deterministic_pipeline(req1)
    res2 = deterministic_pipeline(req2)
    
    rank = {"affordable_now": 2, "affordable_with_plan": 1, "not_affordable": 0}
    assert rank[res2["status"]] <= rank[res1["status"]]

# F. Shift salary earlier while preserving amount -> should not reduce affordability solely due to timing.
def test_metamorphic_f_shift_salary_earlier():
    req1 = create_base_req()
    req1.transactions.append(IncomeEvent(
        event_id="inc1", user_id="u1", description="salary", category="salary", source="Emp", is_salary=True,
        amount=Decimal("1000"), event_date=date(2026, 9, 20), status="settled"
    ))
    req2 = create_base_req()
    req2.transactions.append(IncomeEvent(
        event_id="inc1", user_id="u1", description="salary", category="salary", source="Emp", is_salary=True,
        amount=Decimal("1000"), event_date=date(2026, 9, 16), status="settled"
    ))
    
    assert get_safe_amt(req2) >= get_safe_amt(req1)

# G. Duplicate an already reconciled transaction -> final state should remain unchanged.
# The reconciliation engine should catch duplicate IDs.
def test_metamorphic_g_duplicate_transaction():
    req1 = create_base_req()
    e = ExpenseEvent(
        event_id="exp1", user_id="u1", description="rent", category="rent",
        amount=Decimal("500"), event_date=date(2026, 9, 16), status="settled"
    )
    req1.transactions.append(e)
    
    req2 = create_base_req()
    req2.transactions.append(e)
    req2.transactions.append(copy.deepcopy(e)) # Duplicate event ID
    
    assert get_safe_amt(req2) == get_safe_amt(req1)

# H. Cancel a future recurring expense -> its future cash-flow effect must disappear.
def test_metamorphic_h_cancel_recurring():
    req1 = create_base_req()
    # Rent on 8/16 and 7/17 -> recur on 9/15
    req1.transactions.append(ExpenseEvent(
        event_id="r1", user_id="u1", description="rent", category="rent",
        amount=Decimal("500"), event_date=date(2026, 7, 17), status="settled"
    ))
    req1.transactions.append(ExpenseEvent(
        event_id="r2", user_id="u1", description="rent", category="rent",
        amount=Decimal("500"), event_date=date(2026, 8, 16), status="settled"
    ))
    
    req2 = copy.deepcopy(req1)
    req2.profile.financial_priorities = ["cancel_override:rent"]
    
    # After cancellation, safe amount should be higher
    assert get_safe_amt(req2) > get_safe_amt(req1)
