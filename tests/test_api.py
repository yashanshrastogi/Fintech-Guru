from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal, engine, Base
from app.models.domain import User, FinancialProfile
import pytest

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Ensure test user exists
    user = db.query(User).filter(User.user_id == "u1").first()
    if not user:
        user = User(user_id="u1")
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

def test_api_assistant_chat():
    payload = {
        "user_id": "u1",
        "message": "Can I afford a $500 laptop?"
    }
    
    response = client.post("/api/v1/assistant/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "decision" in data
    assert data["decision"]["status"] == "affordable_now"

