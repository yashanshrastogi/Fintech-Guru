from llm.fallback import mock_multi_agent_pipeline

def mock_deterministic_handler(**kwargs):
    return {"status": "success", "amount": 500}

def test_mock_multi_agent_pipeline():
    result = mock_multi_agent_pipeline(mock_deterministic_handler, test_arg="value")
    
    assert result["status"] == "success"
    assert result["amount"] == 500
    assert "_meta" in result
    assert result["_meta"]["routed_as"] == "multi_agent"
    assert result["_meta"]["executed_as"] == "deterministic_fallback"
