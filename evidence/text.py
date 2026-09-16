from typing import List, Dict, Any
from core.models import MessageEvidence
from llm.client import LLMClient

def process_messages(messages: List[MessageEvidence], client: LLMClient) -> List[Dict[str, Any]]:
    """
    Process all user text messages to extract financial amendments.
    Uses the strict LLM client to ensure no hallucinated non-JSON data is returned.
    """
    results = []
    for msg in messages:
        # Ignore image messages in text processing
        if getattr(msg, "has_image", False):
            continue
            
        extraction = client.extract_evidence(msg.message_text)
        
        # Only retain records that actually extracted something meaningful
        if extraction.get("extracted_salary") or extraction.get("extracted_amount") or extraction.get("cancellation_request"):
            extraction["message_id"] = msg.message_id
            results.append(extraction)
            
    return results
