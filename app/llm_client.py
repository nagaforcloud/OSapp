# app/llm_client.py
"""
Client for communicating with the dedicated LLM inference service.
Replaces local llama.cpp loading in the main application.
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
import httpx
from app.config import Config
from app.logger import info, warning, error

class LLMInferenceClient:
    """Client for LLM inference microservice."""

    def __init__(self):
        """Initialize the LLM inference client."""
        self.service_url = Config.LLM_SERVICE_URL
        self.timeout = 300  # 5 minutes
        self.max_retries = 3

        # Create HTTP client with connection pooling
        self.client = httpx.Client(
            timeout=httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )

    async def _make_request(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Make a request to the inference service."""
        request_data = {
            "model": kwargs.get("model", "local-model"),
            "messages": [{"role": msg["role"], "content": msg["content"]} for msg in messages],
            "max_tokens": kwargs.get("max_tokens", 2048),
            "temperature": kwargs.get("temperature", 0.7),
            "stream": False,
            "user": kwargs.get("user", "streamlit_user")
        }

        for attempt in range(self.max_retries):
            try:
                response = self.client.post(
                    f"{self.service_url}/v1/chat/completions",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                return response.json()

            except httpx.ConnectError as e:
                if attempt == self.max_retries - 1:
                    error(f"Failed to connect to LLM service after {self.max_retries} attempts: {e}")
                    raise
                warning(f"Connection to LLM service failed (attempt {attempt + 1}/{self.max_retries}), retrying...")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

            except httpx.HTTPStatusError as e:
                error(f"LLM service returned error {e.response.status_code}: {e.response.text}")
                raise

            except Exception as e:
                if attempt == self.max_retries - 1:
                    error(f"Unexpected error calling LLM service: {e}")
                    raise
                warning(f"Error calling LLM service (attempt {attempt + 1}/{self.max_retries}), retrying...")
                await asyncio.sleep(1)

    async def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a response from the LLM inference service."""
        try:
            start_time = time.time()

            response = await self._make_request(messages, **kwargs)

            generation_time = time.time() - start_time

            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]

                # Log generation metrics
                usage = response.get("usage", {})
                info("LLM inference completed",
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                    generation_time=generation_time,
                    service_url=self.service_url
                )

                return content.strip()
            else:
                error("Invalid response from LLM service", response=response)
                raise ValueError("Invalid response from LLM service")

        except Exception as e:
            error(f"Failed to generate response: {e}")
            raise

    def health_check(self) -> bool:
        """Check if the LLM inference service is healthy."""
        try:
            response = self.client.get(f"{self.service_url}/health", timeout=10)
            return response.status_code == 200
        except Exception as e:
            warning(f"LLM service health check failed: {e}")
            return False

    def get_model_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the loaded model."""
        try:
            response = self.client.get(f"{self.service_url}/v1/models", timeout=10)
            if response.status_code == 200:
                models = response.json().get("data", [])
                if models:
                    return models[0]  # Return first model info
            return None
        except Exception as e:
            warning(f"Failed to get model info: {e}")
            return None

    def reload_model(self) -> bool:
        """Request model reload in the inference service."""
        try:
            response = self.client.post(f"{self.service_url}/reload_model", timeout=60)
            if response.status_code == 200:
                result = response.json()
                info("Model reload requested", result=result)
                return result.get("status") == "success"
            return False
        except Exception as e:
            error(f"Failed to reload model: {e}")
            return False

    def close(self):
        """Close the HTTP client."""
        self.client.close()

# Global client instance
_llm_client = None

def get_llm_client() -> LLMInferenceClient:
    """Get or create the global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMInferenceClient()
        info("LLM inference client initialized", service_url=_llm_client.service_url)
    return _llm_client

# Compatibility interface for existing code
class LlamaCppAdapter:
    """Adapter that mimics the original llama.cpp adapter but uses the inference service."""

    def __init__(self, model_path=None, n_ctx=2048, temperature=0.7, **kwargs):
        """Initialize the adapter (ignores local parameters)."""
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.temperature = temperature
        self.client = get_llm_client()

        info("Created LLM inference client adapter",
             local_model_path=model_path,
             service_url=self.client.service_url)

    def __call__(self, prompt: str, **kwargs) -> str:
        """Generate response using the inference service."""
        # Convert simple prompt to messages format
        messages = [{"role": "user", "content": prompt}]

        # Set parameters from kwargs or defaults
        max_tokens = kwargs.get("max_tokens", self.n_ctx)
        temperature = kwargs.get("temperature", self.temperature)

        return self.client.generate_response(
            messages,
            max_tokens=max_tokens,
            temperature=temperature
        )

# Global instance for compatibility
local_llm_adapter = None

def initialize_local_llm():
    """Initialize the local LLM adapter (now using inference service)."""
    global local_llm_adapter

    if Config.USE_LOCAL_LLM or Config.LLM_MODEL.startswith("local"):
        # Use the inference service instead of loading locally
        local_llm_adapter = LlamaCppAdapter(
            model_path=Config.LOCAL_LLM_MODEL_PATH,
            n_ctx=Config.LOCAL_LLM_CONTEXT_SIZE,
            temperature=Config.LOCAL_LLM_TEMPERATURE
        )
        info("Local LLM adapter initialized via inference service")
    else:
        info("Using cloud LLM provider, local LLM disabled")
        local_llm_adapter = None

def get_local_llm_adapter():
    """Get the local LLM adapter instance."""
    return local_llm_adapter