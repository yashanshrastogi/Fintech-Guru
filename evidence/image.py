import logging
from typing import List, Dict, Any
from core.models import MessageEvidence
from llm.client import LLMClient

logger = logging.getLogger(__name__)

def process_images(messages: List[MessageEvidence], client: LLMClient) -> List[Dict[str, Any]]:
    """
    Process image messages to extract invoice amounts.
    Enforces a strict JSON vision guard.
    """
    results = []
    for msg in messages:
        if not getattr(msg, "has_image", False):
            continue
            
        # In a real environment, this passes the image path to Ollama's Vision API
        # We enforce the client strictly parses the JSON to avoid conversational wrappers
        # and missing data crashes.
        prompt = (
            "You are a strict financial vision guard. "
            "Extract the total invoice amount from this image into strictly formatted JSON:\n"
            "- extracted_amount (number or null)\n"
            "- is_invoice (boolean)\n\n"
        )
        
        # We reuse the client's _call_llm string mock here, but in production
        # it would call `_call_llm_vision(prompt, msg.image_path)`.
        response_json_str = client._call_llm(prompt)
        
        # Override _parse_json rules for the specific vision schema
        extraction = _parse_vision_json(response_json_str)
        
        if extraction.get("is_invoice") and extraction.get("extracted_amount") is not None:
            extraction["message_id"] = msg.message_id
            results.append(extraction)
            
    return results

def _parse_vision_json(raw_output: str) -> Dict[str, Any]:
    """Strictly parses Vision JSON and enforces the schema."""
    import json
    default_evidence = {
        "extracted_amount": None,
        "is_invoice": False
    }
    
    try:
        clean_str = raw_output.strip()
        if clean_str.startswith("```json"):
            clean_str = clean_str[7:]
        if clean_str.endswith("```"):
            clean_str = clean_str[:-3]
        clean_str = clean_str.strip()
        
        data = json.loads(clean_str)
        
        return {
            "extracted_amount": float(data["extracted_amount"]) if data.get("extracted_amount") is not None else None,
            "is_invoice": bool(data.get("is_invoice", False))
        }
    except Exception as e:
        logger.error(f"Failed to parse LLM Vision JSON output: {e}")
        return default_evidence
