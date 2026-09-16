from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal, engine, Base
from app.models.domain import User, FinancialProfile
import pytest

from app.api.dependencies.auth import get_current_user

client = TestClient(app)

from sqlalchemy.orm import joinedload

def override_get_current_user():
    db = SessionLocal()
    user = db.query(User).options(joinedload(User.profile)).filter(User.user_id == "u1").first()
    db.close()
    return user

app.dependency_overrides[get_current_user] = override_get_current_user

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Ensure test user exists
    user = db.query(User).filter(User.user_id == "u1").first()
    if not user:
        user = User(user_id="u1", username="testuser", hashed_password="hashedpassword")
        profile = FinancialProfile(
            user_id="u1",
            home_currency="USD",
            current_available_balance=1000,
            minimum_balance_to_keep=100,
            max_installment_months=3
        )
        db.add(user)
        db.add(profile)
        db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)

def test_api_deterministic_affordable():
    payload = {
        "description": "test",
        "amount": 500.0,
        "date": "2026-09-15"
    }
    
    response = client.post("/api/v1/affordability/check?user_id=u1", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "affordable_now"
    assert data["plans"][0]["method"] == "full_payment"
    assert float(data["plans"][0]["amount_today"]) == 500.0

from unittest.mock import patch

@patch("app.api.endpoints.assistant.LLMClient")
def test_api_assistant_chat(mock_llm_client):
    mock_instance = mock_llm_client.return_value
    mock_instance.analyze_message.return_value = {
        "intent": "AFFORDABILITY_QUERY",
        "amount": 500.0,
        "description": "laptop"
    }
    
    payload = {
        "user_id": "u1",
        "message": "Can I afford a $500 laptop?"
    }
    
    response = client.post("/api/v1/assistant/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "decision" in data
    assert data["decision"]["status"] == "affordable_now"

