# app/input_validator.py
"""
Input validation module for the Onestream RAG application.
Provides functions to validate and sanitize user inputs.
"""

import re
from typing import Optional, Tuple
from pathlib import Path

class InputValidationError(Exception):
    """Custom exception for input validation errors."""
    pass

class InputValidator:
    """Input validator with sanitization capabilities."""
    
    # Maximum lengths for various inputs
    MAX_QUESTION_LENGTH = 1000
    MAX_PATH_LENGTH = 255
    MAX_CHUNK_SIZE = 10000
    MAX_CHUNK_OVERLAP = 5000
    
    # Allowed characters patterns
    SAFE_PATH_PATTERN = re.compile(r'^[a-zA-Z0-9_.\-/]+$')
    SAFE_TEXT_PATTERN = re.compile(r'^[a-zA-Z0-9\s\.,!?;:\-_\'\"()\[\]{}@#$%^&*+=<>\\/]+$')
    
    @classmethod
    def validate_question(cls, question: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a question input.
        
        Args:
            question: Question string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not question or not question.strip():
            return False, "Question cannot be empty"
            
        if len(question) > cls.MAX_QUESTION_LENGTH:
            return False, f"Question too long (max {cls.MAX_QUESTION_LENGTH} characters)"
            
        # Basic sanitization - remove potentially dangerous characters
        sanitized = re.sub(r'[<>&]', '', question)
        if sanitized != question:
            return False, "Question contains invalid characters"
            
        return True, None
    
    @classmethod
    def validate_path(cls, path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a file path input.
        
        Args:
            path: Path string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not path or not path.strip():
            return False, "Path cannot be empty"
            
        if len(path) > cls.MAX_PATH_LENGTH:
            return False, f"Path too long (max {cls.MAX_PATH_LENGTH} characters)"
            
        # Check for absolute paths (security risk)
        if Path(path).is_absolute():
            return False, "Absolute paths are not allowed"
            
        # Check for directory traversal attempts
        if ".." in path:
            return False, "Directory traversal not allowed"
            
        # Check for safe characters
        if not cls.SAFE_PATH_PATTERN.match(path):
            return False, "Path contains invalid characters"
            
        return True, None
    
    @classmethod
    def validate_chunk_params(cls, chunk_size: int, chunk_overlap: int) -> Tuple[bool, Optional[str]]:
        """
        Validate chunking parameters.
        
        Args:
            chunk_size: Chunk size to validate
            chunk_overlap: Chunk overlap to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(chunk_size, int) or chunk_size <= 0:
            return False, "Chunk size must be a positive integer"
            
        if chunk_size > cls.MAX_CHUNK_SIZE:
            return False, f"Chunk size too large (max {cls.MAX_CHUNK_SIZE})"
            
        if not isinstance(chunk_overlap, int) or chunk_overlap < 0:
            return False, "Chunk overlap must be a non-negative integer"
            
        if chunk_overlap > cls.MAX_CHUNK_OVERLAP:
            return False, f"Chunk overlap too large (max {cls.MAX_CHUNK_OVERLAP})"
            
        if chunk_overlap >= chunk_size:
            return False, "Chunk overlap must be less than chunk size"
            
        return True, None
    
    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """
        Sanitize text input by removing potentially dangerous characters.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        if not text:
            return ""
            
        # Remove HTML/XML tags
        text = re.sub(r'<[^>]*>', '', text)
        
        # Remove potentially dangerous characters while preserving most text
        text = re.sub(r'[<>&]', '', text)
        
        return text.strip()
