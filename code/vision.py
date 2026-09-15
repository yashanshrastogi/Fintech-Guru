"""
V2 Phase 2: Vision Provider Adapter Layer.

Provides an abstract VisionProvider interface with concrete implementations:
  - DisabledVisionProvider: safe fallback when no vision model is available
  - OllamaVisionProvider:   uses a local vision-capable Ollama model (llava, qwen-vl, etc.)

Business rules (hard):
  1. Vision is ONLY attempted when event.amount is None.
  2. A failed or unavailable vision provider never produces amount = 0.
     It always returns None (unknown), preserving the missing-amount state.
  3. Extracted amounts are validated before being applied:
     - amount must be > 0
     - currency must match expected event currency (or home currency)
     - confidence must be >= VISION_MIN_CONFIDENCE (default 0.7)
  4. Vision extracted amounts may not override business rules (deterministic engine
     decides how to handle the event; vision only fills in the blank amount).
  5. Provenance is tracked: every event amended by vision records the source.

Usage:
    from vision import get_vision_provider, VisionResult
    provider = get_vision_provider()
    if provider.is_available():
        result = provider.extract(image_path, currency_hint="IDR", home_currency="IDR")
        if result.is_valid and result.confidence >= 0.7:
            event.amount = result.amount
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava")
VISION_MIN_CONFIDENCE = float(os.getenv("VISION_MIN_CONFIDENCE", "0.7"))
USE_LOCAL_VISION = os.getenv("USE_LOCAL_VISION", "false").lower() == "true"
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class VisionResult:
    """
    Result of a vision extraction attempt.

    Fields:
        amount:      Extracted amount as Decimal, or None if not found/confident.
        currency:    Extracted 3-letter currency code, or None.
        date_found:  Extracted date from the receipt/image, or None.
        confidence:  Extraction confidence (0.0–1.0).
        raw_text:    Raw OCR/extracted text (for audit/provenance).
        method:      Which provider produced this result.
        is_valid:    True if the result passed all validation checks.
        rejection_reason: Why is_valid is False (if applicable).
    """
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    date_found: Optional[date] = None
    confidence: float = 0.0
    raw_text: str = ""
    method: str = "unknown"
    is_valid: bool = False
    rejection_reason: Optional[str] = None

    @classmethod
    def unavailable(cls, reason: str = "vision_model_unavailable") -> "VisionResult":
        return cls(method="disabled", is_valid=False, rejection_reason=reason)

    @classmethod
    def extraction_error(cls, reason: str, raw_text: str = "") -> "VisionResult":
        return cls(method="error", is_valid=False, rejection_reason=reason, raw_text=raw_text)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class VisionProvider(ABC):
    """Abstract vision provider. All implementations must satisfy the safety contract."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider can actually perform extractions."""
        ...

    @abstractmethod
    def extract(
        self,
        image_path: Path,
        currency_hint: Optional[str] = None,
        home_currency: Optional[str] = None,
    ) -> VisionResult:
        """
        Extract financial information from an image file.

        Args:
            image_path:    Absolute path to the image file.
            currency_hint: Expected currency (from event.currency).
            home_currency: User's home currency (for validation fallback).

        Returns:
            VisionResult with is_valid=True only if extraction passed all checks.
            Never returns amount=0 on failure — always None.
        """
        ...


# ---------------------------------------------------------------------------
# DisabledVisionProvider (safe fallback)
# ---------------------------------------------------------------------------

class DisabledVisionProvider(VisionProvider):
    """
    Safe no-op vision provider used when:
    - USE_LOCAL_VISION=false (default)
    - Configured vision model is not installed in Ollama
    - Vision model check failed at startup
    """

    def is_available(self) -> bool:
        return False

    def extract(self, image_path: Path, currency_hint=None, home_currency=None) -> VisionResult:
        return VisionResult.unavailable("vision_support_disabled")


# ---------------------------------------------------------------------------
# OllamaVisionProvider
# ---------------------------------------------------------------------------

