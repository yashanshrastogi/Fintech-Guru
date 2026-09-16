import sys
import time
from app.main import AffordabilityRequest
from core.models import UserProfile, BaseEvent
from llm.router import route_request
from app.main import deterministic_pipeline, multi_agent_fallback_handler
from decimal import Decimal

# Setup base profile
profile = UserProfile(
    user_id="u1",
    home_currency="USD",
    minimum_balance_to_keep=Decimal("1500.0"),
    financial_priorities=[],
    expense_categories_to_protect=[],
    expense_categories_willing_to_reduce=[],
    expense_categories_willing_to_stop=[],
    payment_methods_user_will_consider=["full_payment"],
    max_installment_months=3
)

events = [
    BaseEvent(
        event_id="e1",
        user_id="u1",
        description="Salary",
        category="salary",
        amount=Decimal("60000.0"), # Original salary
        currency="USD",
        event_date="2026-10-01",
        status="settled",
        event_type="income"
    )
]

req = AffordabilityRequest(
    mode="agentic", # Use router
    profile=profile,
    transactions=events,
    purchase={
        "request_id": "req_evidence_01",
        "user_id": "u1",
        "description": "My salary increased from 60,000 to 70,000 starting next month.",
        "request_amount": Decimal("0.0"),
        "request_date": "2026-09-16",
        "evidence": []
    }
)

start = time.time()
print("Sending request through router...")

result = route_request(
    mode=req.mode,
    deterministic_handler=deterministic_pipeline,
    multi_agent_handler=multi_agent_fallback_handler,
    req=req
)

latency = (time.time() - start) * 1000

print(f"\n--- INTEGRATION TEST RESULTS ---")
print(f"Latency: {latency:.2f} ms")
print(f"Final Decision: {result['status']}")
print(f"Explanation: {result['explanation'].summary}")

# We should also see if it used Qwen by checking if the salary event was amended.
