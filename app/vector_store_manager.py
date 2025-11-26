# app/vector_store_manager.py
"""
Vector store manager for the Onestream RAG application.
Handles Qdrant vector store initialization, creation, and management with robust error handling.
"""

import os
from typing import List, Optional
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain_community.vectorstores import Qdrant as QdrantVectorStore
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

class VectorStoreError(Exception):
    """Custom exception for vector store errors."""
    pass

class VectorStoreManager:
    """Enhanced vector store manager with robust error handling."""
    
    def __init__(self, qdrant_path: str, collection_name: str, vector_size: int = 1024):
        """
        Initialize the vector store manager.
        
        Args:
            qdrant_path: Path to Qdrant storage
            collection_name: Name of the collection
            vector_size: Size of vectors
        """
        self.qdrant_path = qdrant_path
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.client: Optional[QdrantClient] = None
    
    def initialize_client(self) -> bool:
        """
        Initialize the Qdrant client.
        
        Returns:
            Whether initialization was successful
        """
        try:
            # Ensure the path exists
            os.makedirs(self.qdrant_path, exist_ok=True)
            
            # Initialize client
            self.client = QdrantClient(path=self.qdrant_path)
            return True
        except Exception as e:
            # Add more detailed error information
            error_details = f"Failed to initialize Qdrant client: {str(e)}"
            # Check if path exists and is accessible
            if not os.path.exists(self.qdrant_path):
                error_details += f" | Qdrant path does not exist: {self.qdrant_path}"
            elif not os.access(self.qdrant_path, os.W_OK):
                error_details += f" | Qdrant path is not writable: {self.qdrant_path}"
            
            raise VectorStoreError(error_details)
    
    def collection_exists(self) -> bool:
        """
        Check if the collection exists.
        
        Returns:
            Whether collection exists
        """
        if not self.client:
            raise VectorStoreError("Client not initialized")
            
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return True
        except Exception as e:
            # Log the specific error for debugging (this won't raise an exception)
            # This is expected behavior when the collection doesn't exist
            return False
    
    def collection_has_documents(self) -> bool:
        """
        Check if the collection exists and has documents.
        
        Returns:
            Whether collection exists and has documents
        """
        if not self.client:
            raise VectorStoreError("Client not initialized")
            
        try:
            # Initialize client if needed
            if not self.client:
                self.initialize_client()
                
            collection_info = self.client.get_collection(self.collection_name)
            # Check if the collection has points (documents)
            return collection_info.points_count > 0 if collection_info.points_count is not None else False
        except Exception as e:
            # If we can't get collection info, assume it doesn't have documents
            return False
    
    def create_collection(self) -> bool:
        """
        Create the collection if it doesn't exist.
        
        Returns:
            Whether creation was successful
        """
        if not self.client:
            raise VectorStoreError("Client not initialized")
            
        try:
            if not self.collection_exists():
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
            return True
        except Exception as e:
            # Add more detailed error information
            error_details = f"Failed to create collection '{self.collection_name}': {str(e)}"
            # Check if this is a permission error
            if "permission" in str(e).lower():
                error_details += " | Check if the Qdrant path is writable"
            # Check if this is a configuration error
            elif "config" in str(e).lower():
                error_details += " | Check vector size and distance configuration"
                
            raise VectorStoreError(error_details)
    
    def get_vectorstore(self, embeddings: Embeddings) -> QdrantVectorStore:
        """
        Get or create a vector store instance.
        
        Args:
            embeddings: Embeddings model to use
            
        Returns:
            QdrantVectorStore instance
        """
        try:
            # Initialize client if needed
            if not self.client:
                self.initialize_client()
            
            # Create collection if needed
            self.create_collection()
            
            # Create vector store
            return QdrantVectorStore(
                client=self.client,
                collection_name=self.collection_name,
                embeddings=embeddings,
            )
        except Exception as e:
            # Add more detailed error information
            error_details = f"Failed to create vector store: {str(e)}"
            # Check if client is initialized
            if not self.client:
                error_details += " | Qdrant client is not initialized"
            # Check if collection name is valid
            if not self.collection_name:
                error_details += " | Collection name is empty"
            # Check if embeddings are valid
            if not embeddings:
                error_details += " | Embeddings model is not valid"
                
            raise VectorStoreError(error_details)
    
    def add_documents(self, vectorstore: QdrantVectorStore, documents: List[Document]) -> bool:
        """
        Add documents to the vector store.
        
        Args:
            vectorstore: Vector store instance
            documents: Documents to add
            
        Returns:
            Whether operation was successful
        """
        try:
            if not documents:
                raise VectorStoreError("No documents to add")
                
            vectorstore.add_documents(documents)
            return True
        except Exception as e:
            # Add more detailed error information
            error_msg = str(e)
            detailed_error = f"Failed to add documents to vector store: {error_msg}"
            
            # Check if this is a specific authentication error
            if "401" in error_msg or "Unauthorized" in error_msg:
                detailed_error = (
                    "Failed to add documents to vector store: API authentication error. "
                    "Please check your API key in the .env file. "
                    "For DeepSeek, set DEEPSEEK_API_KEY. For Mistral, set MISTRAL_API_KEY."
                )
            elif "RetryError" in error_msg and "HTTPStatusError" in error_msg:
                detailed_error = (
                    "Failed to add documents to vector store: Connection error with the AI service. "
                    "Please check your API key and internet connection."
                )
            elif "404" in error_msg or "Not Found" in error_msg:
                detailed_error = (
                    "Failed to add documents to vector store: Resource not found. "
                    "Please check your configuration and ensure the service is accessible. "
                    "This could be due to: 1) Incorrect Qdrant path, 2) Corrupted database, "
                    "3) Missing collection, 4) Incorrect embedding model configuration."
                )
            elif "llama_decode returned -1" in error_msg:
                detailed_error = (
                    "Failed to add documents to vector store: Embedding model error. "
                    "This typically happens when there's a mismatch between the embedding model and the expected format. "
                    "Please ensure you're using a compatible embedding model (BGE or similar) and that it's properly configured."
                )
            
            raise VectorStoreError(detailed_error)
    
    def search(self, vectorstore: QdrantVectorStore, query: str, k: int = 4) -> List[Document]:
        """
        Search for similar documents.
        
        Args:
            vectorstore: Vector store instance
            query: Query string
            k: Number of results to return
            
        Returns:
            List of similar documents
        """
        try:
            return vectorstore.similarity_search(query, k=k)
        except Exception as e:
            raise VectorStoreError(f"Failed to search vector store: {str(e)}")
