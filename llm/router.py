import logging
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

def route_request(mode: str, deterministic_handler: Callable, multi_agent_handler: Callable, **kwargs) -> Dict[str, Any]:
    """
    Routes the incoming request strictly based on the provided mode.
    
    Args:
        mode: The requested mode.
        deterministic_handler: The function to call for deterministic routing.
        multi_agent_handler: The function to call for multi-agent routing.
        **kwargs: Arguments to pass to the handlers.
        
    Returns:
        The response dictionary from the selected handler.
    """
    mode_lower = mode.strip().lower()
    
    # "agentic" is an explicit alias for "multi_agent" to prevent the
    # routing failure that occurred in V1 (where 'agentic' fell through to default/deterministic)
    if mode_lower in ("multi_agent", "agentic", "agent"):
        logger.info(f"Routing request to MULTI-AGENT pipeline (mode: {mode_lower})")
        return multi_agent_handler(**kwargs)
        
    elif mode_lower in ("deterministic", "strict", "fast"):
        logger.info(f"Routing request to DETERMINISTIC pipeline (mode: {mode_lower})")
        return deterministic_handler(**kwargs)
        
    else:
        # Ambiguous mode: reject strictly rather than defaulting silently
        logger.error(f"Ambiguous or unrecognized mode requested: {mode}")
        raise ValueError(
            f"Unrecognized routing mode: '{mode}'. "
            "Must be one of: 'deterministic', 'multi_agent', 'agentic'."
        )
