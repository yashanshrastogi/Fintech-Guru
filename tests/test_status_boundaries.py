from decimal import Decimal
from datetime import date, timedelta
import pytest

from core.models import UserProfile, PurchaseRequest, ExpenseEvent, IncomeEvent
from app.engine import deterministic_pipeline, AffordabilityRequest

def create_base_request(req_amt: str, min_balance: str, current_balance: str) -> AffordabilityRequest:
    return AffordabilityRequest(
        mode="deterministic",
        profile=UserProfile(
            user_id="u1",
            home_currency="USD",
            current_available_balance=Decimal(current_balance),
            minimum_balance_to_keep=Decimal(min_balance)
        ),
        transactions=[],
        purchase=PurchaseRequest(
            request_id="req1",
            user_id="u1",
            description="Test purchase",
            request_amount=Decimal(req_amt),
            request_date=date(2026, 9, 15)
        )
    )

def add_recurring_expense(req: AffordabilityRequest, amount: str, last_date: date, category: str = "rent"):
    # To trigger recurring logic, we need at least 2 events 30 days apart
    req.transactions.append(ExpenseEvent(
        event_id=f"exp_1_{category}", user_id="u1", description=category, category=category,
        amount=Decimal(amount), event_date=last_date - timedelta(days=30), status="settled"
    ))
    req.transactions.append(ExpenseEvent(
        event_id=f"exp_2_{category}", user_id="u1", description=category, category=category,
        amount=Decimal(amount), event_date=last_date, status="settled"
    ))

def add_recurring_income(req: AffordabilityRequest, amount: str, last_date: date):
    req.transactions.append(IncomeEvent(
        event_id="inc_1", user_id="u1", description="salary", category="salary", source="Employer", is_salary=True,
        amount=Decimal(amount), event_date=last_date - timedelta(days=30), status="settled"
    ))
    req.transactions.append(IncomeEvent(
        event_id="inc_2", user_id="u1", description="salary", category="salary", source="Employer", is_salary=True,
        amount=Decimal(amount), event_date=last_date, status="settled"
    ))

def test_exact_affordability_threshold():
    req = create_base_request(req_amt="900", min_balance="100", current_balance="1000")
    res = deterministic_pipeline(req)
    assert res["status"] == "affordable_now"
    
def test_epsilon_below_threshold():
    req = create_base_request(req_amt="900.01", min_balance="100", current_balance="1000")
    res = deterministic_pipeline(req)
    assert res["status"] != "affordable_now"

def test_epsilon_above_threshold():
    req = create_base_request(req_amt="899.99", min_balance="100", current_balance="1000")
    res = deterministic_pipeline(req)
    assert res["status"] == "affordable_now"

def test_salary_date_boundary_before():
    req = create_base_request(req_amt="50", min_balance="100", current_balance="100")
    add_recurring_income(req, "1000", date(2026, 8, 16)) # Next is 9/15 but since frequency is 30, it might be 9/15. Wait, 8/16 + 30 days is 9/15. 
    # Let's put last_date on 8/17 to make next date 9/16
    req.transactions.clear()
    add_recurring_income(req, "1000", date(2026, 8, 17))
    res = deterministic_pipeline(req)
    assert res["status"] != "affordable_now" 

def test_salary_date_boundary_after():
    req = create_base_request(req_amt="50", min_balance="100", current_balance="100")
    add_recurring_income(req, "1000", date(2026, 8, 15)) # Next is 9/14 (already passed, wait! The simulator projects from request_date. If next expected is past, does it project today?)
    res = deterministic_pipeline(req)
    # The salary should make it affordable
    assert res["status"] == "affordable_with_plan"

def test_expense_date_boundary_after():
    req = create_base_request(req_amt="900", min_balance="100", current_balance="1000")
    add_recurring_expense(req, "500", date(2026, 8, 17)) # next is 9/16
    res = deterministic_pipeline(req)
    assert res["status"] != "affordable_now"
    
def test_expense_date_boundary_way_future():
    req = create_base_request(req_amt="900", min_balance="100", current_balance="1000")
    # rent every 365 days
    req.transactions.append(ExpenseEvent(
        event_id="rent1", user_id="u1", description="rent", category="rent",
        amount=Decimal("5000"), event_date=date(2024, 12, 17), status="settled"
    ))
    req.transactions.append(ExpenseEvent(
        event_id="rent2", user_id="u1", description="rent", category="rent",
        amount=Decimal("5000"), event_date=date(2025, 12, 17), status="settled"
    ))
    res = deterministic_pipeline(req)
    assert res["status"] == "affordable_now"
