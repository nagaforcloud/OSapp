# services/inference_api/config.py
"""
Configuration management for the inference service.
"""

import os
from pathlib import Path
from decouple import config, Csv

class Config:
    """Configuration for LLM inference service."""

    # Service configuration
    HOST = config('HOST', default='0.0.0.0', cast=str)
    PORT = config('PORT', default=8000, cast=int)
    WORKERS = config('WORKERS', default=1, cast=int)
    LOG_LEVEL = config('LOG_LEVEL', default='INFO', cast=str)

    # Model configuration
    MODEL_PATH = config('LOCAL_LLM_MODEL_PATH', default='/app/models/mistral-7b-instruct.gguf', cast=str)
    MODEL_N_CTX = config('LOCAL_MODEL_N_CTX', default=4096, cast=int)
    MODEL_N_GPU_LAYERS = config('LOCAL_MODEL_N_GPU_LAYERS', default=0, cast=int)
    MODEL_VERBOSE = config('LOCAL_MODEL_VERBOSE', default=False, cast=bool)

    # Inference parameters
    DEFAULT_MAX_TOKENS = config('DEFAULT_MAX_TOKENS', default=2048, cast=int)
    DEFAULT_TEMPERATURE = config('DEFAULT_TEMPERATURE', default=0.7, cast=float)
    DEFAULT_TOP_P = config('DEFAULT_TOP_P', default=0.9, cast=float)
    DEFAULT_REPEAT_PENALTY = config('DEFAULT_REPEAT_PENALTY', default=1.1, cast=float)

    # Performance settings
    MODEL_THREADS = config('MODEL_THREADS', default=os.cpu_count(), cast=int)
    USE_MMAP = config('USE_MMAP', default=True, cast=bool)
    USE_MLOCK = config('USE_MLOCK', default=False, cast=bool)

    # Monitoring
    ENABLE_METRICS = config('ENABLE_METRICS', default=True, cast=bool)
    METRICS_PORT = config('METRICS_PORT', default=9091, cast=int)
    HEALTH_CHECK_INTERVAL = config('HEALTH_CHECK_INTERVAL', default=30, cast=int)

    # Security
    MAX_REQUEST_SIZE = config('MAX_REQUEST_SIZE', default=10*1024*1024, cast=int)  # 10MB
    RATE_LIMIT_REQUESTS = config('RATE_LIMIT_REQUESTS', default=100, cast=int)
    RATE_LIMIT_WINDOW = config('RATE_LIMIT_WINDOW', default=60, cast=int)  # seconds

    # Paths
    MODELS_DIR = Path(config('MODELS_DIR', default='/app/models', cast=str))
    LOGS_DIR = Path(config('LOGS_DIR', default='/app/logs', cast=str))

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration."""
        try:
            # Validate paths
            cls.MODELS_DIR.mkdir(parents=True, exist_ok=True)
            cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)

            # Validate model file
            if not cls.MODEL_PATH:
                print("ERROR: LOCAL_LLM_MODEL_PATH not specified")
                return False

            model_file = Path(cls.MODEL_PATH)
            if not model_file.exists():
                print(f"ERROR: Model file not found: {cls.MODEL_PATH}")
                return False

            if not model_file.suffix == '.gguf':
                print(f"ERROR: Model file must be .gguf format: {cls.MODEL_PATH}")
                return False

            # Validate numerical values
            if cls.MODEL_N_CTX <= 0 or cls.MODEL_N_CTX > 8192:
                print(f"ERROR: Invalid context size: {cls.MODEL_N_CTX}")
                return False

            if cls.DEFAULT_MAX_TOKENS <= 0 or cls.DEFAULT_MAX_TOKENS > cls.MODEL_N_CTX:
                print(f"ERROR: Invalid max_tokens: {cls.DEFAULT_MAX_TOKENS}")
                return False

            if cls.DEFAULT_TEMPERATURE < 0.0 or cls.DEFAULT_TEMPERATURE > 2.0:
                print(f"ERROR: Invalid temperature: {cls.DEFAULT_TEMPERATURE}")
                return False

            return True

        except Exception as e:
            print(f"ERROR: Configuration validation failed: {e}")
            return False

# Global config instance
cfg = Config()