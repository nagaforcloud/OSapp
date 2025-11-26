# app/logger.py
"""
Enhanced logging module for the Onestream RAG application.
Provides structured logging with different levels and contextual information.
"""

import logging
import os
import json
import uuid
import time
from typing import Optional, Dict, Any
from datetime import datetime
from contextlib import contextmanager
from functools import wraps

class AppLogger:
    """Enhanced application logger with structured logging capabilities."""
    
    def __init__(self, name: str = "onestream_rag", log_file: str = "app.log"):
        """
        Initialize the application logger.
        
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
            
            # File handler with detailed information
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(detailed_formatter)
            
            # Console handler with simple format
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.WARNING)  # Only warnings and above to console
            console_handler.setFormatter(simple_formatter)
            
            # Add handlers to logger
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def info(self, message: str, user_id: Optional[str] = None, session_id: Optional[str] = None):
        """Log info message with optional user and session context."""
        context = self._build_context(user_id, session_id)
        self.logger.info(f"{context}{message}")
    
    def warning(self, message: str, user_id: Optional[str] = None, session_id: Optional[str] = None):
        """Log warning message with optional user and session context."""
        context = self._build_context(user_id, session_id)
        self.logger.warning(f"{context}{message}")
    
    def error(self, message: str, user_id: Optional[str] = None, session_id: Optional[str] = None):
        """Log error message with optional user and session context."""
        context = self._build_context(user_id, session_id)
        self.logger.error(f"{context}{message}")
    
    def debug(self, message: str, user_id: Optional[str] = None, session_id: Optional[str] = None):
        """Log debug message with optional user and session context."""
        context = self._build_context(user_id, session_id)
        self.logger.debug(f"{context}{message}")
    
    def exception(self, message: str, user_id: Optional[str] = None, session_id: Optional[str] = None):
        """Log exception with traceback and optional user and session context."""
        context = self._build_context(user_id, session_id)
        self.logger.exception(f"{context}{message}")
    
    def _build_context(self, user_id: Optional[str], session_id: Optional[str]) -> str:
        """Build context string for log messages."""
        context_parts = []
        if user_id:
            context_parts.append(f"user:{user_id}")
        if session_id:
            context_parts.append(f"session:{session_id[:8]}")
        
        if context_parts:
            return f"[{', '.join(context_parts)}] - "
        return ""

# Create a default logger instance
default_logger = AppLogger()

# Convenience functions that match the standard logging module interface
def info(message: str, user_id: Optional[str] = None, session_id: Optional[str] = None):
    default_logger.info(message, user_id, session_id)

def warning(message: str, user_id: Optional[str] = None, session_id: Optional[str] = None):
    default_logger.warning(message, user_id, session_id)

def error(message: str, user_id: Optional[str] = None, session_id: Optional[str] = None):
    default_logger.error(message, user_id, session_id)

def debug(message: str, user_id: Optional[str] = None, session_id: Optional[str] = None):
    default_logger.debug(message, user_id, session_id)

def exception(message: str, user_id: Optional[str] = None, session_id: Optional[str] = None):
    default_logger.exception(message, user_id, session_id)
