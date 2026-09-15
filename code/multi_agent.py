"""
Multi-Agent reasoning layer running locally via Ollama.
Includes the 3 agents (Financial Analyst, Risk Auditor, Preference Reviewer)
and the Disagreement/Cross-Review logic.
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
import concurrent.futures

from ollama_client import ollama_client
from models import Request, FinancialProfile, CandidatePlan, FinancialEvent
from config import AGENT_CROSS_REVIEW, MAX_AGENT_ROUNDS, CODE_DIR

logger = logging.getLogger(__name__)

# Load prompts
def _load_prompt(name: str) -> str:
    path = CODE_DIR / "prompts" / f"{name}.txt"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load prompt {name}: {e}")
        return ""

PROMPTS = {
    "financial_analyst": _load_prompt("financial_analyst"),
    "risk_auditor": _load_prompt("risk_auditor"),
    "preference_reviewer": _load_prompt("preference_reviewer"),
}

def _build_context(
    request: Request,
    profile: FinancialProfile,
    events: List[FinancialEvent],
    candidates: List[CandidatePlan],
    messages: List[Any],
    extra_context: Optional[Dict[str, Any]] = None
) -> str:
    """Build a compact JSON context for the LLM."""
    
    compact_candidates = []
    for c in candidates:
        compact_candidates.append({
            "candidate_id": c.candidate_id,
            "method": c.payment_method,
            "safety_status": c.safety_status,
            "total_paid": float(c.total_amount_paid),
            "deadline_met": c.deadline_met,
            "requires_spending_changes": c.requires_spending_changes,
            "min_forecast_balance": float(c.minimum_forecast_balance)
        })

    ctx = {
        "request": {
            "id": request.request_id,
            "type": request.request_type,
            "amount": float(request.requested_amount),
            "date": request.request_date.isoformat(),
            "deadline": request.desired_completion_date.isoformat()
        },
        "profile": {
            "currency": profile.home_currency,
            "min_balance": float(profile.minimum_balance_to_keep),
            "allowed_methods": profile.payment_methods_user_will_consider
        },
        "candidate_plans": compact_candidates,
    }
    
    if extra_context:
        ctx.update(extra_context)
        
    messages_texts = [f"<UNTRUSTED_EVIDENCE>{m.message_text}</UNTRUSTED_EVIDENCE>" for m in messages[:10]]
    if messages_texts:
        ctx["messages"] = messages_texts
        
    return json.dumps(ctx, indent=2)


def invoke_agent(agent_name: str, context_json: str) -> Optional[Dict[str, Any]]:
    """Invoke a single agent via Ollama."""
    prompt_template = PROMPTS.get(agent_name)
    if not prompt_template:
        return None
        
    prompt = prompt_template.replace("{context_json}", context_json)
    
    # We ignore latency/tokens here for brevity, telemetry handled in ollama_client or wrapper
    result, lat, inc, outc = ollama_client.structured_completion(prompt, agent=agent_name)
    
    if result:
        # Save telemetry trace
        _log_agent_trace(
            request_id=json.loads(context_json).get("request", {}).get("id", "unknown"),
            agent=agent_name,
            candidate=result.get("selected_candidate_id"),
            confidence=result.get("confidence", 0.0),
            latency=lat,
            success=True
        )
    return result

def _log_agent_trace(request_id: str, agent: str, candidate: str, confidence: float, latency: float, success: bool):
    """Write minimal trace record to evaluation/agent_trace.jsonl"""
    trace_path = CODE_DIR.parent / "evaluation" / "agent_trace.jsonl"
    try:
        trace_path.parent.mkdir(exist_ok=True)
        record = {
            "timestamp": os.environ.get("CURRENT_TIME", ""),
            "request_id": request_id,
            "agent": agent,
            "selected_candidate": candidate,
            "confidence": confidence,
            "latency": latency,
            "success": success
        }
        with open(trace_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass


def run_agentic_review(
    request: Request,
    profile: FinancialProfile,
    events: List[FinancialEvent],
    candidates: List[CandidatePlan],
    messages: List[Any],
) -> Dict[str, Any]:
    """
    Run the 3 agents in parallel and handle cross-review if they disagree.
    Returns the opinions dict.
    """
    context_json = _build_context(request, profile, events, candidates, messages)
    
    opinions = {}
    
    # Phase 1: Parallel invocation of the 3 base agents
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future_fa = executor.submit(invoke_agent, "financial_analyst", context_json)
        future_ra = executor.submit(invoke_agent, "risk_auditor", context_json)
        future_pr = executor.submit(invoke_agent, "preference_reviewer", context_json)
        
        opinions["financial_analyst"] = future_fa.result()
        opinions["risk_auditor"] = future_ra.result()
        opinions["preference_reviewer"] = future_pr.result()
        
    # Check for disagreement
    valid_opinions = [v for v in opinions.values() if v and "selected_candidate_id" in v]
    if not valid_opinions:
        return opinions
        
    selected = set(v["selected_candidate_id"] for v in valid_opinions)
    
    if len(selected) > 1 and AGENT_CROSS_REVIEW:
        # Disagreement! Run cross-review round
        logger.info(f"Agents disagree on {request.request_id} ({selected}). Running cross-review.")
        
        cross_context = _build_context(
            request, profile, events, candidates, messages, 
            extra_context={"other_agent_opinions": opinions}
        )
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future_fa = executor.submit(invoke_agent, "financial_analyst", cross_context)
            future_ra = executor.submit(invoke_agent, "risk_auditor", cross_context)
            future_pr = executor.submit(invoke_agent, "preference_reviewer", cross_context)
            
            op_fa = future_fa.result()
            op_ra = future_ra.result()
            op_pr = future_pr.result()
            
            if op_fa: opinions["financial_analyst"] = op_fa
            if op_ra: opinions["risk_auditor"] = op_ra
            if op_pr: opinions["preference_reviewer"] = op_pr
            
    return opinions
