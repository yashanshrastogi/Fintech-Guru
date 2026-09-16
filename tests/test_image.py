from typing import Dict, Any
from evidence.image import _parse_vision_json

def test_vision_strict_json_parsing_valid():
    result = _parse_vision_json('{"extracted_amount": 540.25, "is_invoice": true}')
    
    assert result["extracted_amount"] == 540.25
    assert result["is_invoice"] is True

def test_vision_strict_json_parsing_conversational_wrapper():
    # LLMs hallucinate markdown wrappers even when format="json"
    result = _parse_vision_json('```json\n{"extracted_amount": 200, "is_invoice": true}\n```')
    
    assert result["extracted_amount"] == 200.0
    assert result["is_invoice"] is True

def test_vision_strict_json_parsing_malformed():
    # Invalid JSON should fallback safely to default empty state
    result = _parse_vision_json('Here is your json: {extracted_amount: 100')
    
    assert result["extracted_amount"] is None
    assert result["is_invoice"] is False

def test_vision_strict_json_parsing_not_an_invoice():
    # It's an image but not an invoice
    result = _parse_vision_json('{"extracted_amount": null, "is_invoice": false}')
    
    assert result["extracted_amount"] is None
    assert result["is_invoice"] is False
