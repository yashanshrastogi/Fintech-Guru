import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_health():
    print("Testing /health...")
    resp = requests.get(f"{BASE_URL}/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    print("Health OK")

def test_profile_and_history():
    print("Testing /profile and /history...")
    user_id = "u_test_docker"
    # GET profile
    resp = requests.get(f"{BASE_URL}/profile/{user_id}")
    assert resp.status_code == 200
    
    # PUT profile
    payload = {
        "home_currency": "USD",
        "current_available_balance": 15000.0,
        "minimum_balance_to_keep": 2000.0,
        "recurring_incomes": [],
        "recurring_expenses": [],
        "obligations": []
    }
    resp = requests.put(f"{BASE_URL}/profile/{user_id}", json=payload)
    assert resp.status_code == 200
    
    # GET history
    resp = requests.get(f"{BASE_URL}/profile/{user_id}/history")
    assert resp.status_code == 200
    print("Profile & History OK")

def test_chat():
    print("Testing /assistant/chat...")
    payload = {
        "message": "Can I afford a $1500 laptop next week?",
        "user_id": "u_test_docker"
    }
    resp = requests.post(f"{BASE_URL}/assistant/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "decision" in data
    print(f"Chat OK, Status: {data['decision']['status']}")

def test_what_if():
    print("Testing /what-if/...")
    
    req_payload = {
        "requested_amount": 1500.0,
        "request_date": "2024-10-01"
    }
    resp = requests.post(f"{BASE_URL}/what-if/?user_id=u_test_docker", json=req_payload)
    assert resp.status_code == 200
    print("What-If OK")

if __name__ == "__main__":
    time.sleep(2) # Give backend time to start
    test_health()
    test_profile_and_history()
    test_chat()
    test_what_if()
    print("All E2E Docker integration tests passed.")
