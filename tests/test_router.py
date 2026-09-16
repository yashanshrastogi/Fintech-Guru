import pytest
from llm.router import route_request

def mock_deterministic_handler(**kwargs):
    return {"status": "deterministic_success"}

def mock_multi_agent_handler(**kwargs):
    return {"status": "multi_agent_success"}

def test_router_deterministic_mode():
    res = route_request("deterministic", mock_deterministic_handler, mock_multi_agent_handler)
    assert res["status"] == "deterministic_success"

def test_router_strict_alias():
    res = route_request("strict", mock_deterministic_handler, mock_multi_agent_handler)
    assert res["status"] == "deterministic_success"

def test_router_multi_agent_mode():
    res = route_request("multi_agent", mock_deterministic_handler, mock_multi_agent_handler)
    assert res["status"] == "multi_agent_success"

def test_router_agentic_alias_fixes_v1_bug():
    # This explicitly proves we fixed the V1 bug where "agentic" was missed
    res = route_request("agentic", mock_deterministic_handler, mock_multi_agent_handler)
    assert res["status"] == "multi_agent_success"

def test_router_rejects_ambiguous_modes():
    with pytest.raises(ValueError, match="Unrecognized routing mode"):
        route_request("auto", mock_deterministic_handler, mock_multi_agent_handler)
        
    with pytest.raises(ValueError, match="Unrecognized routing mode"):
        route_request("heuristic", mock_deterministic_handler, mock_multi_agent_handler)
