# app/retry_utils.py
"""
Retry utilities for the Onestream RAG application.
Provides decorators and functions for retrying operations with exponential backoff.
"""

import time
import random
import logging
from typing import Callable, Any, Type, Tuple, Optional
from functools import wraps

class RetryError(Exception):
    """Custom exception for retry failures."""
    pass

def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        jitter: Whether to add random jitter to delay
        exceptions: Tuple of exceptions to catch and retry on
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    # If this was the last attempt, re-raise
                    if attempt == max_attempts - 1:
                        raise RetryError(f"Function failed after {max_attempts} attempts: {str(e)}") from e
                    
                    # Calculate delay
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    
                    # Add jitter if requested
                    if jitter:
                        delay *= (0.5 + random.random() * 0.5)
                    
                    # Log retry attempt
                    logging.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    # Wait before retry
                    time.sleep(delay)
            
            # This should never be reached due to the re-raise above
            raise RetryError(f"Function failed after {max_attempts} attempts: {last_exception}")
        
        return wrapper
    return decorator

def retry_with_fallback(
    fallback_func: Callable,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for retrying functions with a fallback function.
    
    Args:
        fallback_func: Function to call if all retries fail
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        jitter: Whether to add random jitter to delay
        exceptions: Tuple of exceptions to catch and retry on
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    # If this was the last attempt, try fallback
                    if attempt == max_attempts - 1:
                        try:
                            logging.warning(
                                f"All retry attempts failed for {func.__name__}: {str(e)}. "
                                f"Trying fallback function..."
                            )
                            return fallback_func(*args, **kwargs)
                        except Exception as fallback_error:
                            raise RetryError(
                                f"Both function and fallback failed. "
                                f"Original error: {str(e)}. "
                                f"Fallback error: {str(fallback_error)}"
                            ) from fallback_error
                    
                    # Calculate delay
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    
                    # Add jitter if requested
                    if jitter:
                        delay *= (0.5 + random.random() * 0.5)
                    
                    # Log retry attempt
                    logging.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    # Wait before retry
                    time.sleep(delay)
            
            # This should never be reached
            raise RetryError(f"Function failed after {max_attempts} attempts: {last_exception}")
        
        return wrapper
    return decorator
