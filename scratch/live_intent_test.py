import httpx
import uuid
import time
import json

def test_live_intents():
    print("--- LIVE INTENT ROUTING TEST ---")
    base_url = "http://localhost:8000/api/v1"
    
    # Wait for backend
    print("Waiting for backend...")
    for _ in range(15):
        try:
            httpx.get(f"{base_url}/health", timeout=2)
            break
        except:
            time.sleep(2)
    else:
        print("Backend not ready!")
        return
        
    username = f"intent_tester_{uuid.uuid4().hex[:6]}"
    password = "secure_password123"
    httpx.post(f"{base_url}/auth/register", json={"username": username, "password": password})
    login_resp = httpx.post(f"{base_url}/auth/login", data={"username": username, "password": password})
    token = login_resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    user_id = httpx.get(f"{base_url}/auth/me", headers=headers).json()["user_id"]
    
    print("\n1. Test GREETING (no decision)")
    r1 = httpx.post(f"{base_url}/assistant/chat", json={"message": "hi there!"}, headers=headers, timeout=120.0)
    d1 = r1.json()
    print(f"Intent: {d1.get('intent')}, Decision: {'YES' if d1.get('decision') else 'NO'}")
    assert d1.get('intent') == 'GREETING'
    assert d1.get('decision') is None
    
    print("\n2. Test PROFILE_UPDATE")
    r2 = httpx.post(f"{base_url}/assistant/chat", json={"message": "My balance is $80000, minimum reserve $20000. My monthly income is 45000 and expenses are 30000"}, headers=headers, timeout=120.0)
    d2 = r2.json()
    print(f"Intent: {d2.get('intent')}, Decision: {'YES' if d2.get('decision') else 'NO'}")
    assert d2.get('intent') == 'PROFILE_UPDATE'
    assert d2.get('decision') is None
    
    prof_check = httpx.get(f"{base_url}/profile/{user_id}", headers=headers).json()
    print(f"Updated Balance: {prof_check['current_available_balance']}")
    assert prof_check['current_available_balance'] == 80000.0
    
    print("\n3. Test AFFORDABILITY_QUERY")
    r3 = httpx.post(f"{base_url}/assistant/chat", json={"message": "Can I afford a $50000 laptop?"}, headers=headers, timeout=60.0)
    d3 = r3.json()
    print(f"Intent: {d3.get('intent')}, Decision Status: {d3.get('decision', {}).get('status')}")
    assert d3.get('intent') == 'AFFORDABILITY_QUERY'
    assert d3.get('decision') is not None
    
    print("\n4. Test WHAT_IF")
    r4 = httpx.post(f"{base_url}/assistant/chat", json={"message": "What if I wait 30 days?"}, headers=headers, timeout=60.0)
    d4 = r4.json()
    print(f"Intent: {d4.get('intent')}, Decision Status: {d4.get('decision', {}).get('status')}")
    assert d4.get('intent') == 'WHAT_IF'
    assert d4.get('decision') is not None

    print("\n5. Test EXPLANATION")
    r5 = httpx.post(f"{base_url}/assistant/chat", json={"message": "Why?"}, headers=headers, timeout=60.0)
    d5 = r5.json()
    print(f"Intent: {d5.get('intent')}, Decision: {'YES' if d5.get('decision') else 'NO'}, Reply: {d5.get('reply')[:50]}...")
    assert d5.get('intent') == 'EXPLANATION'
    assert d5.get('decision') is None

    print("\n--- TESTS PASSED ---")

if __name__ == "__main__":
    test_live_intents()
