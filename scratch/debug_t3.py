import json
from decimal import Decimal
from datetime import date
from core.models import UserProfile, BaseEvent
from app.main import AffordabilityRequest
from llm.router import route_request
from app.main import deterministic_pipeline, multi_agent_fallback_handler
from forecasting.simulator import simulate_cashflow
from app.main import build_canonical_state

def test_template_3():
    profile = UserProfile(
        user_id="u_20",
        home_currency="USD",
        current_available_balance=Decimal("5000.0"),
        minimum_balance_to_keep=Decimal("1000.0"),
        payment_methods_user_will_consider=["full_payment", "installments"],
        max_installment_months=3
    )
    
    events = [
        BaseEvent(
            event_id="evt_s_20",
            user_id="u_20",
            description="Salary",
            category="salary",
            amount=Decimal("3000.0"),
            currency="USD",
            event_date="2026-10-01",
            status="settled",
            event_type="income"
        )
    ]
    
    req = AffordabilityRequest(
        mode="deterministic",
        profile=profile,
        transactions=events,
        purchase={
            "request_id": "req_20",
            "user_id": "u_20",
            "description": "Buy a car repair.",
            "request_amount": Decimal("4500.0"),
            "request_date": "2026-09-16",
            "evidence": []
        }
    )
    
    state = build_canonical_state(req)
    print("State Balance:", state.current_available_balance)
    print("State Min Balance:", state.minimum_balance_to_keep)
    
    # baseline
    baseline = simulate_cashflow(state)
    print("Baseline:")
    for b in baseline[:16]:
        print(f"  {b.date}: {b.closing_balance}")
        
    res = route_request("deterministic", deterministic_pipeline, multi_agent_fallback_handler, req)
    print("Decision:", res["status"])
    print("Safe Amount:", res["explanation"].safe_amount_today)

if __name__ == "__main__":
    test_template_3()
