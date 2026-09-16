from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api_deterministic_affordable():
    payload = {
        "user_id": "u1",
        "request_amount": 500,
        "request_date": "2026-09-15",
        "mode": "deterministic",
        "profile": {
            "current_available_balance": 1000,
            "minimum_balance_to_keep": 100,
            "max_installment_months": 3
        },
        "recurring_events": []
    }
    
    response = client.post("/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "affordable_now"
    assert data["method"] == "full_payment"
    assert data["amount"] == 500.0

def test_api_multi_agent_fallback():
    payload = {
        "user_id": "u1",
        "request_amount": 500,
        "request_date": "2026-09-15",
        "mode": "agentic",  # Use V1 alias
        "profile": {
            "current_available_balance": 1000,
            "minimum_balance_to_keep": 100,
            "max_installment_months": 3
        },
        "recurring_events": []
    }
    
    response = client.post("/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "affordable_now"

def test_api_invalid_mode_rejected():
    payload = {
        "user_id": "u1",
        "request_amount": 500,
        "request_date": "2026-09-15",
        "mode": "heuristic",
        "profile": {
            "current_available_balance": 1000,
            "minimum_balance_to_keep": 100,
            "max_installment_months": 3
        },
        "recurring_events": []
    }
    
    response = client.post("/evaluate", json=payload)
    assert response.status_code == 400
    assert "Unrecognized routing mode" in response.json()["detail"]
