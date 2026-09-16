import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class LLMClient:
    """
    A unified interface for querying the local LLM.
    Enforces strict JSON schema extraction without conversational wrappers.
    """
    
    def __init__(self, endpoint: str = "http://localhost:11434"):
        self.endpoint = endpoint
        
    def extract_evidence(self, text: str) -> Dict[str, Any]:
        """
        Extracts financial evidence from user messages.
        In a real deployment, this would hit the Ollama API with format="json".
        For the pipeline test, we mock the behavior.
        """
        # A real implementation would invoke Ollama and parse JSON.
        # This wrapper forces the caller to expect dicts and handles parse errors.
        prompt = (
            "Extract the following into strictly formatted JSON:\n"
            "- extracted_salary (number or null)\n"
            "- extracted_amount (number or null)\n"
            "- cancellation_request (boolean)\n\n"
            f"Message: {text}"
        )
        
        response_json_str = self._call_llm(prompt)
        
        return self._parse_json(response_json_str)

    def _call_llm(self, prompt: str) -> str:
        """Mock method for LLM network call."""
        return '{"extracted_salary": null, "extracted_amount": null, "cancellation_request": false}'
        
    def _parse_json(self, raw_output: str) -> Dict[str, Any]:
        """Strictly parses JSON and enforces the evidence schema."""
        default_evidence = {
            "extracted_salary": None,
            "extracted_amount": None,
            "cancellation_request": False
        }
        
        try:
            # Strip conversational wrappers (e.g. ```json ... ```)
            clean_str = raw_output.strip()
            if clean_str.startswith("```json"):
                clean_str = clean_str[7:]
            if clean_str.endswith("```"):
                clean_str = clean_str[:-3]
            clean_str = clean_str.strip()
            
            data = json.loads(clean_str)
            
            # Enforce schema types
            return {
                "extracted_salary": float(data["extracted_salary"]) if data.get("extracted_salary") is not None else None,
                "extracted_amount": float(data["extracted_amount"]) if data.get("extracted_amount") is not None else None,
                "cancellation_request": bool(data.get("cancellation_request", False))
            }
        except Exception as e:
            logger.error(f"Failed to parse LLM JSON output: {e}")
            return default_evidence
