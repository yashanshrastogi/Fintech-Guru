import httpx
import time
import json
import uuid

def test_full_live_session():
    print("--- FINTECH GURU V2: FULL LIVE SCREENING & MONITORING SESSION ---")
    
    base_url = "http://localhost:8000/api/v1"
    
    # Wait for backend
    print("Waiting for backend...")
    for _ in range(10):
        try:
            httpx.get(f"{base_url}/health", timeout=2)
            break
        except:
            time.sleep(2)
    else:
        print("Backend not ready!")
        return
    
    # 1. Registration
    username = f"live_tester_{uuid.uuid4().hex[:6]}"
    password = "secure_password123"
    print(f"\n[*] 1. Registering new user: {username}")
    reg_resp = httpx.post(f"{base_url}/auth/register", json={"username": username, "password": password})
    if reg_resp.status_code != 200:
        print("Registration failed:", reg_resp.text)
        return
    print("  -> Success")
    
    # 2. Login
    print("\n[*] 2. Authenticating via JWT")
    login_resp = httpx.post(f"{base_url}/auth/login", data={"username": username, "password": password})
    if login_resp.status_code != 200:
        print("Login failed:", login_resp.text)
        return
    token = login_resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("  -> Success, Token acquired")
    
    # 3. Fetch User ID
    print("\n[*] 3. Fetching User ID (/auth/me)")
    me_resp = httpx.get(f"{base_url}/auth/me", headers=headers)
    user_id = me_resp.json()["user_id"]
    print(f"  -> Success, User ID: {user_id}")
    
    # 4. Initialize Profile
    print("\n[*] 4. Initializing Financial Profile")
    # GET initializes with 0.0 balance if not exists
    prof_get = httpx.get(f"{base_url}/profile/{user_id}", headers=headers)
    print("  -> Initial Profile:", prof_get.status_code)
    
    # PUT sets the real values
    prof_payload = {
        "home_currency": "USD",
        "current_available_balance": 5000.0,
        "minimum_balance_to_keep": 1500.0,
        "recurring_incomes": [
            {"category": "salary", "direction": "credit", "average_amount": 4000.0, "frequency_days": 30, "is_salary": True}
        ],
        "recurring_expenses": [
            {"category": "rent", "direction": "debit", "average_amount": 1200.0, "frequency_days": 30}
        ],
        "obligations": []
    }
    prof_put = httpx.put(f"{base_url}/profile/{user_id}", json=prof_payload, headers=headers)
    print("  -> Update Profile:", prof_put.status_code)
    
    # 5. Affordability Chat Call
    print("\n[*] 5. Triggering Affordability Engine (Live Qwen3:8b Inference)")
    chat_payload = {
        "message": "Can I afford to buy a $3000 Macbook Pro?",
        "base_request": {
            "mode": "agentic",
            "profile": {
                "user_id": user_id,
                "home_currency": "USD",
                "minimum_balance_to_keep": 1500.0,
                "financial_priorities": [],
                "expense_categories_to_protect": [],
                "expense_categories_willing_to_reduce": [],
                "expense_categories_willing_to_stop": [],
                "payment_methods_user_will_consider": ["full_payment", "installments"],
                "max_installment_months": 12
            },
            "transactions": [],
            "purchase": {
                "request_id": "req-live-1",
                "user_id": user_id,
                "description": "Macbook Pro",
                "request_amount": 3000.0,
                "request_date": "2026-09-16",
                "evidence": []
            }
        }
    }
    
    start_time = time.time()
    chat_resp = httpx.post(f"{base_url}/assistant/chat", json=chat_payload, headers=headers, timeout=60.0)
    end_time = time.time()
    
    print(f"  -> Chat Response ({end_time - start_time:.2f}s): {chat_resp.status_code}")
    if chat_resp.status_code == 200:
        data = chat_resp.json()
        print("     Decision Status:", data["decision"]["status"])
        print("     Explanation:", data["decision"]["explanation"]["summary"])
        print("     Lowest Projected Balance:", data["decision"]["explanation"]["lowest_projected_balance"])
        
    print("\n--- SESSION COMPLETE ---")

if __name__ == "__main__":
    test_full_live_session()
