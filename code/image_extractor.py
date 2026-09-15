"""
Image extraction for blank amounts in financial events.
Uses vision API to extract financial amounts from PNG images.
Isolated from business logic. Results are cached.
"""
from decimal import Decimal
from pathlib import Path
from typing import Optional, Dict
import logging
import re
import json
import base64

from config import MEDIA_DIR, USE_LLM_IMAGE_OCR, LLM_PROVIDER, GOOGLE_API_KEY, OPENAI_API_KEY, AGENTIC_MODE
from models import ImageEvidence
from ollama_client import ollama_client

logger = logging.getLogger(__name__)

# Cache for extracted amounts
_extraction_cache: Dict[str, dict] = {}


def extract_amount_from_image(
    image_evidence: ImageEvidence,
    expected_currency: str,
    home_currency: str,
) -> dict:
    """
    Extract a financial amount from an image file.
    
    Returns:
    {
        "amount": Decimal or None,
        "currency": str or None,
        "confidence": float,
        "raw_text": str,
        "method": str,
    }
    """
    image_id = image_evidence.image_id
    cache_key = image_id
    
    if cache_key in _extraction_cache:
        return _extraction_cache[cache_key]
    
    image_path = MEDIA_DIR / f"{image_id}.png"
    
    if not image_path.exists():
        logger.warning(f"Image not found: {image_path}")
        result = {"amount": None, "currency": None, "confidence": 0.0, 
                  "raw_text": "", "method": "not_found"}
        _extraction_cache[cache_key] = result
        return result
    
    if not USE_LLM_IMAGE_OCR:
        result = {"amount": None, "currency": None, "confidence": 0.0,
                  "raw_text": "", "method": "disabled"}
        _extraction_cache[cache_key] = result
        return result
    
    # Try extraction based on provider
    if AGENTIC_MODE:
        result = _extract_with_ollama(image_path, expected_currency, home_currency)
    elif LLM_PROVIDER == "google" and GOOGLE_API_KEY:
        result = _extract_with_gemini(image_path, expected_currency, home_currency)
    elif LLM_PROVIDER == "openai" and OPENAI_API_KEY:
        result = _extract_with_openai(image_path, expected_currency, home_currency)
    else:
        result = {"amount": None, "currency": None, "confidence": 0.0,
                  "raw_text": "", "method": "no_provider"}
    
    _extraction_cache[cache_key] = result
    return result


def _extract_with_gemini(
    image_path: Path,
    expected_currency: str,
    home_currency: str,
) -> dict:
    """Extract amount using Google Gemini vision API."""
    try:
        import google.generativeai as genai
        from config import LLM_MODEL
        
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel(LLM_MODEL)
        
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        prompt = f"""You are a financial document parser. Extract the total amount from this financial document image.

The document is related to a transaction in {expected_currency} (home currency: {home_currency}).

Extract:
1. The total amount (the main financial figure)
2. The currency

Return ONLY a JSON object with no markdown:
{{"amount": <number>, "currency": "<3-letter-code>", "confidence": <0.0-1.0>}}

If you cannot find a clear amount, return:
{{"amount": null, "currency": null, "confidence": 0.0}}

Be conservative with confidence. Only return high confidence if the amount is clearly legible."""
        
        image_part = {
            "mime_type": "image/png",
            "data": base64.b64encode(image_bytes).decode("utf-8"),
        }
        
        response = model.generate_content([prompt, image_part])
        raw_text = response.text.strip()
        
        # Parse JSON response
        result = _parse_extraction_response(raw_text)
        result["method"] = "gemini"
        result["raw_text"] = raw_text
        return result
        
    except Exception as e:
        logger.error(f"Gemini extraction failed for {image_path}: {e}")
        return {"amount": None, "currency": None, "confidence": 0.0,
                "raw_text": str(e), "method": "gemini_error"}


