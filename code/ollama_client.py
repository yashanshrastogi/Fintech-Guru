import os
import json
import time
import urllib.request
import urllib.error
import logging
import hashlib
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse

from config import (
    OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT, OLLAMA_MAX_RETRIES,
    AGENT_TEMPERATURE
)

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for local Ollama API with structured output and health checking."""
    
    def __init__(self):
        self.base_url = OLLAMA_BASE_URL.rstrip('/')
        self.model_override = OLLAMA_MODEL
        self.detected_model = None
        self.is_healthy = False
        self._cache = {}
        
        # Enforce local-only policy
        self._enforce_local_policy()

    def _enforce_local_policy(self):
        """Ensure no cloud LLM API calls are made."""
        parsed = urlparse(self.base_url)
        hostname = parsed.hostname or ""
        
        allowed_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "[::1]"}
        
        if hostname not in allowed_hosts:
            logger.error(f"External LLM endpoint blocked by local-only policy: {self.base_url}")
            raise RuntimeError("External LLM endpoint blocked by local-only policy. Only localhost is permitted.")

    def check_health(self) -> Tuple[bool, Optional[str]]:
        """
        Check if Ollama is reachable and auto-detect Qwen 3 7B model if not overridden.
        Returns: (is_healthy, detected_model_name)
        """
        if self.model_override:
            self.detected_model = self.model_override
            self.is_healthy = self._ping_ollama()
            return self.is_healthy, self.detected_model

        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    models = data.get('models', [])
                    model_names = [m.get('name') for m in models]
                    
                    # Look for qwen3 8b variants
                    qwen_models = [name for name in model_names if 'qwen' in name.lower()]
                    
                    if not qwen_models:
                        logger.warning("Ollama reachable but no Qwen models found.")
                        self.is_healthy = False
                        return False, None
                        
                    # Prioritize exact 'qwen3:8b' or similar
                    target_model = None
                    for name in qwen_models:
                        if 'qwen3:8b' in name.lower() or 'qwen' in name.lower():
                            target_model = name
                            break
                    
                    if not target_model:
                        target_model = qwen_models[0]
                        
                    self.detected_model = target_model
                    self.is_healthy = True
                    return True, self.detected_model
                else:
                    self.is_healthy = False
                    return False, None
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            self.is_healthy = False
            return False, None

    def _ping_ollama(self) -> bool:
        """Check if base URL is responsive."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/version")
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except Exception:
            return False

    def chat_completion(
        self, 
        prompt: str, 
        agent: str = "generic", 
        response_format: str = "json",
        cache_key: Optional[str] = None
    ) -> Tuple[Optional[str], float, int, int]:
        """
        Execute a chat completion request to Ollama.
        Returns: (text, latency_ms, input_tokens, output_tokens)
        """
        if not self.is_healthy or not self.detected_model:
            logger.warning("Ollama not healthy, skipping chat completion.")
            return None, 0.0, 0, 0
            
        if cache_key and cache_key in self._cache:
            logger.info(f"Ollama cache hit for key {cache_key}")
            return self._cache[cache_key]

        start_time = time.time()
        
        payload = {
            "model": self.detected_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": AGENT_TEMPERATURE
            }
        }
        
        if response_format == "json":
            payload["format"] = "json"
            
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        retries = OLLAMA_MAX_RETRIES
        for attempt in range(retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as response:
                    if response.status == 200:
                        resp_data = json.loads(response.read().decode('utf-8'))
                        text = resp_data.get('response', '')
                        
                        latency_ms = (time.time() - start_time) * 1000
                        eval_count = resp_data.get('eval_count', 0)
                        prompt_eval_count = resp_data.get('prompt_eval_count', 0)
                        
                        result = (text, latency_ms, prompt_eval_count, eval_count)
                        if cache_key:
                            self._cache[cache_key] = result
                        return result
                    
            except Exception as e:
                logger.warning(f"Ollama completion failed (attempt {attempt+1}/{retries+1}): {e}")
                if attempt == retries:
                    break
                time.sleep(1.0)
                
        return None, 0.0, 0, 0

    def structured_completion(
        self, 
        prompt: str, 
        agent: str = "generic",
        cache_key: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], float, int, int]:
        """
        Get structured JSON output, attempting a repair if malformed.
        """
        text, latency, in_tokens, out_tokens = self.chat_completion(
            prompt, agent, "json", cache_key=cache_key
        )
        
        if not text:
            return None, latency, in_tokens, out_tokens
            
        try:
            return json.loads(text), latency, in_tokens, out_tokens
        except json.JSONDecodeError:
            logger.warning(f"Malformed JSON from agent {agent}. Attempting repair...")
            # Repair attempt: Ask LLM to fix it
            repair_prompt = f"Fix this invalid JSON and return ONLY valid JSON without markdown blocks:\n\n{text}"
            repair_text, r_latency, r_in, r_out = self.chat_completion(repair_prompt, agent, "json")
            
            try:
                if repair_text:
                    parsed = json.loads(repair_text)
                    return parsed, latency + r_latency, in_tokens + r_in, out_tokens + r_out
            except json.JSONDecodeError:
                logger.error(f"Agent {agent} failed JSON repair.")
                
            return None, latency, in_tokens, out_tokens

# Global client singleton
ollama_client = OllamaClient()
