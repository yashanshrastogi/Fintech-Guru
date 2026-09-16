import httpx
import time

def test_api():
    print("Waiting for backend to be ready...")
    time.sleep(3) # Give docker a sec just in case

    print("Registering user...")
    resp = httpx.post("http://localhost:8000/api/v1/auth/register", json={"username": "prod_tester", "password": "secure_password"})
    print("Register Response:", resp.status_code, resp.text)
    
    # It might return 400 if already exists, so we login anyway
    print("Logging in...")
    login_resp = httpx.post("http://localhost:8000/api/v1/auth/login", data={"username": "prod_tester", "password": "secure_password"})
    print("Login Response:", login_resp.status_code, login_resp.text)
    
    token = login_resp.json().get("access_token")
    if not token:
        print("Failed to get token!")
        return
        
    print("Getting user profile via token...")
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = httpx.get("http://localhost:8000/api/v1/auth/me", headers=headers)
    print("Me Response:", me_resp.status_code, me_resp.text)
    
    user_id = me_resp.json()["user_id"]
    
    print("Checking affordability endpoint with Auth...")
    payload = {
        "message": "Can I buy a $1500 laptop?",
        "base_request": {
            "mode": "agentic",
            "profile": {
                "user_id": user_id,
                "home_currency": "USD",
                "minimum_balance_to_keep": 1000,
                "financial_priorities": [],
                "expense_categories_to_protect": [],
                "expense_categories_willing_to_reduce": [],
                "expense_categories_willing_to_stop": [],
                "payment_methods_user_will_consider": ["full_payment"],
                "max_installment_months": 0
            },
            "transactions": [
                {
                    "event_id": "e1",
                    "user_id": user_id,
                    "description": "Salary",
                    "category": "salary",
                    "amount": 5000,
                    "currency": "USD",
                    "event_date": "2026-10-01",
                    "status": "settled",
                    "event_type": "income"
                }
            ],
            "purchase": {
                "request_id": "r1",
                "user_id": user_id,
                "description": "laptop",
                "request_amount": 1500,
                "request_date": "2026-09-15",
                "evidence": []
            }
        }
    }
    afford_resp = httpx.post("http://localhost:8000/api/v1/assistant/chat", json=payload, headers=headers, timeout=20.0)
    print("Chat Response:", afford_resp.status_code, afford_resp.text[:200])

if __name__ == "__main__":
    test_api()
