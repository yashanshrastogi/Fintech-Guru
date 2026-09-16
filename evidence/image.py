import logging
import re
from typing import List, Dict, Any
from core.models import EvidenceItem
from llm.client import LLMClient

logger = logging.getLogger(__name__)


def process_evidence_items(items: List[EvidenceItem], client: LLMClient) -> List[Dict[str, Any]]:
    """
    Process evidence items that contain image/document content.
    Extracts structured financial facts using vision-capable LLM calls.
    """
    results = []
    for item in items:
        if item.item_type not in ("image", "document"):
            continue

        system = (
            "You are a strict financial vision guard. "
            "Extract structured data from invoice/receipt images. "
            "Respond ONLY with valid JSON, no prose, no code fences."
        )
        user = (
            "Extract the total invoice amount from this evidence:\n"
            f"Content type: {item.item_type}\n"
            f"Content: {item.raw_content[:500]}\n\n"
            "Return: {\"extracted_amount\": number_or_null, \"is_invoice\": boolean}"
        )

        response_json_str = client._call_llm(system=system, user=user)
        extraction = _parse_vision_json(response_json_str)

        if extraction.get("is_invoice") and extraction.get("extracted_amount") is not None:
            extraction["evidence_id"] = item.evidence_id
            results.append(extraction)

    return results

# Keep backward-compatible alias
process_images = process_evidence_items


def _parse_vision_json(raw_output: str) -> Dict[str, Any]:
    """Strictly parses Vision JSON and enforces the schema."""
    import json
    default_evidence = {
        "extracted_amount": None,
        "is_invoice": False
    }

    try:
        clean_str = raw_output.strip()

        # Strip <think>...</think> blocks from qwen3
        clean_str = re.sub(r"<think>.*?</think>", "", clean_str, flags=re.DOTALL).strip()

        # Strip markdown code fences
        if clean_str.startswith("```"):
            clean_str = re.sub(r"^```[a-z]*\n?", "", clean_str)
            clean_str = re.sub(r"\n?```$", "", clean_str)
        clean_str = clean_str.strip()

        data = json.loads(clean_str)

        return {
            "extracted_amount": float(data["extracted_amount"]) if data.get("extracted_amount") is not None else None,
            "is_invoice": bool(data.get("is_invoice", False))
        }
    except Exception as e:
        logger.error(f"Failed to parse LLM Vision JSON output: {e}")
        return default_evidence

