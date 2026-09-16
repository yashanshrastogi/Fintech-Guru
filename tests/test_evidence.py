from typing import Dict, Any
from llm.client import LLMClient

class MockLLMClient(LLMClient):
    def __init__(self, raw_response: str):
        super().__init__()
        self.raw_response = raw_response
        
    def _call_llm(self, system: str, user: str) -> str:
        return self.raw_response

def test_strict_json_parsing_valid():
    client = MockLLMClient('{"extracted_salary": 1500.50, "extracted_amount": null, "cancellation_request": true}')
    result = client.extract_evidence("I got a raise to 1500.50 and cancel my trip")
    
    assert result["extracted_salary"] == 1500.50
    assert result["extracted_amount"] is None
    assert result["cancellation_request"] is True

def test_strict_json_parsing_conversational_wrapper():
    # LLMs often hallucinate markdown wrappers even when format="json"
    client = MockLLMClient('```json\n{"extracted_salary": 2000, "extracted_amount": 50, "cancellation_request": false}\n```')
    result = client.extract_evidence("My salary is 2000 and the bill is 50")
    
    assert result["extracted_salary"] == 2000.0
    assert result["extracted_amount"] == 50.0
    assert result["cancellation_request"] is False

def test_strict_json_parsing_malformed():
    # Invalid JSON should fallback safely to default empty state
    client = MockLLMClient('Here is your json: {extracted_salary: 100')
    result = client.extract_evidence("salary is 100")
    
    assert result["extracted_salary"] is None
    assert result["extracted_amount"] is None
    assert result["cancellation_request"] is False
