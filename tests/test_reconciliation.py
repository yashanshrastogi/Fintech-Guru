from decimal import Decimal
from core.models import FinancialEvent, FinancialProfile
from core.fx import FXConverter
from core.reconciliation import reconcile_events, EventStatus

class MockFXConverter:
    def to_home_currency(self, amount, from_currency, to_currency, date_str):
        return amount

def test_cancelled_event_not_included():
    profile = FinancialProfile(
        user_id="user_1", home_currency="USD", current_available_balance=Decimal("100"), 
        minimum_balance_to_keep=Decimal("10"), financial_priorities=[], expense_categories_to_protect=[], 
        expense_categories_willing_to_reduce=[], expense_categories_willing_to_stop=[], 
        payment_methods_user_will_consider=[], max_installment_months=None
    )
    fx = MockFXConverter()
    events = [
        FinancialEvent(
            event_id="e1", user_id="user_1", event_type="expense", description="test", category="test",
            direction="debit", amount=Decimal("50"), currency="USD", event_date="2026-09-15",
            settlement_date=None, status=EventStatus.CANCELLED, linked_event_id=None, flexibility="fixed", minimum_allowed_amount=None
        )
    ]
    included, res = reconcile_events(events, profile, "2026-09-15", [], fx)
    assert len(included) == 0
    assert "EventStatus.CANCELLED" in res["e1"]

def test_pending_debit_included():
    profile = FinancialProfile(
        user_id="user_1", home_currency="USD", current_available_balance=Decimal("100"), 
        minimum_balance_to_keep=Decimal("10"), financial_priorities=[], expense_categories_to_protect=[], 
        expense_categories_willing_to_reduce=[], expense_categories_willing_to_stop=[], 
        payment_methods_user_will_consider=[], max_installment_months=None
    )
    fx = MockFXConverter()
    events = [
        FinancialEvent(
            event_id="e1", user_id="user_1", event_type="expense", description="test", category="test",
            direction="debit", amount=Decimal("50"), currency="USD", event_date="2026-09-15",
            settlement_date=None, status=EventStatus.PENDING, linked_event_id=None, flexibility="fixed", minimum_allowed_amount=None
        )
    ]
    included, res = reconcile_events(events, profile, "2026-09-15", [], fx)
    assert len(included) == 1

def test_pending_credit_excluded():
    profile = FinancialProfile(
        user_id="user_1", home_currency="USD", current_available_balance=Decimal("100"), 
        minimum_balance_to_keep=Decimal("10"), financial_priorities=[], expense_categories_to_protect=[], 
        expense_categories_willing_to_reduce=[], expense_categories_willing_to_stop=[], 
        payment_methods_user_will_consider=[], max_installment_months=None
    )
    fx = MockFXConverter()
    events = [
        FinancialEvent(
            event_id="e1", user_id="user_1", event_type="income", description="test", category="test",
            direction="credit", amount=Decimal("50"), currency="USD", event_date="2026-09-15",
            settlement_date=None, status=EventStatus.PENDING, linked_event_id=None, flexibility="fixed", minimum_allowed_amount=None
        )
    ]
    included, res = reconcile_events(events, profile, "2026-09-15", [], fx)
    assert len(included) == 0

def test_duplicate_event_superseded():
    profile = FinancialProfile(
        user_id="user_1", home_currency="USD", current_available_balance=Decimal("100"), 
        minimum_balance_to_keep=Decimal("10"), financial_priorities=[], expense_categories_to_protect=[], 
        expense_categories_willing_to_reduce=[], expense_categories_willing_to_stop=[], 
        payment_methods_user_will_consider=[], max_installment_months=None
    )
    fx = MockFXConverter()
    events = [
        FinancialEvent(
            event_id="e1", user_id="user_1", event_type="expense", description="original", category="test",
            direction="debit", amount=Decimal("50"), currency="USD", event_date="2026-09-15",
            settlement_date=None, status=EventStatus.PENDING, linked_event_id=None, flexibility="fixed", minimum_allowed_amount=None
        ),
        FinancialEvent(
            event_id="e2", user_id="user_1", event_type="expense", description="duplicate", category="test",
            direction="debit", amount=Decimal("50"), currency="USD", event_date="2026-09-15",
            settlement_date=None, status=EventStatus.DUPLICATE, linked_event_id="e1", flexibility="fixed", minimum_allowed_amount=None
        )
    ]
    included, res = reconcile_events(events, profile, "2026-09-15", [], fx)
    assert len(included) == 1
    assert included[0].event_id == "e1"  # e1 is retained, e2 is duplicate

def test_settled_supersedes_pending():
    profile = FinancialProfile(
        user_id="user_1", home_currency="USD", current_available_balance=Decimal("100"), 
        minimum_balance_to_keep=Decimal("10"), financial_priorities=[], expense_categories_to_protect=[], 
        expense_categories_willing_to_reduce=[], expense_categories_willing_to_stop=[], 
        payment_methods_user_will_consider=[], max_installment_months=None
    )
    fx = MockFXConverter()
    events = [
        FinancialEvent(
            event_id="e1", user_id="user_1", event_type="expense", description="original", category="test",
            direction="debit", amount=Decimal("50"), currency="USD", event_date="2026-09-15",
            settlement_date=None, status=EventStatus.PENDING, linked_event_id=None, flexibility="fixed", minimum_allowed_amount=None
        ),
        FinancialEvent(
            event_id="e2", user_id="user_1", event_type="expense", description="settled", category="test",
            direction="debit", amount=Decimal("50"), currency="USD", event_date="2026-09-15",
            settlement_date=None, status=EventStatus.SETTLED, linked_event_id="e1", flexibility="fixed", minimum_allowed_amount=None
        )
    ]
    included, res = reconcile_events(events, profile, "2026-09-15", [], fx)
    assert len(included) == 1
    assert included[0].event_id == "e2"  # e1 is amended/superseded by e2
    assert "settled_as_e2" in res["e1"]
