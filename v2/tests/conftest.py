"""
V2 Test Suite - conftest.py
Shared fixtures for all V2 tests.
"""
import sys
from pathlib import Path
from decimal import Decimal
from datetime import date
from typing import List, Optional
import pytest

# Add code directory to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "code"))


@pytest.fixture
def sample_profile():
    from models import FinancialProfile
    return FinancialProfile(
        user_id="test_user_01",
        home_currency="IDR",
        current_available_balance=Decimal("10_000_000"),
        minimum_balance_to_keep=Decimal("1_000_000"),
        financial_priorities=["education", "debt_repayment"],
        expense_categories_to_protect=["rent", "groceries"],
        expense_categories_willing_to_reduce=["entertainment"],
        expense_categories_willing_to_stop=["streaming"],
        payment_methods_user_will_consider=["full_payment", "installments", "partial_payment"],
        max_installment_months=12,
    )


@pytest.fixture
def request_date():
    return date(2026, 9, 1)


@pytest.fixture
def sample_request(request_date):
    from models import Request
    return Request(
        request_id="test_req_01",
        user_id="test_user_01",
        request_date=request_date,
        request_type="purchase",
        requested_amount=Decimal("3_000_000"),
        desired_completion_date=date(2026, 11, 30),
        allows_partial_payment=True,
        request_text="Can I buy this laptop?",
    )


def make_event(
    event_id="evt_01",
    user_id="test_user_01",
    event_type="expense",
    description="Test event",
    category="groceries",
    direction="debit",
    amount=Decimal("500_000"),
    currency="IDR",
    event_date=date(2026, 8, 1),
    settlement_date=None,
    status="settled",
    linked_event_id=None,
    flexibility="fixed",
    minimum_allowed_amount=None,
):
    from models import FinancialEvent
    e = FinancialEvent(
        event_id=event_id,
        user_id=user_id,
        event_type=event_type,
        description=description,
        category=category,
        direction=direction,
        amount=amount,
        currency=currency,
        event_date=event_date,
        settlement_date=settlement_date,
        status=status,
        linked_event_id=linked_event_id,
        flexibility=flexibility,
        minimum_allowed_amount=minimum_allowed_amount,
    )
    e.amount_home_currency = amount  # same currency for simplicity
    return e


def make_recurring_events(
    category="groceries",
    direction="debit",
    amounts=None,
    base_date=date(2026, 1, 1),
    freq_days=30,
    n=6,
    flexibility="stoppable",
    status="settled",
):
    """Create a series of recurring events with given amounts and frequency."""
    if amounts is None:
        amounts = [Decimal("500_000")] * n

    events = []
    for i in range(n):
        evt_date = base_date + __import__("datetime").timedelta(days=i * freq_days)
        amt = amounts[i] if i < len(amounts) else amounts[-1]
        events.append(make_event(
            event_id=f"evt_{category}_{i:02d}",
            category=category,
            direction=direction,
            amount=amt,
            event_date=evt_date,
            status=status,
            flexibility=flexibility,
        ))
    return events


@pytest.fixture
def mock_ollama_client(monkeypatch):
    """Mock OllamaClient to avoid real inference in tests."""
    import ollama_client as oc

    class MockClient:
        is_healthy = False
        detected_model = "mock_model"
        base_url = "http://localhost:11434"

        def check_health(self):
            return False, None

        def chat_completion(self, *args, **kwargs):
            return None, 0.0, 0, 0

    monkeypatch.setattr(oc, "ollama_client", MockClient())
    return MockClient()
