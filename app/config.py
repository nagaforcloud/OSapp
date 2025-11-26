# app/config.py
"""
Configuration module for the Onestream RAG application.
Handles loading and validation of environment variables and application settings.
"""

import os
from typing import List, Optional

class ConfigError(Exception):
    """Custom exception for configuration errors"""
    pass

def get_env_var(var_name: str, default: Optional[str] = None, required: bool = False) -> str:
    """
    Get environment variable with proper error handling.
    
    Args:
        var_name: Name of the environment variable
        default: Default value if not found
        required: Whether the variable is required
        
    Returns:
        Value of the environment variable
        
    Raises:
        ConfigError: If required variable is missing
    """
    value = os.getenv(var_name, default)
    if required and (value is None or value == ""):
        raise ConfigError(f"Required environment variable {var_name} is not set")
    return value

def get_env_int(var_name: str, default: int, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
    """
    Get integer environment variable with validation.
    
    Args:
        var_name: Name of the environment variable
        default: Default value if not found
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Integer value of the environment variable
        
    Raises:
        ConfigError: If value is not a valid integer or out of bounds
    """
    try:
        value_str = os.getenv(var_name)
        if value_str is None:
            return default
            
        value = int(value_str)
        
        if min_val is not None and value < min_val:
            raise ConfigError(f"Environment variable {var_name} must be >= {min_val}")
            
        if max_val is not None and value > max_val:
            raise ConfigError(f"Environment variable {var_name} must be <= {max_val}")
            
        return value
    except ValueError:
        raise ConfigError(f"Environment variable {var_name} must be a valid integer")

# --- App UI ---
APP_TITLE = "🤖 Onestream RAG Assistant"
APP_ICON = "📚"
APP_LAYOUT = "wide"
CHAT_INPUT = "Ask a question about Onestream..."

# --- Paths (use environment variables or defaults) ---
try:
    DOCUMENTS_DIR = get_env_var("DOCUMENTS_DIR", "data/documents")
    QDRANT_PATH = get_env_var("QDRANT_PATH", "vector_db")
    DEFAULT_COLLECTION = get_env_var("DEFAULT_COLLECTION", "onestream_docs")
    
    # Validate paths exist or can be created
    os.makedirs(DOCUMENTS_DIR, exist_ok=True)
    os.makedirs(QDRANT_PATH, exist_ok=True)
except Exception as e:
    raise ConfigError(f"Error setting up paths: {e}")

# --- File Support ---
SUPPORTED_TYPES: List[str] = [".pdf", ".txt", ".md"]

# --- Chunking ---
try:
    CHUNK_SIZE = get_env_int("CHUNK_SIZE", 1000, min_val=100, max_val=10000)
    CHUNK_OVERLAP = get_env_int("CHUNK_OVERLAP", 200, min_val=0, max_val=CHUNK_SIZE // 2)
except ConfigError as e:
    raise ConfigError(f"Chunking configuration error: {e}")

# --- Qdrant ---
VECTOR_SIZE = 384  # Changed from 1024 to match BERT embedding model (bge-small-en-v1.5)
DISTANCE = "COSINE"  # COSINE, DOT, EUCLID

# --- LLM ---
LLM_MODEL = get_env_var("LLM_MODEL", "deepseek-chat")
EMBEDDING_MODEL = get_env_var("EMBEDDING_MODEL", "text-embedding-ada-002")

# --- Inference Service Configuration ---
USE_LOCAL_LLM = get_env_var("USE_LOCAL_LLM", "false").lower() == "true"
LLM_SERVICE_URL = get_env_var("LLM_SERVICE_URL", "http://llm-service:8000")

# --- Qwen Coder Plus Settings ---
QWEN_CODER_MODEL = get_env_var("QWEN_CODER_MODEL", "qwen-coder-plus")

# --- Local LLM Settings ---
LOCAL_LLM_MODEL_PATH = get_env_var("LOCAL_LLM_MODEL_PATH", "models/mistral-7b-instruct-v0.2.Q4_K_M.gguf")
LOCAL_EMBEDDING_MODEL_PATH = get_env_var("LOCAL_EMBEDDING_MODEL_PATH", "models/bge-small-en-v1.5-q4_k_m.gguf")
# Validate that the model paths exist or fall back to defaults
import os
from pathlib import Path

# Check if the configured paths exist, if not fall back to defaults
DEFAULT_LLM_MODEL_PATH = "models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
DEFAULT_EMBEDDING_MODEL_PATH = "models/bge-small-en-v1.5-q4_k_m.gguf"

# Validate LLM model path
if LOCAL_LLM_MODEL_PATH and not Path(LOCAL_LLM_MODEL_PATH).exists():
    print(f"Warning: Configured LLM model path '{LOCAL_LLM_MODEL_PATH}' not found, falling back to default")
    LOCAL_LLM_MODEL_PATH = DEFAULT_LLM_MODEL_PATH

# Validate embedding model path  
if LOCAL_EMBEDDING_MODEL_PATH and not Path(LOCAL_EMBEDDING_MODEL_PATH).exists():
    print(f"Warning: Configured embedding model path '{LOCAL_EMBEDDING_MODEL_PATH}' not found, falling back to default")
    LOCAL_EMBEDDING_MODEL_PATH = DEFAULT_EMBEDDING_MODEL_PATH

LOCAL_LLM_CONTEXT_SIZE = get_env_int("LOCAL_LLM_CONTEXT_SIZE", 2048, min_val=512, max_val=32768)
LOCAL_LLM_MAX_TOKENS = get_env_int("LOCAL_LLM_MAX_TOKENS", 2000, min_val=100, max_val=8192)
LOCAL_LLM_TEMPERATURE = float(os.getenv("LOCAL_LLM_TEMPERATURE", "0.7"))

# --- Retrieval ---
try:
    TOP_K = get_env_int("TOP_K", 4, min_val=1, max_val=20)
except ConfigError as e:
    raise ConfigError(f"Retrieval configuration error: {e}")

# --- Prompt ---
RAG_PROMPT = """\

You are an expert AI assistant with access to the following context.
Answer the question in detail, using information from the context.
If possible, provide step-by-step explanations and include a practical example to illustrate your answer.
Make sure your response is clear, thorough, and easy to understand.

Context:
{context}

Question:
{question}

Instructions for your answer:
- Provide a detailed explanation.
- Break down complex ideas into simple steps.
- If applicable, include a real-world or practical example.
- Do not say "according to the context" — just answer confidently.
- If the context doesn't contain the answer, say "I cannot answer this based on the available documents."

Answer:

"""
