# app/enhanced_logger.py
"""
Enhanced logging module for the Onestream RAG application.
Provides structured logging with correlation IDs, request tracking,
and comprehensive context information.
"""

import logging
import os
import json
import uuid
import time
import threading
from typing import Optional, Dict, Any
from datetime import datetime
from contextlib import contextmanager
from functools import wraps


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': threading.current_thread().name,
            'process': os.getpid()
        }

        # Add extra fields if they exist
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'session_id'):
            log_entry['session_id'] = record.session_id
        if hasattr(record, 'duration_ms'):
            log_entry['duration_ms'] = record.duration_ms
        if hasattr(record, 'component'):
            log_entry['component'] = record.component
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        if hasattr(record, 'metadata'):
            log_entry['metadata'] = record.metadata

        return json.dumps(log_entry)


class EnhancedLogger:
    """Enhanced application logger with structured logging and correlation tracking."""

    def __init__(self, name: str = "onestream_rag", log_file: str = "app.log"):
        """
        Initialize enhanced application logger.

        Args:
            name: Logger name
            log_file: Log file path
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Prevent adding multiple handlers if logger already exists
        if not self.logger.handlers:
            # Create formatters
            detailed_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            simple_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            json_formatter = JsonFormatter()

            # File handler with detailed information
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(detailed_formatter)

            # JSON structured log handler
            json_handler = logging.FileHandler(log_file.replace('.log', '_structured.log'))
            json_handler.setLevel(logging.INFO)
            json_handler.setFormatter(json_formatter)

            # Console handler with simple format
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.WARNING)
            console_handler.setFormatter(simple_formatter)

            # Add handlers to logger
            self.logger.addHandler(file_handler)
            self.logger.addHandler(json_handler)
            self.logger.addHandler(console_handler)

    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with additional context."""
        extra = {}

        # Add context fields
        if 'request_id' in kwargs:
            extra['request_id'] = kwargs.pop('request_id')
        if 'user_id' in kwargs:
            extra['user_id'] = kwargs.pop('user_id')
        if 'session_id' in kwargs:
            extra['session_id'] = kwargs.pop('session_id')
        if 'component' in kwargs:
            extra['component'] = kwargs.pop('component')
        if 'operation' in kwargs:
            extra['operation'] = kwargs.pop('operation')
        if 'duration_ms' in kwargs:
            extra['duration_ms'] = kwargs.pop('duration_ms')
        if 'metadata' in kwargs:
            extra['metadata'] = kwargs.pop('metadata')

        # Add any remaining kwargs to metadata
        if kwargs:
            if 'metadata' not in extra:
                extra['metadata'] = {}
            extra['metadata'].update(kwargs)

        self.logger.log(level, message, extra=extra)

    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self._log_with_context(logging.ERROR, message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, **kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with traceback and context."""
        self._log_with_context(logging.ERROR, message, exc_info=True, **kwargs)


# Thread-local storage for request context
_request_context = threading.local()


@contextmanager
def request_context(request_id: str = None, user_id: str = None, session_id: str = None, **kwargs):
    """
    Context manager for request-level logging.

    Args:
        request_id: Unique request identifier
        user_id: User identifier
        session_id: Session identifier
        **kwargs: Additional context
    """
    # Store context in thread-local storage
    old_context = getattr(_request_context, 'context', {})

    new_context = {
        'request_id': request_id or str(uuid.uuid4()),
        'user_id': user_id,
        'session_id': session_id,
        **kwargs
    }

    _request_context.context = new_context

    logger = EnhancedLogger()
    logger.info("Request started", **new_context)

    start_time = time.time()
    try:
        yield logger
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.exception(
            "Request failed",
            duration_ms=duration_ms,
            error_type=type(e).__name__,
            **new_context
        )
        raise
    finally:
        duration_ms = (time.time() - start_time) * 1000
        logger.info("Request completed", duration_ms=duration_ms, **new_context)
        _request_context.context = old_context


def logged_operation(operation_name: str = None, component: str = None, log_args: bool = False):
    """
    Decorator for logging function operations.

    Args:
        operation_name: Name of the operation
        component: Component name
        log_args: Whether to log function arguments
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = EnhancedLogger()
            context = getattr(_request_context, 'context', {})

            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            comp = component or func.__module__

            log_data = {
                'operation': op_name,
                'component': comp,
                'function': func.__name__
            }

            if log_args:
                # Sanitize args for logging (avoid sensitive data)
                safe_args = [str(arg)[:100] for arg in args[:3]]  # Limit args and length
                safe_kwargs = {k: str(v)[:100] for k, v in list(kwargs.items())[:3]}
                log_data.update({
                    'args_count': len(args),
                    'kwargs_count': len(kwargs),
                    'sample_args': safe_args,
                    'sample_kwargs': safe_kwargs
                })

            start_time = time.time()
            logger.info(f"Starting operation: {op_name}", **log_data, **context)

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"Completed operation: {op_name}",
                    duration_ms=duration_ms,
                    success=True,
                    **log_data,
                    **context
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.exception(
                    f"Failed operation: {op_name}",
                    duration_ms=duration_ms,
                    success=False,
                    error_type=type(e).__name__,
                    **log_data,
                    **context
                )
                raise

        return wrapper
    return decorator


def get_current_context() -> Dict[str, Any]:
    """Get current request context."""
    return getattr(_request_context, 'context', {})


# Create default logger instance
default_logger = EnhancedLogger()

# Convenience functions
def info(message: str, **kwargs):
    context = get_current_context()
    default_logger.info(message, **{**context, **kwargs})

def warning(message: str, **kwargs):
    context = get_current_context()
    default_logger.warning(message, **{**context, **kwargs})

def error(message: str, **kwargs):
    context = get_current_context()
    default_logger.error(message, **{**context, **kwargs})

def debug(message: str, **kwargs):
    context = get_current_context()
    default_logger.debug(message, **{**context, **kwargs})

def exception(message: str, **kwargs):
    context = get_current_context()
    default_logger.exception(message, **{**context, **kwargs})