def _extract_with_openai(
    image_path: Path,
    expected_currency: str,
    home_currency: str,
) -> dict:
    """Extract amount using OpenAI GPT-4 Vision API."""
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        
        prompt = f"""You are a financial document parser. Extract the total amount from this financial document image.

The document is related to a transaction in {expected_currency} (home currency: {home_currency}).

Return ONLY a JSON object:
{{"amount": <number or null>, "currency": "<3-letter-code or null>", "confidence": <0.0-1.0>}}"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{b64_image}",
                        "detail": "low"
                    }}
                ]
            }],
            max_tokens=100,
        )
        
        raw_text = response.choices[0].message.content.strip()
        result = _parse_extraction_response(raw_text)
        result["method"] = "openai"
        result["raw_text"] = raw_text
        return result
        
    except Exception as e:
        logger.error(f"OpenAI extraction failed for {image_path}: {e}")
        return {"amount": None, "currency": None, "confidence": 0.0,
                "raw_text": str(e), "method": "openai_error"}


def _extract_with_ollama(
    image_path: Path,
    expected_currency: str,
    home_currency: str,
) -> dict:
    """Extract amount using Ollama (if vision supported, else fallback gracefully)."""
    try:
        if not ollama_client.is_healthy:
            return {"amount": None, "currency": None, "confidence": 0.0,
                    "raw_text": "ollama_unhealthy", "method": "ollama"}
        
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        
        prompt = f"""You are a financial document parser. Extract the total amount from this financial document image.
The document is related to a transaction in {expected_currency} (home currency: {home_currency}).
Return ONLY a JSON object:
{{"amount": <number or null>, "currency": "<3-letter-code or null>", "confidence": <0.0-1.0>}}"""
        
        import urllib.request
        import urllib.error
        payload = {
            "model": ollama_client.detected_model,
            "prompt": prompt,
            "images": [b64_image],
            "stream": False,
            "format": "json"
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            f"{ollama_client.base_url}/api/generate",
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status == 200:
                resp_data = json.loads(response.read().decode('utf-8'))
                raw_text = resp_data.get('response', '').strip()
                result = _parse_extraction_response(raw_text)
                result["method"] = "ollama"
                result["raw_text"] = raw_text
                return result
            else:
                return {"amount": None, "currency": None, "confidence": 0.0,
                        "raw_text": f"HTTP {response.status}", "method": "ollama_error"}
                
    except Exception as e:
        logger.warning(f"Ollama vision extraction failed (model may not support vision): {e}")
        return {"amount": None, "currency": None, "confidence": 0.0,
                "raw_text": str(e), "method": "ollama_error"}


def _parse_extraction_response(raw_text: str) -> dict:
    """Parse the JSON response from the vision API."""
    try:
        # Clean up any markdown code blocks
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        
        data = json.loads(text)
        amount = data.get("amount")
        currency = data.get("currency")
        confidence = float(data.get("confidence", 0.0))
        
        if amount is not None:
            amount = Decimal(str(amount))
        
        return {
            "amount": amount,
            "currency": currency,
            "confidence": confidence,
            "raw_text": raw_text,
        }
    except Exception as e:
        logger.warning(f"Failed to parse extraction response: {e}. Raw: {raw_text}")
        
        # Try regex fallback
        amount = _regex_extract_amount(raw_text)
        if amount is not None:
            return {"amount": amount, "currency": None, "confidence": 0.5, "raw_text": raw_text}
        
        return {"amount": None, "currency": None, "confidence": 0.0, "raw_text": raw_text}


def _regex_extract_amount(text: str) -> Optional[Decimal]:
    """Fallback regex extraction for common amount patterns."""
    patterns = [
        r'"amount"\s*:\s*([\d,]+\.?\d*)',
        r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'(\d+\.\d{2})',
        r'(\d{4,})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                amount_str = match.group(1).replace(",", "")
                return Decimal(amount_str)
            except Exception:
                continue
    
    return None


def get_cached_results() -> Dict[str, dict]:
    """Get all cached extraction results (for usage reporting)."""
    return dict(_extraction_cache)
