# app/resource_manager.py
"""
Resource manager for the Onestream RAG application.
Handles proper cleanup and context management for various resources.
"""

import os
import shutil
import tempfile
from contextlib import contextmanager
from typing import Generator, Optional, Any
from pathlib import Path

class ResourceManagerError(Exception):
    """Custom exception for resource manager errors."""
    pass

class ResourceManager:
    """Resource manager for handling cleanup and context management."""
    
    def __init__(self):
        """Initialize the resource manager."""
        self.resources = []
    
    def register_resource(self, resource: Any, cleanup_func: callable):
        """
        Register a resource with its cleanup function.
        
        Args:
            resource: Resource to register
            cleanup_func: Function to cleanup the resource
        """
        self.resources.append((resource, cleanup_func))
    
    def cleanup(self):
        """Cleanup all registered resources."""
        errors = []
        for resource, cleanup_func in self.resources:
            try:
                cleanup_func(resource)
            except Exception as e:
                errors.append(f"Failed to cleanup {resource}: {str(e)}")
        
        self.resources.clear()
        
        if errors:
            raise ResourceManagerError(f"Errors during cleanup: {'; '.join(errors)}")

@contextmanager
def temporary_directory() -> Generator[str, None, None]:
    """
    Context manager for creating and cleaning up temporary directories.
    
    Yields:
        Path to temporary directory
    """
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                raise ResourceManagerError(f"Failed to remove temporary directory: {e}")

@contextmanager
def managed_file(filepath: str, mode: str = 'r') -> Generator[Any, None, None]:
    """
    Context manager for file handling with automatic cleanup.
    
    Args:
        filepath: Path to file
        mode: File open mode
        
    Yields:
        File object
    """
    file_obj = None
    try:
        file_obj = open(filepath, mode)
        yield file_obj
    finally:
        if file_obj:
            try:
                file_obj.close()
            except Exception:
                pass  # Ignore close errors

class VectorStoreContext:
    """Context manager for vector store operations."""
    
    def __init__(self, vector_manager: Any):
        """
        Initialize vector store context.
        
        Args:
            vector_manager: Vector store manager instance
        """
        self.vector_manager = vector_manager
        self.original_client = None
    
    def __enter__(self):
        """Enter context."""
        # Store original client if exists
        self.original_client = getattr(self.vector_manager, 'client', None)
        return self.vector_manager
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and cleanup."""
        # Cleanup client if it was created
        if hasattr(self.vector_manager, 'client') and self.vector_manager.client:
            try:
                # Qdrant client doesn't have explicit close method in local mode
                # but we set it to None to help with garbage collection
                self.vector_manager.client = None
            except Exception:
                pass  # Ignore cleanup errors

def safe_remove(path: str) -> bool:
    """
    Safely remove a file or directory.
    
    Args:
        path: Path to remove
        
    Returns:
        Whether removal was successful
    """
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        return True
    except Exception as e:
        raise ResourceManagerError(f"Failed to remove {path}: {e}")
