# services/inference_api/main.py
"""
Dedicated LLM inference microservice.
Hosts local LLM models and provides OpenAI-compatible API.
"""

import os
import time
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import structlog

# Configure structured logging
logger = structlog.get_logger()

# Initialize FastAPI app
app = FastAPI(
    title="Onestream RAG Inference Service",
    description="Dedicated LLM inference microservice",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
model = None
model_info = {}
inference_stats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "total_tokens": 0,
    "start_time": time.time()
}


class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role (system, user, assistant)")
    content: str = Field(..., description="Message content")


class ChatCompletionRequest(BaseModel):
    model: str = Field(default="local-model", description="Model name")
    messages: List[ChatMessage] = Field(..., description="Conversation messages")
    max_tokens: Optional[int] = Field(default=2048, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(default=0.7, description="Sampling temperature")
    stream: Optional[bool] = Field(default=False, description="Enable streaming")
    user: Optional[str] = Field(default=None, description="User identifier")


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: UsageInfo


class ErrorResponse(BaseModel):
    error: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    uptime_seconds: float
    requests_processed: int
    memory_usage_mb: float


def load_model():
    """Load the local LLM model."""
    global model, model_info

    try:
        # Get model configuration from environment
        model_path = os.getenv('LOCAL_LLM_MODEL_PATH', '/app/models/mistral-7b-instruct.gguf')
        n_ctx = int(os.getenv('LOCAL_MODEL_N_CTX', '4096'))
        n_gpu_layers = int(os.getenv('LOCAL_MODEL_N_GPU_LAYERS', '0'))

        if not os.path.exists(model_path):
            logger.error("Model file not found", model_path=model_path)
            return False

        logger.info("Loading local LLM",
                   model_path=model_path,
                   n_ctx=n_ctx,
                   n_gpu_layers=n_gpu_layers)

        # Import llama-cpp-python here to avoid import issues if not installed
        try:
            from llama_cpp import Llama

            # Load model
            model = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                verbose=os.getenv('LOG_LEVEL') == 'DEBUG',
                use_mmap=True,
                use_mlock=False,
                embedding=False,
                n_threads=os.cpu_count()
            )

            # Get model info
            model_info = {
                "path": model_path,
                "n_ctx": n_ctx,
                "n_gpu_layers": n_gpu_layers,
                "model_size": os.path.getsize(model_path) / (1024 * 1024),  # MB
                "file_name": os.path.basename(model_path)
            }

            logger.info("Model loaded successfully",
                      model_info=model_info)
            return True

        except ImportError as e:
            logger.error("Failed to import llama-cpp-python", error=str(e))
            return False

    except Exception as e:
        logger.error("Failed to load model", error=str(e))
        return False


def generate_response(request: ChatCompletionRequest) -> Dict[str, Any]:
    """Generate response using the loaded model."""
    try:
        # Format prompt from messages
        prompt = format_prompt(request.messages)

        # Set generation parameters
        generation_params = {
            'max_tokens': request.max_tokens or 2048,
            'temperature': request.temperature or 0.7,
            'stop': ['<|im_end|>', '<|im_start|>', '<|file_sep|>'],
            'echo': False,
            'stream': False
        }

        # Generate response
        start_time = time.time()
        output = model(prompt, **generation_params)
        generation_time = time.time() - start_time

        # Extract response text
        if 'choices' in output:
            response_text = output['choices'][0]['text'].strip()
        else:
            response_text = output['text'].strip()

        # Calculate token usage (approximate)
        prompt_tokens = len(prompt.split())
        completion_tokens = len(response_text.split())
        total_tokens = prompt_tokens + completion_tokens

        # Update stats
        inference_stats["total_requests"] += 1
        inference_stats["successful_requests"] += 1
        inference_stats["total_tokens"] += total_tokens

        logger.info("Generated response",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    generation_time=generation_time,
                    user=request.user)

        return {
            "response_text": response_text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "generation_time": generation_time
        }

    except Exception as e:
        inference_stats["failed_requests"] += 1
        logger.error("Generation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}"
        )


def format_prompt(messages: List[ChatMessage]) -> str:
    """Format messages into a single prompt for the model."""
    # Simple chat format - you can customize based on your model
    formatted_parts = []

    for message in messages:
        if message.role == "system":
            formatted_parts.append(f"System: {message.content}")
        elif message.role == "user":
            formatted_parts.append(f"Human: {message.content}")
        elif message.role == "assistant":
            formatted_parts.append(f"Assistant: {message.content}")

    formatted_parts.append("Assistant: ")
    return "\n".join(formatted_parts)


@app.on_event("startup")
async def startup_event():
    """Initialize the service."""
    logger.info("Starting inference service")

    # Create model directory if it doesn't exist
    Path("/app/models").mkdir(parents=True, exist_ok=True)

    # Load the model
    if not load_model():
        logger.error("Failed to load model on startup")
        # Continue running - model can be loaded later via reload endpoint
    else:
        logger.info("Inference service ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down inference service")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    import psutil

    uptime = time.time() - inference_stats["start_time"]
    memory_usage = psutil.Process().memory_info().rss / (1024 * 1024)  # MB

    return HealthResponse(
        status="healthy" if model is not None else "unhealthy",
        model_loaded=model is not None,
        uptime_seconds=uptime,
        requests_processed=inference_stats["total_requests"],
        memory_usage_mb=memory_usage
    )


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint."""
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded. Please check the service status."
        )

    try:
        # Generate response
        result = generate_response(request)

        # Create OpenAI-compatible response
        response = ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model or "local-model",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=result["response_text"]),
                    finish_reason="stop"
                )
            ],
            usage=UsageInfo(
                prompt_tokens=result["prompt_tokens"],
                completion_tokens=result["completion_tokens"],
                total_tokens=result["total_tokens"]
            )
        )

        return response

    except Exception as e:
        logger.error("Chat completion failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat completion failed: {str(e)}"
        )


@app.post("/v1/models")
async def list_models():
    """List available models."""
    if model is None:
        return {"data": []}

    return {
        "data": [
            {
                "id": "local-model",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "local",
                **model_info
            }
        ]
    }


@app.post("/reload_model")
async def reload_model():
    """Reload the model."""
    logger.info("Reloading model...")

    # Cleanup existing model
    global model
    if model is not None:
        del model
        model = None

    # Load new model
    success = load_model()

    return {
        "status": "success" if success else "failed",
        "model_info": model_info if success else None
    }


@app.get("/stats")
async def get_stats():
    """Get inference statistics."""
    return {
        **inference_stats,
        "uptime_seconds": time.time() - inference_stats["start_time"],
        "model_info": model_info
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=1,
        log_level="info"
    )