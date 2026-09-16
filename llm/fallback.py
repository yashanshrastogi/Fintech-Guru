import logging
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

def mock_multi_agent_pipeline(deterministic_handler: Callable, **kwargs) -> Dict[str, Any]:
    """
    Mocks the expensive 3-agent debate that failed in V1.
    Logs a warning and immediately falls back to the deterministic pipeline.
    This guarantees mathematical safety and fast execution.
    """
    logger.warning("MULTI-AGENT DEBATE DISABLED: Falling back to deterministic pipeline for safety and performance.")
    
    # We execute the deterministic handler but wrap the response to indicate it was a fallback
    response = deterministic_handler(**kwargs)
    
    # Inject metadata to prove the fallback occurred
    response["_meta"] = {
        "routed_as": "multi_agent",
        "executed_as": "deterministic_fallback",
        "reason": "Agentic debate is disabled in V2 to enforce hard safety boundaries."
    }
    
    return response