class OllamaVisionProvider(VisionProvider):
    """
    Vision provider that uses a locally running Ollama vision model.

    Supported models: llava, llava-llama3, qwen2-vl, moondream, etc.
    The model must support image inputs via Ollama's /api/generate endpoint.

    Safety guarantees:
    - Model availability is checked on construction (not every call).
    - Image is base64-encoded and sent inline — no external network calls.
    - Extracted amount is validated against currency_hint before acceptance.
    - Low-confidence or unparseable responses are silently rejected.
    """

    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_VISION_MODEL):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._available: Optional[bool] = None  # Lazy check

    def is_available(self) -> bool:
        if self._available is None:
            self._available = self._check_model_exists()
        return self._available

    def _check_model_exists(self) -> bool:
        """Ping Ollama's /api/tags to see if the vision model is installed."""
        try:
            url = f"{self._base_url}/api/tags"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
            models = [m.get("name", "") for m in data.get("models", [])]
            available = any(self._model in m for m in models)
            if available:
                logger.info(f"Vision model '{self._model}' found in Ollama.")
            else:
                logger.warning(
                    f"Vision model '{self._model}' NOT found in Ollama. "
                    f"Available models: {models}. "
                    f"Run: ollama pull {self._model}"
                )
            return available
        except Exception as e:
            logger.warning(f"Could not reach Ollama to check vision model: {e}")
            return False

    def extract(
        self,
        image_path: Path,
        currency_hint: Optional[str] = None,
        home_currency: Optional[str] = None,
    ) -> VisionResult:
        if not self.is_available():
            return VisionResult.unavailable(f"vision_model_not_installed:{self._model}")

        if not image_path.exists():
            return VisionResult.extraction_error(f"image_not_found:{image_path}")

        # Encode image to base64
        try:
            import base64
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            return VisionResult.extraction_error(f"image_read_error:{e}")

        # Build prompt
        prompt = self._build_prompt(currency_hint, home_currency)

        # Call Ollama vision endpoint
        payload = json.dumps({
            "model": self._model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "options": {"temperature": 0.0},
        }).encode("utf-8")

        try:
            url = f"{self._base_url}/api/generate"
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
                raw = resp.read().decode("utf-8")
            response_data = json.loads(raw)
            raw_text = response_data.get("response", "")
        except Exception as e:
            return VisionResult.extraction_error(f"ollama_call_failed:{e}")

        # Parse response
        return self._parse_response(raw_text, currency_hint, home_currency)

    def _build_prompt(self, currency_hint: Optional[str], home_currency: Optional[str]) -> str:
        cur = currency_hint or home_currency or "unknown"
        return f"""You are a financial document parser. Look at this receipt or document image.
Extract the total monetary amount shown.

Expected currency: {cur}

Return ONLY a JSON object with exactly these fields:
{{
  "amount": <number or null>,
  "currency": "<3-letter code or null>",
  "date": "<YYYY-MM-DD or null>",
  "confidence": <0.0 to 1.0>,
  "notes": "<brief note>"
}}

Rules:
- If you cannot find a clear total amount, set amount to null and confidence to 0.
- Only extract the TOTAL amount, not subtotals or tax amounts.
- Do not invent amounts that are not visible in the image.
- Set confidence based on how clearly you can read the number (1.0 = perfectly clear).
"""

    def _parse_response(
        self,
        raw_text: str,
        currency_hint: Optional[str],
        home_currency: Optional[str],
    ) -> VisionResult:
        # Extract JSON from response
        text = raw_text.strip()
        try:
            # Handle possible markdown wrapping
            if "```" in text:
                parts = text.split("```")
                for part in parts:
                    part = part.strip().lstrip("json").strip()
                    if part.startswith("{"):
                        text = part
                        break

            data = json.loads(text)
        except Exception as e:
            return VisionResult.extraction_error(
                f"json_parse_failed:{e}", raw_text=raw_text[:500]
            )

        raw_amount = data.get("amount")
        raw_currency = data.get("currency")
        confidence = float(data.get("confidence", 0.0))
        raw_date = data.get("date")

        # Parse amount
        try:
            amount = Decimal(str(raw_amount)) if raw_amount is not None else None
        except Exception:
            amount = None

        # Parse date
        extracted_date = None
        if raw_date:
            try:
                from datetime import date as date_type
                extracted_date = date_type.fromisoformat(str(raw_date))
            except Exception:
                pass

        # Validate
        if amount is None:
            return VisionResult(
                method=f"ollama:{self._model}",
                raw_text=raw_text[:500],
                confidence=confidence,
                is_valid=False,
                rejection_reason="amount_not_found_in_image",
            )

        if amount <= Decimal("0"):
            return VisionResult(
                amount=None,
                method=f"ollama:{self._model}",
                raw_text=raw_text[:500],
                confidence=confidence,
                is_valid=False,
                rejection_reason=f"invalid_amount:{amount}",
            )

        # Currency validation
        accepted_currencies = {c for c in [currency_hint, home_currency] if c}
        if raw_currency and accepted_currencies and raw_currency.upper() not in accepted_currencies:
            return VisionResult(
                amount=None,
                currency=raw_currency,
                method=f"ollama:{self._model}",
                raw_text=raw_text[:500],
                confidence=confidence,
                is_valid=False,
                rejection_reason=f"currency_mismatch:got={raw_currency},expected={accepted_currencies}",
            )

        # Confidence threshold
        if confidence < VISION_MIN_CONFIDENCE:
            return VisionResult(
                amount=None,
                currency=raw_currency,
                method=f"ollama:{self._model}",
                raw_text=raw_text[:500],
                confidence=confidence,
                is_valid=False,
                rejection_reason=f"low_confidence:{confidence:.2f}<{VISION_MIN_CONFIDENCE}",
            )

        return VisionResult(
            amount=amount,
            currency=raw_currency or currency_hint or home_currency,
            date_found=extracted_date,
            confidence=confidence,
            raw_text=raw_text[:500],
            method=f"ollama:{self._model}",
            is_valid=True,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_provider_instance: Optional[VisionProvider] = None


def get_vision_provider(force_new: bool = False) -> VisionProvider:
    """
    Get the singleton VisionProvider.

    Logic:
    1. If USE_LOCAL_VISION=false → DisabledVisionProvider
    2. If USE_LOCAL_VISION=true  → OllamaVisionProvider (checks model availability)
    3. If model not available    → DisabledVisionProvider (with warning)

    Args:
        force_new: Force recreation of the singleton (useful for testing).
    """
    global _provider_instance

    if _provider_instance is not None and not force_new:
        return _provider_instance

    if not USE_LOCAL_VISION:
        logger.info("Vision support disabled (USE_LOCAL_VISION=false). "
                    "Events with blank amounts will remain unresolved.")
        _provider_instance = DisabledVisionProvider()
        return _provider_instance

    provider = OllamaVisionProvider(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_VISION_MODEL,
    )

    if provider.is_available():
        logger.info(f"Vision provider: OllamaVisionProvider (model={OLLAMA_VISION_MODEL})")
        _provider_instance = provider
    else:
        logger.warning(
            f"Requested vision model '{OLLAMA_VISION_MODEL}' is not available. "
            f"Falling back to DisabledVisionProvider. "
            f"To enable vision: ollama pull {OLLAMA_VISION_MODEL}"
        )
        _provider_instance = DisabledVisionProvider()

    return _provider_instance
