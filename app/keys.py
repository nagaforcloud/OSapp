# app/keys.py
"""
API key management module for the Onestream RAG application.
Handles loading and validation of API keys from environment variables or .env files.
"""

from decouple import config as decouple_config

# --- Primary Functions ---
def get_mistral_api_key():
    """Get Mistral API key from environment or .env file."""
    key = decouple_config("MISTRAL_API_KEY", default=None)
    if not key or key == "your_mistral_api_key_here":
        raise EnvironmentError(
            "MISTRAL_API_KEY not found or is still the placeholder value. "
            "Set it in .env or environment variables with your actual API key. "
            "Get one at https://console.mistral.ai/"
        )
    return key

def get_deepseek_api_key():
    """Get DeepSeek API key from environment or .env file."""
    key = decouple_config("DEEPSEEK_API_KEY", default=None)
    if not key or key == "your_deepseek_api_key_here":
        raise EnvironmentError(
            "DEEPSEEK_API_KEY not found or is still the placeholder value. "
            "Set it in .env or environment variables with your actual API key. "
            "Get one at https://platform.deepseek.com/"
        )
    return key

def get_qwen_api_key():
    """Get Qwen API key from environment or .env file."""
    key = decouple_config("QWEN_CODER_API_KEY", default=None)
    if not key or key == "your_qwen_coder_api_key_here":
        raise EnvironmentError(
            "QWEN_CODER_API_KEY not found or is still the placeholder value. "
            "Set it in .env or environment variables with your actual API key. "
            "Get one from Alibaba Cloud DashScope."
        )
    return key

def get_langchain_api_key():
    """Get LangChain API key from environment or .env file."""
    key = decouple_config("LANGCHAIN_API_KEY", default=None)
    # Optional: LangChain tracing works without a key (but better with one)
    if not key:
        print("⚠️ LANGCHAIN_API_KEY not set. Tracing may be limited.")
    return key

# --- Optional: Validate required keys at import (only if required)
if __name__ == "__main__":
    # This runs only if you execute keys.py directly
    pass
else:
    # Optional: Enforce Mistral key on import (only if using Mistral)
    # We don't enforce Qwen key here because it's only needed when using Qwen
    pass
