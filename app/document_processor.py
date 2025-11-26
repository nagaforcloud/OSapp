# app/document_processor.py
"""
Enhanced document processing module for the Onestream RAG application.
Handles loading, parsing, and chunking of various document types with robust error handling.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Supported document types
SUPPORTED_TYPES = [".pdf", ".txt", ".md"]

@dataclass
class DocumentProcessingResult:
    """Result of document processing operation."""
    success: bool
    documents: List[Document]
    errors: List[str]
    loaded_files: List[str]

class DocumentProcessorError(Exception):
    """Custom exception for document processing errors."""
    pass

class DocumentProcessor:
    """Enhanced document processor with robust error handling and validation."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the document processor.
        
        Args:
            chunk_size: Size of document chunks
            chunk_overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
    def validate_path(self, path: str) -> bool:
        """
        Validate that a path exists and is accessible.
        
        Args:
            path: Path to validate
            
        Returns:
            Whether path is valid
        """
        if not os.path.exists(path):
            return False
        if not os.path.isdir(path):
            return False
        return True
    
    def get_supported_files(self, path: str) -> List[str]:
        """
        Get list of supported files in a directory.
        
        Args:
            path: Directory path
            
        Returns:
            List of supported file paths
        """
        if not self.validate_path(path):
            return []
            
        files = []
        for file_path in Path(path).iterdir():
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_TYPES:
                files.append(str(file_path))
        return files
    
    def load_document(self, file_path: str) -> Optional[List[Document]]:
        """
        Load a single document with appropriate loader.
        
        Args:
            file_path: Path to document file
            
        Returns:
            List of loaded documents or None if failed
        """
        try:
            ext = Path(file_path).suffix.lower()
            
            if ext == ".pdf":
                loader = PyPDFLoader(file_path)
            elif ext == ".txt":
                loader = TextLoader(file_path, encoding="utf-8")
            elif ext == ".md":
                loader = UnstructuredMarkdownLoader(file_path)
            else:
                raise DocumentProcessorError(f"Unsupported file type: {ext}")
                
            return loader.load()
        except Exception as e:
            raise DocumentProcessorError(f"Failed to load {file_path}: {str(e)}")
    
    def process_documents(self, path: str) -> DocumentProcessingResult:
        """
        Process all supported documents in a directory.
        
        Args:
            path: Directory containing documents
            
        Returns:
            Processing result with documents and any errors
        """
        # Validate path
        if not self.validate_path(path):
            return DocumentProcessingResult(
                success=False,
                documents=[],
                errors=[f"Document directory not found or inaccessible: {path}"],
                loaded_files=[]
            )
        
        # Get supported files
        files = self.get_supported_files(path)
        if not files:
            return DocumentProcessingResult(
                success=False,
                documents=[],
                errors=["No supported files found (.pdf, .txt, .md)"],
                loaded_files=[]
            )
        
        # Process each file
        all_documents = []
        errors = []
        loaded_files = []
        
        for file_path in files:
            try:
                documents = self.load_document(file_path)
                if documents:
                    all_documents.extend(documents)
                    loaded_files.append(Path(file_path).name)
            except DocumentProcessorError as e:
                errors.append(str(e))
            except Exception as e:
                errors.append(f"Unexpected error loading {file_path}: {str(e)}")
        
        # Check if we have any documents
        if not all_documents:
            if not errors:
                errors.append("No documents could be loaded")
            return DocumentProcessingResult(
                success=False,
                documents=[],
                errors=errors,
                loaded_files=loaded_files
            )
        
        return DocumentProcessingResult(
            success=True,
            documents=all_documents,
            errors=errors,
            loaded_files=loaded_files
        )
    
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks.
        
        Args:
            documents: List of documents to chunk
            
        Returns:
            List of chunked documents
        """
        try:
            return self.splitter.split_documents(documents)
        except Exception as e:
            raise DocumentProcessorError(f"Failed to chunk documents: {str(e)}")
