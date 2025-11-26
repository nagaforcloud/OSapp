# app/qwen_adapter.py
"""
Qwen Coder Plus adapter for the Onestream RAG application.
Provides integration with Alibaba's Qwen Coder Plus model via API.
"""

import os
import json
import requests
from typing import List, Optional, Dict, Any
from decouple import config as decouple_config

from langchain_core.language_models import BaseLanguageModel
from langchain_core.embeddings import Embeddings
try:
    # Try newer pydantic first
    from pydantic import BaseModel, Field
except ImportError:
    # Fall back to langchain's compatibility shim
    from langchain_core.pydantic_v1 import BaseModel, Field

class QwenError(Exception):
    """Custom exception for Qwen adapter errors."""
    pass

class QwenChatMessage(BaseModel):
    """Represents a message in a Qwen chat conversation."""
    role: str
    content: str

class QwenChatRequest(BaseModel):
    """Represents a request to the Qwen chat API."""
    model: str = Field(default="qwen-coder-plus")
    input: Dict[str, Any] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)

class QwenEmbeddingsRequest(BaseModel):
    """Represents a request to the Qwen embeddings API."""
    model: str = Field(default="qwen-coder-plus")
    input: Dict[str, Any] = Field(default_factory=dict)

class QwenLLM(BaseLanguageModel):
    """Qwen Coder Plus LLM implementation."""
    
    model_name: str = "qwen-coder-plus"
    api_key: str
    api_url: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    temperature: float = 0.7
    max_tokens: int = 2000
    
    def __init__(self, api_key: str, model_name: str = "qwen-coder-plus", 
                 temperature: float = 0.7, max_tokens: int = 2000, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    def _call_api(self, messages: List[QwenChatMessage]) -> str:
        """Call the Qwen API with the given messages."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "input": {
                "messages": [msg.dict() for msg in messages]
            },
            "parameters": {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["output"]["text"]
        except requests.exceptions.RequestException as e:
            raise QwenError(f"API request failed: {str(e)}")
        except KeyError as e:
            raise QwenError(f"Unexpected API response format: {str(e)}")
    
    def invoke(self, prompt, **kwargs) -> Any:
        """Invoke the LLM with a prompt."""
        messages = [QwenChatMessage(role="user", content=prompt)]
        response = self._call_api(messages)
        # Create a simple response object with content attribute
        class Response:
            def __init__(self, content):
                self.content = content
        return Response(response)
    
    @property
    def _llm_type(self) -> str:
        return "qwen"

class QwenEmbeddings(Embeddings):
    """Qwen Coder Plus embeddings implementation."""
    
    model_name: str = "qwen-coder-plus"
    api_key: str
    api_url: str = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
    
    def __init__(self, api_key: str, model_name: str = "qwen-coder-plus", **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.model_name = model_name
    
    def _call_embeddings_api(self, texts: List[str]) -> List[List[float]]:
        """Call the Qwen embeddings API with the given texts."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "input": {
                "texts": texts
            }
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["output"]["embeddings"]
        except requests.exceptions.RequestException as e:
            raise QwenError(f"API request failed: {str(e)}")
        except KeyError as e:
            raise QwenError(f"Unexpected API response format: {str(e)}")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        return self._call_embeddings_api(texts)
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        embeddings = self._call_embeddings_api([text])
        return embeddings[0] if embeddings else []

class QwenAdapter:
    """Adapter for Qwen Coder Plus API."""
    
    def __init__(self):
        """Initialize the Qwen adapter."""
        pass
    
    def get_api_key(self) -> str:
        """Get Qwen API key from environment or .env file."""
        key = decouple_config("QWEN_CODER_API_KEY", default=None)
        if not key or key == "your_qwen_coder_api_key_here":
            raise QwenError(
                "QWEN_CODER_API_KEY not found or is still the placeholder value. "
                "Set it in .env or environment variables with your actual API key."
            )
        return key
    
    def load_qwen_llm(self, model_name: str = "qwen-coder-plus", 
                      temperature: float = 0.7, max_tokens: int = 2000) -> QwenLLM:
        """
        Load Qwen Coder Plus LLM.
        
        Args:
            model_name: Name of the Qwen model to use
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            QwenLLM instance
        """
        try:
            api_key = self.get_api_key()
            llm = QwenLLM(
                api_key=api_key,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return llm
        except Exception as e:
            raise QwenError(f"Failed to load Qwen LLM: {str(e)}")
    
    def load_qwen_embeddings(self, model_name: str = "qwen-coder-plus") -> QwenEmbeddings:
        """
        Load Qwen Coder Plus embeddings.
        
        Args:
            model_name: Name of the Qwen model to use
            
        Returns:
            QwenEmbeddings instance
        """
        try:
            api_key = self.get_api_key()
            embeddings = QwenEmbeddings(
                api_key=api_key,
                model_name=model_name
            )
            return embeddings
        except Exception as e:
            raise QwenError(f"Failed to load Qwen embeddings: {str(e)}")