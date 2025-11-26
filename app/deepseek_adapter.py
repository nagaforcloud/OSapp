# app/deepseek_adapter.py
"""
DeepSeek adapter for the Onestream RAG application.
Provides integration with DeepSeek models via OpenAI-compatible API.
"""

import os
from typing import Optional, Dict, Any
from decouple import config as decouple_config

from langchain_core.language_models import BaseLanguageModel
from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Load config and keys
try:
    from config import *
    from keys import get_deepseek_api_key
    DEEPSEEK_API_KEY_AVAILABLE = True
except ImportError:
    get_deepseek_api_key = None
    DEEPSEEK_API_KEY_AVAILABLE = False
    print("Warning: DeepSeek API key management not available.")

class DeepSeekError(Exception):
    """Custom exception for DeepSeek adapter errors."""
    pass

class DeepSeekAdapter:
    """Adapter for DeepSeek API integration."""
    
    def __init__(self):
        """Initialize the DeepSeek adapter."""
        pass
    
    def get_api_key(self) -> str:
        """
        Get DeepSeek API key from environment or .env file.
        
        Returns:
            DeepSeek API key
            
        Raises:
            DeepSeekError: If API key is missing or invalid
        """
        if DEEPSEEK_API_KEY_AVAILABLE:
            try:
                return get_deepseek_api_key()
            except EnvironmentError as e:
                raise DeepSeekError(str(e))
        else:
            # Fallback to direct environment variable access
            key = decouple_config("DEEPSEEK_API_KEY", default=None)
            if not key or key == "your_deepseek_api_key_here":
                raise DeepSeekError(
                    "DEEPSEEK_API_KEY not found or is still the placeholder value. "
                    "Set it in .env or environment variables with your actual API key. "
                    "Get one at https://platform.deepseek.com/"
                )
            return key
    
    def load_deepseek_llm(self, model_name: str = "deepseek-chat", 
                          temperature: float = 0.7, max_tokens: int = 2000,
                          **kwargs) -> ChatOpenAI:
        """
        Load DeepSeek LLM via OpenAI-compatible API.
        
        Args:
            model_name: Name of the DeepSeek model to use
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for ChatOpenAI
            
        Returns:
            ChatOpenAI instance configured for DeepSeek
            
        Raises:
            DeepSeekError: If model cannot be loaded
        """
        try:
            api_key = self.get_api_key()
            
            # Default parameters for DeepSeek
            default_params = {
                "model": model_name,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "openai_api_key": api_key,
                "openai_api_base": "https://api.deepseek.com/v1"
            }
            
            # Update with user-provided parameters
            default_params.update(kwargs)
            
            llm = ChatOpenAI(**default_params)
            return llm
        except Exception as e:
            raise DeepSeekError(f"Failed to load DeepSeek LLM: {str(e)}")
    
    def load_deepseek_embeddings(self, model_name: str = "deepseek-embedding", 
                                  **kwargs) -> OpenAIEmbeddings:
        """
        Load DeepSeek embeddings via OpenAI-compatible API.
        
        Args:
            model_name: Name of the DeepSeek embedding model to use
            **kwargs: Additional parameters for OpenAIEmbeddings
            
        Returns:
            OpenAIEmbeddings instance configured for DeepSeek
            
        Raises:
            DeepSeekError: If embeddings cannot be loaded
        """
        try:
            api_key = self.get_api_key()
            
            # Default parameters for DeepSeek embeddings
            default_params = {
                "model": model_name,
                "openai_api_key": api_key,
                "openai_api_base": "https://api.deepseek.com/v1"
            }
            
            # Update with user-provided parameters
            default_params.update(kwargs)
            
            embeddings = OpenAIEmbeddings(**default_params)
            return embeddings
        except Exception as e:
            raise DeepSeekError(f"Failed to load DeepSeek embeddings: {str(e)}")