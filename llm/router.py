"""
LLM Router — Production Request Routing for FinTech Guru V2

Routing Contract:
  - "deterministic"  → pure deterministic pipeline, no LLM call
  - "evidence"       → one Qwen evidence extraction call + deterministic recalculation
  - "agentic"        → alias for "evidence" (backward compat, production-safe)
  - "multi_agent"    → reserved for isolated experiment only (not production default)

The PRODUCTION DEFAULT is "deterministic".
The LLM is invoked ONLY when explicit evidence extraction is needed.
The old multi-agent debate is NOT a production path.
"""

import logging
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

# Modes that trigger evidence-extraction (one Qwen call)
EVIDENCE_MODES = {"evidence", "agentic", "agent"}

# Modes that are purely deterministic (no LLM call)
DETERMINISTIC_MODES = {"deterministic", "strict", "fast"}

# Legacy multi-agent debate — only for isolated experiments
MULTI_AGENT_MODES = {"multi_agent", "debate"}


def route_request(
    mode: str,
    deterministic_handler: Callable,
    multi_agent_handler: Callable,
    **kwargs,
) -> Dict[str, Any]:
    """
    Routes an incoming affordability request to the correct pipeline.

    Production normal path:
      1. deterministic  → deterministic_handler (no LLM)
      2. evidence       → evidence_handler → deterministic_handler (1 LLM call)
      3. agentic        → alias for "evidence"

    Legacy path (not production default):
      4. multi_agent    → multi_agent_handler (multi-call LLM debate)

    Args:
        mode: Routing mode string from the request.
        deterministic_handler: The pure-deterministic pipeline callable.
        multi_agent_handler: The evidence extraction + deterministic callable.
            NOTE: despite the name kept for backward compat, this is now the
            single-call evidence-extraction path.  True multi-agent debate
            is not exposed in V2 production.
        **kwargs: Passed through to the selected handler.

    Returns:
        Result dict from the selected handler.

    Raises:
        ValueError: If the mode is completely unrecognized.
    """
    mode_lower = mode.strip().lower() if mode else "deterministic"

    if mode_lower in DETERMINISTIC_MODES:
        logger.info(f"[Router] DETERMINISTIC path selected (mode={mode_lower})")
        return deterministic_handler(**kwargs)

    elif mode_lower in EVIDENCE_MODES:
        # "agentic" in the old code meant multi-agent debate.
        # In V2 production, "agentic" means: run one Qwen evidence extraction
        # call, then the deterministic engine makes the final decision.
        logger.info(
            f"[Router] EVIDENCE EXTRACTION path selected (mode={mode_lower}) — "
            "1 Qwen call + deterministic recalculation"
        )
        return multi_agent_handler(**kwargs)

    elif mode_lower in MULTI_AGENT_MODES:
        # This path is only for isolated benchmarking experiments.
        # It must NEVER be used by the production UI default.
        logger.warning(
            f"[Router] MULTI-AGENT DEBATE path selected (mode={mode_lower}) — "
            "NOT the production default. Use for experiments only."
        )
        return multi_agent_handler(**kwargs)

    else:
        logger.error(f"[Router] Unrecognized routing mode: '{mode}'")
        raise ValueError(
            f"Unrecognized routing mode: '{mode}'. "
            "Valid modes: 'deterministic', 'evidence', 'agentic', 'multi_agent'."
        )
