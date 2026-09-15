"""
V2 Tests — Vision Provider (Phase 2).

Tests all vision provider scenarios without requiring a real Ollama instance.
Uses monkeypatching to simulate vision model responses.

Run with: pytest v2/tests/test_vision.py -v
"""
import sys
import json
import base64
from pathlib import Path
from decimal import Decimal
from datetime import date
from unittest.mock import patch, MagicMock
import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "code"))

import os
os.environ["USE_LOCAL_VISION"] = "false"  # default: disable vision

from vision import (
    VisionResult, DisabledVisionProvider, OllamaVisionProvider, get_vision_provider
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_tmp_image(tmp_path: Path, content: bytes = b"fake_image_data") -> Path:
    img = tmp_path / "test_receipt.png"
    img.write_bytes(content)
    return img


def make_ollama_response(amount, currency="IDR", confidence=0.9, date_str=None):
    """Build the JSON response that Ollama vision would return."""
    return json.dumps({
        "amount": amount,
        "currency": currency,
        "date": date_str,
        "confidence": confidence,
        "notes": "test",
    })


def make_ollama_http_response(body: str):
    """Wrap body in Ollama's /api/generate response envelope."""
    return json.dumps({"response": body, "done": True}).encode("utf-8")


# ---------------------------------------------------------------------------
# DisabledVisionProvider tests
# ---------------------------------------------------------------------------

def test_disabled_provider_is_not_available():
    provider = DisabledVisionProvider()
    assert not provider.is_available()


def test_disabled_provider_extract_returns_unavailable(tmp_path):
    provider = DisabledVisionProvider()
    img = make_tmp_image(tmp_path)
    result = provider.extract(img, currency_hint="IDR")
    assert not result.is_valid
    assert result.amount is None
    assert "disabled" in result.rejection_reason


def test_get_vision_provider_returns_disabled_when_env_false():
    with patch.dict("os.environ", {"USE_LOCAL_VISION": "false"}):
        provider = get_vision_provider(force_new=True)
    assert isinstance(provider, DisabledVisionProvider)


# ---------------------------------------------------------------------------
# OllamaVisionProvider — model availability
# ---------------------------------------------------------------------------

def test_ollama_vision_provider_unavailable_when_model_missing():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "models": [{"name": "qwen3:8b"}, {"name": "nomic-embed-text"}]
        }).encode("utf-8")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        provider = OllamaVisionProvider(model="llava")
        available = provider.is_available()
    assert not available


def test_ollama_vision_provider_available_when_model_present():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "models": [{"name": "llava:latest"}, {"name": "qwen3:8b"}]
        }).encode("utf-8")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        provider = OllamaVisionProvider(model="llava")
        available = provider.is_available()
    assert available


# ---------------------------------------------------------------------------
# OllamaVisionProvider — extraction scenarios
# ---------------------------------------------------------------------------

def _make_provider_with_model(model="llava"):
    """Build a provider that thinks the model is available."""
    provider = OllamaVisionProvider(model=model)
    provider._available = True  # skip model check
    return provider


def _mock_ollama_call(mock_urlopen, response_body: str):
    """Configure mock to return a given Ollama response body."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = make_ollama_http_response(response_body)
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_resp


def test_valid_receipt_amount_extracted(tmp_path):
    """Happy path: model returns clean JSON with valid amount."""
    provider = _make_provider_with_model()
    img = make_tmp_image(tmp_path)

    with patch("urllib.request.urlopen") as mock_urlopen:
        _mock_ollama_call(mock_urlopen, make_ollama_response(500000, "IDR", 0.95))
        result = provider.extract(img, currency_hint="IDR", home_currency="IDR")

    assert result.is_valid
    assert result.amount == Decimal("500000")
    assert result.confidence == 0.95
    assert "llava" in result.method


def test_invalid_amount_zero_is_rejected(tmp_path):
    """Amount = 0 must be rejected (not treated as None or valid)."""
    provider = _make_provider_with_model()
    img = make_tmp_image(tmp_path)

    with patch("urllib.request.urlopen") as mock_urlopen:
        _mock_ollama_call(mock_urlopen, make_ollama_response(0, "IDR", 0.9))
        result = provider.extract(img, currency_hint="IDR")

    assert not result.is_valid
    assert result.amount is None
    assert "invalid_amount" in result.rejection_reason


def test_null_amount_is_rejected(tmp_path):
    """Model returning null amount must produce is_valid=False, amount=None."""
    provider = _make_provider_with_model()
    img = make_tmp_image(tmp_path)

    with patch("urllib.request.urlopen") as mock_urlopen:
        _mock_ollama_call(mock_urlopen, make_ollama_response(None, "IDR", 0.8))
        result = provider.extract(img, currency_hint="IDR")

    assert not result.is_valid
    assert result.amount is None
    assert "amount_not_found" in result.rejection_reason


def test_wrong_currency_is_rejected(tmp_path):
    """If extracted currency doesn't match expected, reject the result."""
    provider = _make_provider_with_model()
    img = make_tmp_image(tmp_path)

    with patch("urllib.request.urlopen") as mock_urlopen:
        # Returns USD amount but event expects IDR
        _mock_ollama_call(mock_urlopen, make_ollama_response(100, "USD", 0.95))
        result = provider.extract(img, currency_hint="IDR", home_currency="IDR")

    assert not result.is_valid
    assert result.amount is None
    assert "currency_mismatch" in result.rejection_reason


def test_low_confidence_is_rejected(tmp_path):
    """Confidence < 0.7 must be rejected even if amount is valid."""
    provider = _make_provider_with_model()
    img = make_tmp_image(tmp_path)

    with patch("urllib.request.urlopen") as mock_urlopen:
        _mock_ollama_call(mock_urlopen, make_ollama_response(500000, "IDR", 0.4))
        result = provider.extract(img, currency_hint="IDR")

    assert not result.is_valid
    assert result.amount is None
    assert "low_confidence" in result.rejection_reason


def test_ambiguous_json_response_handled(tmp_path):
    """Malformed model response must not crash — return extraction_error."""
    provider = _make_provider_with_model()
    img = make_tmp_image(tmp_path)

    with patch("urllib.request.urlopen") as mock_urlopen:
        _mock_ollama_call(mock_urlopen, "Sorry, I cannot determine the amount from this image.")
        result = provider.extract(img, currency_hint="IDR")

    assert not result.is_valid
    assert result.amount is None
    assert result.rejection_reason is not None


def test_image_not_found_returns_error():
    """If the image file doesn't exist, return extraction_error immediately."""
    provider = _make_provider_with_model()
    result = provider.extract(Path("/nonexistent/path/image.png"), currency_hint="IDR")
    assert not result.is_valid
    assert result.amount is None
    assert "image_not_found" in result.rejection_reason


def test_blank_amount_no_image_stays_none():
    """When there is no image and amount is blank, result must stay None (not zero)."""
    result = VisionResult.unavailable("no_image_available")
    assert result.amount is None
    assert not result.is_valid


def test_blank_amount_with_successful_extraction_is_valid(tmp_path):
    """Successful extraction must return is_valid=True with positive Decimal amount."""
    provider = _make_provider_with_model()
    img = make_tmp_image(tmp_path)

    with patch("urllib.request.urlopen") as mock_urlopen:
        _mock_ollama_call(mock_urlopen, make_ollama_response(1_500_000, "IDR", 0.9))
        result = provider.extract(img, currency_hint="IDR", home_currency="IDR")

    assert result.is_valid
    assert isinstance(result.amount, Decimal)
    assert result.amount > Decimal("0")
