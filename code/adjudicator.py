"""
Adjudicator for the Multi-Agent layer.
Takes opinions from the 3 agents, weights them, and makes the final candidate selection.
Enforces hard safety constraints.
"""
import json
import logging
from typing import List, Dict, Any, Optional

from models import CandidatePlan, Request, FinancialProfile
from ollama_client import ollama_client
from multi_agent import _build_context, _load_prompt, _log_agent_trace
from config import CODE_DIR

logger = logging.getLogger(__name__)

class Adjudicator:
    def __init__(self):
        self.prompt_template = _load_prompt("adjudicator")
        
    def adjudicate(
        self,
        request: Request,
        profile: FinancialProfile,
        candidates: List[CandidatePlan],
        agent_opinions: Dict[str, Any]
    ) -> Optional[CandidatePlan]:
        """
        Run the adjudicator agent.
        """
        # 1. Enforce safety veto BEFORE Adjudication
        # The adjudicator only sees safe candidates, or all candidates if none are safe.
        safe_candidates = [c for c in candidates if c.safety_status == "safe"]
        if not safe_candidates:
            # If no safe candidates exist, the deterministic fallback has already handled it
            # by offering `not_recommended` or similar. No agent needed.
            logger.warning(f"Adjudicator invoked but NO safe candidates exist for {request.request_id}.")
            safe_candidates = candidates
            
        context_json = _build_context(
            request, profile, [], safe_candidates, [],
            extra_context={"agent_opinions": agent_opinions}
        )
        
        prompt = self.prompt_template.replace("{context_json}", context_json)
        
        result, lat, inc, outc = ollama_client.structured_completion(prompt, agent="adjudicator")
        
        if not result or "selected_candidate_id" not in result:
            logger.warning("Adjudicator failed to return valid selection.")
            return None
            
        selected_id = result["selected_candidate_id"]
        
        # Log trace
        _log_agent_trace(
            request_id=request.request_id,
            agent="adjudicator",
            candidate=selected_id,
            confidence=result.get("confidence", 0.0),
            latency=lat,
            success=True
        )
        
        # 2. VETO logic: The adjudicator selected a candidate. 
        # Check if it actually exists in the deterministic list.
        matched = next((c for c in candidates if c.candidate_id == selected_id), None)
        
        if not matched:
            logger.warning(f"Adjudicator selected INVALID candidate_id: {selected_id}")
            return None
            
        if matched.safety_status != "safe" and matched.payment_method != "not_recommended":
            logger.error(f"Adjudicator selected UNSAFE candidate: {selected_id}. VETO applied.")
            return None
            
        return matched
