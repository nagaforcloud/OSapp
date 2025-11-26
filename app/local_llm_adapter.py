# app/local_llm_adapter.py
"""
Local LLM adapter for llama.cpp integration with the Onestream RAG application.
This module provides adapters for running local LLMs using llama.cpp through LangChain.
"""

import os
from typing import Optional, Dict, Any, List
from pathlib import Path

# Try to import local LLM components
try:
    from langchain_community.llms import LlamaCpp
    from langchain_community.embeddings import LlamaCppEmbeddings
    from langchain_core.embeddings import Embeddings
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LlamaCpp = None
    LlamaCppEmbeddings = None
    Embeddings = object  # Fallback for type hints
    LLAMA_CPP_AVAILABLE = False
    print("Warning: llama-cpp-python not installed. Local LLM support will be disabled.")

class LocalLLMError(Exception):
    """Custom exception for local LLM errors."""
    pass

class LocalLLMAdapter:
    """Adapter for local LLMs using llama.cpp."""
    
    def __init__(self):
        """Initialize the local LLM adapter."""
        if not LLAMA_CPP_AVAILABLE:
            raise LocalLLMError(
                "Local LLM support is not available. "
                "Please install llama-cpp-python: pip install llama-cpp-python"
            )
    
    def validate_model_path(self, model_path: str) -> bool:
        """
        Validate that the model path exists and is accessible.
        
        Args:
            model_path: Path to the model file
            
        Returns:
            Whether the path is valid
        """
        if not model_path:
            return False
            
        path = Path(model_path)
        return path.exists() and path.is_file()
    
    def load_local_llm(self, model_path: str, **kwargs) -> LlamaCpp:
        """
        Load a local LLM using llama.cpp.
        
        Args:
            model_path: Path to the GGUF model file
            **kwargs: Additional parameters for LlamaCpp
            
        Returns:
            LlamaCpp instance
            
        Raises:
            LocalLLMError: If model cannot be loaded
        """
        if not self.validate_model_path(model_path):
            raise LocalLLMError(f"Model file not found or inaccessible: {model_path}")
        
        # Default parameters for LlamaCpp
        default_params = {
            "temperature": 0.7,
            "max_tokens": 2000,
            "top_p": 1,
            "n_ctx": 2048,  # Context window size
            "n_threads": os.cpu_count() or 4,  # Use CPU cores
            "n_batch": 512,  # Batch size for prompt processing
            "verbose": False  # Reduce verbose output
        }
        
        # Update with user-provided parameters
        default_params.update(kwargs)
        
        try:
            llm = LlamaCpp(
                model_path=model_path,
                **default_params
            )
            return llm
        except Exception as e:
            raise LocalLLMError(f"Failed to load local LLM: {str(e)}")
    
    def load_local_embeddings(self, model_path: str, **kwargs) -> Any:
        """
        Load local embeddings model using llama.cpp.
        
        Args:
            model_path: Path to the GGUF model file for embeddings
            **kwargs: Additional parameters for LlamaCppEmbeddings
            
        Returns:
            Embeddings instance (either LlamaCppEmbeddings or BertEmbeddings)
            
        Raises:
            LocalLLMError: If model cannot be loaded
        """
        if not self.validate_model_path(model_path):
            raise LocalLLMError(f"Embeddings model file not found or inaccessible: {model_path}")
        
        # Check if this is a BERT model by examining the file name
        is_bert_model = any(bert_name in model_path.lower() for bert_name in [
            'bge', 'bert', 'roberta', 'mpnet'
        ])
        
        if is_bert_model:
            # Use custom BERT embeddings for BGE/BERT models
            try:
                default_params = {
                    "n_ctx": 512,  # BERT models typically have 512 context length
                    "n_threads": os.cpu_count() or 4,
                    "embedding": True,  # Enable embedding mode
                    "verbose": False
                }
                
                # Update with user-provided parameters
                default_params.update(kwargs)
                
                embeddings = BertEmbeddings(
                    model_path=model_path,
                    **default_params
                )
                return embeddings
            except Exception as e:
                raise LocalLLMError(f"Failed to load BERT embeddings: {str(e)}")
        else:
            # Use LlamaCppEmbeddings for LLaMA-style models
            # Default parameters for LlamaCppEmbeddings
            default_params = {
                "n_ctx": 2048,  # Context window size
                "n_threads": os.cpu_count() or 4,  # Use CPU cores
            }
            
            # Update with user-provided parameters
            default_params.update(kwargs)
            
            try:
                embeddings = LlamaCppEmbeddings(
                    model_path=model_path,
                    **default_params
                )
                return embeddings
            except Exception as e:
                raise LocalLLMError(f"Failed to load local embeddings: {str(e)}")
    
    def get_model_info(self, model_path: str) -> Dict[str, Any]:
        """
        Get information about a local model.
        
        Args:
            model_path: Path to the model file
            
        Returns:
            Dictionary with model information
        """
        if not self.validate_model_path(model_path):
            return {"error": f"Model file not found: {model_path}"}
        
        try:
            path = Path(model_path)
            stat = path.stat()
            
            return {
                "name": path.name,
                "path": str(path.absolute()),
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": stat.st_mtime,
                "valid": True
            }
        except Exception as e:
            return {"error": f"Failed to get model info: {str(e)}"}

    def check_recommended_models(self) -> Dict[str, Any]:
        """
        Check if recommended models exist.
        
        Returns:
            Dictionary with information about recommended models
        """
        models_dir = Path("models")
        recommended_models = {
            "llm_model": {
                "filename": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
                "path": models_dir / "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
                "exists": False,
                "recommended": True
            },
            "embedding_model": {
                "filename": "bge-small-en-v1.5-q4_k_m.gguf",
                "path": models_dir / "bge-small-en-v1.5-q4_k_m.gguf",
                "exists": False,
                "recommended": True
            }
        }
        
        # Check if models directory exists
        if not models_dir.exists():
            return {
                "models_dir_exists": False,
                "models": recommended_models,
                "message": "Models directory not found. Run 'python download_models.py' to download recommended models."
            }
        
        # Check each recommended model
        for model_key, model_info in recommended_models.items():
            if model_info["path"].exists():
                recommended_models[model_key]["exists"] = True
                # Get model info
                model_stats = model_info["path"].stat()
                recommended_models[model_key]["size_mb"] = round(model_stats.st_size / (1024 * 1024), 2)
        
        models_exist = all(model["exists"] for model in recommended_models.values())
        
        return {
            "models_dir_exists": True,
            "models": recommended_models,
            "all_models_exist": models_exist,
            "message": "All recommended models found!" if models_exist else "Some recommended models are missing. Run 'python download_models.py' to download them."
        }


