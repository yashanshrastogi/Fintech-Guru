"""
LLM Client — Production Ollama Interface for FinTech Guru V2

Responsibilities:
  - Call qwen3:8b via Ollama /api/generate with format=json
  - Strip <think>…</think> blocks that qwen3 emits in reasoning mode
  - Enforce strict evidence schema on all outputs
  - Graceful fallback to empty evidence on connection failure
  - NEVER be the source of financial truth — only extract structured facts
"""

import json
import logging
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL_NAME = "qwen3:8b"
DEFAULT_ENDPOINT = "http://localhost:11434"
REQUEST_TIMEOUT_SEC = 60  # qwen3:8b first-token can be slow on CPU

# System prompt — instructs the model to return pure JSON, no commentary
EVIDENCE_SYSTEM_PROMPT = (
    "You are a financial data extraction assistant. "
    "You MUST respond with ONLY a valid JSON object and NOTHING else. "
    "No prose, no markdown, no code fences, no <think> blocks in your final answer. "
    "If a field is not mentioned, use null or false as appropriate."
)

EVIDENCE_USER_TEMPLATE = (
    "Extract the following fields from the user message below into a JSON object:\n"
    "  extracted_salary: number (new annual/monthly salary if mentioned, else null)\n"
    "  salary_effective_date: ISO date string (e.g. '2026-10-01') if mentioned, else null\n"
    "  extracted_amount: number (purchase/transaction amount if mentioned, else null)\n"
    "  cancellation_request: boolean (true if the user mentions cancelling a subscription/service)\n"
    "  cancelled_category: string (the specific category being cancelled, e.g. 'gym', else null)\n"
    "  currency: string (3-letter ISO currency code if explicitly stated, else null)\n\n"
    "User message: \"{message}\"\n\n"
    "Respond with ONLY the JSON object."
)

DEFAULT_EVIDENCE = {
    "extracted_salary": None,
    "salary_effective_date": None,
    "extracted_amount": None,
    "cancellation_request": False,
    "cancelled_category": None,
    "currency": None,
}


class LLMClient:
    """
    Production interface to qwen3:8b via Ollama.

    Architectural contract:
      - Returns structured Dict[str, Any] evidence facts only.
      - Does NOT make any financial decisions.
      - Does NOT produce amounts or statuses.
      - The deterministic engine uses the extracted facts.
    """

    def __init__(self, endpoint: str = DEFAULT_ENDPOINT, model: str = MODEL_NAME):
        self.endpoint = endpoint.rstrip("/")
        self.model = model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_evidence(self, text: str) -> Dict[str, Any]:
        """
        Extracts structured financial evidence from a natural language message.

        Returns a dict conforming to DEFAULT_EVIDENCE schema.
        On any failure, returns DEFAULT_EVIDENCE (graceful degradation).
        """
        prompt = EVIDENCE_USER_TEMPLATE.format(message=text.replace('"', "'"))
        raw = self._call_llm(system=EVIDENCE_SYSTEM_PROMPT, user=prompt)
        return self._parse_evidence_json(raw)

    # ------------------------------------------------------------------
    # Private implementation
    # ------------------------------------------------------------------

    def _call_llm(self, system: str, user: str) -> str:
        """
        Calls Ollama /api/generate.

        Uses `stream: false` so we get a single complete response.
        Uses `format: json` to nudge the model toward valid JSON output.
        Prepends the system prompt into the prompt field (Ollama /api/generate
        does not have a separate system field in all versions — we inline it).
        """
        import requests

        full_prompt = f"[SYSTEM]\n{system}\n\n[USER]\n{user}"

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 512,
            },
        }

        try:
            resp = requests.post(
                f"{self.endpoint}/api/generate",
                json=payload,
                timeout=REQUEST_TIMEOUT_SEC,
            )
            resp.raise_for_status()
            data = resp.json()
            raw_response = data.get("response", "{}")
            logger.info(
                f"[LLMClient] qwen3:8b responded — "
                f"eval_count={data.get('eval_count', '?')} tokens"
            )
            return raw_response
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"[LLMClient] Ollama not reachable: {e}")
            return "{}"
        except requests.exceptions.HTTPError as e:
            logger.warning(f"[LLMClient] Ollama HTTP error: {e}")
            return "{}"
        except requests.exceptions.Timeout:
            logger.warning(f"[LLMClient] Ollama request timed out after {REQUEST_TIMEOUT_SEC}s")
            return "{}"
        except Exception as e:
            logger.warning(f"[LLMClient] Unexpected error calling Ollama: {e}")
            return "{}"

    def _strip_think_blocks(self, raw: str) -> str:
        """
        Qwen3 emits <think>…</think> reasoning blocks before its actual answer.
        Strip them so that JSON parsing is not confused.
        """
        # Remove <think>...</think> blocks (may span multiple lines)
        cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
        return cleaned.strip()

    def _parse_evidence_json(self, raw: str) -> Dict[str, Any]:
        """
        Parses the LLM response into the evidence schema.
        Falls back to DEFAULT_EVIDENCE on any parse/schema error.
        """
        result = dict(DEFAULT_EVIDENCE)  # start with safe defaults

        try:
            # 1. Strip reasoning blocks
            clean = self._strip_think_blocks(raw)

            # 2. Strip markdown code fences if present
            if clean.startswith("```"):
                clean = re.sub(r"^```[a-z]*\n?", "", clean)
                clean = re.sub(r"\n?```$", "", clean)
            clean = clean.strip()

            if not clean or clean == "{}":
                return result

            # 3. Parse JSON
            data = json.loads(clean)

            # 4. Enforce schema — coerce types carefully
            if data.get("extracted_salary") is not None:
                result["extracted_salary"] = float(data["extracted_salary"])

            if data.get("salary_effective_date") is not None:
                result["salary_effective_date"] = str(data["salary_effective_date"])

            if data.get("extracted_amount") is not None:
                result["extracted_amount"] = float(data["extracted_amount"])

            result["cancellation_request"] = bool(data.get("cancellation_request", False))

            if data.get("cancelled_category") is not None:
                result["cancelled_category"] = str(data["cancelled_category"]).lower()

            if data.get("currency") is not None:
                result["currency"] = str(data["currency"]).upper()[:3]

            logger.info(f"[LLMClient] Extracted evidence: {result}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"[LLMClient] JSON parse error: {e} | raw={raw[:200]!r}")
            return result
        except Exception as e:
            logger.error(f"[LLMClient] Evidence schema error: {e}")
            return result

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Quick availability check — does NOT load a model."""
        import requests
        try:
            resp = requests.get(f"{self.endpoint}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def model_is_available(self) -> bool:
        """Check that the specific model is installed."""
        import requests
        try:
            resp = requests.get(f"{self.endpoint}/api/tags", timeout=5)
            if resp.status_code != 200:
                return False
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            return any(self.model in m for m in models)
        except Exception:
            return False
