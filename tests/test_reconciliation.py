import pytest
from decimal import Decimal
from datetime import date
from core.models import BaseEvent, UserProfile
from core.reconciliation import reconcile_events, EventStatus

def test_cancelled_event_not_included():
    profile = UserProfile(
        user_id="user_1", home_currency="USD", current_available_balance=Decimal("100"), 
        minimum_balance_to_keep=Decimal("10"), financial_priorities=[], expense_categories_to_protect=[], 
        expense_categories_willing_to_reduce=[], expense_categories_willing_to_stop=[], 
        payment_methods_user_will_consider=[], max_installment_months=None
    )
    events = [
        BaseEvent(
            event_id="e1", user_id="user_1", event_type="expense", description="test", category="test",
            amount=Decimal("50"), currency="USD", event_date=date(2026, 9, 15),
            settlement_date=None, status=EventStatus.CANCELLED, linked_event_id=None
        )
    ]
    included, res = reconcile_events(events, profile, date(2026, 9, 15))
    assert len(included) == 0
    assert "excluded_status_cancelled" in res["e1"]

def test_pending_debit_included():
    profile = UserProfile(
        user_id="user_1", home_currency="USD", current_available_balance=Decimal("100"), 
        minimum_balance_to_keep=Decimal("10")
    )
    events = [
        BaseEvent(
            event_id="e1", user_id="user_1", event_type="expense", description="test", category="test",
            amount=Decimal("50"), currency="USD", event_date=date(2026, 9, 15),
            settlement_date=None, status=EventStatus.PENDING, linked_event_id=None
        )
    ]
    included, res = reconcile_events(events, profile, date(2026, 9, 15))
    assert len(included) == 1
    assert "included" in res["e1"]

def test_pending_credit_excluded():
    profile = UserProfile(
        user_id="user_1", home_currency="USD", current_available_balance=Decimal("100"), 
        minimum_balance_to_keep=Decimal("10")
    )
    events = [
        BaseEvent(
            event_id="e1", user_id="user_1", event_type="income", description="test", category="test",
            amount=Decimal("50"), currency="USD", event_date=date(2026, 9, 15),
            settlement_date=None, status=EventStatus.PENDING, linked_event_id=None
        )
    ]
    included, res = reconcile_events(events, profile, date(2026, 9, 15))
    assert len(included) == 0

def test_duplicate_event_superseded():
    profile = UserProfile(
        user_id="user_1", home_currency="USD", current_available_balance=Decimal("100"), 
        minimum_balance_to_keep=Decimal("10")
    )
    events = [
        BaseEvent(
            event_id="e1", user_id="user_1", event_type="expense", description="original", category="test",
            amount=Decimal("50"), currency="USD", event_date=date(2026, 9, 15),
            status=EventStatus.PENDING
        ),
        BaseEvent(
            event_id="e2", user_id="user_1", event_type="expense", description="duplicate", category="test",
            amount=Decimal("50"), currency="USD", event_date=date(2026, 9, 15),
            status=EventStatus.DUPLICATE, linked_event_id="e1"
        )
    ]
    included, res = reconcile_events(events, profile, date(2026, 9, 15))
    assert len(included) == 1
    assert included[0].event_id == "e1"  # e1 is retained, e2 is duplicate

def test_settled_supersedes_pending():
    profile = UserProfile(
        user_id="user_1", home_currency="USD", current_available_balance=Decimal("100"), 
        minimum_balance_to_keep=Decimal("10")
    )
    events = [
        BaseEvent(
            event_id="e1", user_id="user_1", event_type="expense", description="original", category="test",
            amount=Decimal("50"), currency="USD", event_date=date(2026, 9, 15),
            status=EventStatus.PENDING
        ),
        BaseEvent(
            event_id="e2", user_id="user_1", event_type="expense", description="settled", category="test",
            amount=Decimal("50"), currency="USD", event_date=date(2026, 9, 15),
            status=EventStatus.SETTLED, linked_event_id="e1"
        )
    ]
    included, res = reconcile_events(events, profile, date(2026, 9, 15))
    assert len(included) == 1
    assert included[0].event_id == "e2"  # e1 is amended/superseded by e2
    assert "settled_as_e2" in res["e1"]