class BertEmbeddings(Embeddings):
    """Custom embeddings class for BERT models using llama.cpp."""
    
    def __init__(self, model_path: str, **kwargs):
        """
        Initialize BERT embeddings with llama.cpp.
        
        Args:
            model_path: Path to the GGUF BERT model file
            **kwargs: Additional parameters for the Llama model
        """
        if not LLAMA_CPP_AVAILABLE:
            raise ImportError("llama-cpp-python is not installed")
            
        try:
            from llama_cpp import Llama
        except ImportError as e:
            raise ImportError(f"Failed to import Llama from llama_cpp: {e}")
            
        # Default parameters optimized for BERT models
        default_params = {
            "n_ctx": 512,  # BERT models typically have 512 context length
            "n_threads": os.cpu_count() or 4,
            "embedding": True,  # Enable embedding mode
            "verbose": False
        }
        
        # Update with user-provided parameters
        default_params.update(kwargs)
        
        # Initialize the Llama model
        self.model = Llama(model_path=model_path, **default_params)
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        embeddings = []
        for text in texts:
            # For BERT models, we need to use the correct embedding method
            # The embed method should work for BERT models when embedding=True is set
            try:
                result = self.model.embed(text)
                embeddings.append(result)
            except Exception as e:
                # If direct embedding fails, try using the predict method with embedding=True
                try:
                    # For BERT models, we might need to format the text differently
                    # BERT models typically expect [CLS] token at the beginning
                    formatted_text = f"[CLS] {text} [SEP]"
                    result = self.model.embed(formatted_text)
                    embeddings.append(result)
                except Exception as e2:
                    # If both methods fail, raise an informative error
                    raise Exception(f"Failed to embed text: {str(e)}. Alternative method also failed: {str(e2)}")
        return embeddings
        
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        try:
            result = self.model.embed(text)
            return result
        except Exception as e:
            # If direct embedding fails, try using the predict method with embedding=True
            try:
                # For BERT models, we might need to format the text differently
                # BERT models typically expect [CLS] token at the beginning
                formatted_text = f"[CLS] {text} [SEP]"
                result = self.model.embed(formatted_text)
                return result
            except Exception as e2:
                # If both methods fail, raise an informative error
                raise Exception(f"Failed to embed query: {str(e)}. Alternative method also failed: {str(e2)}")


def create_local_llm_example():
    pass  # Placeholder function
