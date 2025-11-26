#!/usr/bin/env python3
"""
Test script to verify Qdrant database initialization.
"""

import os
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent / "app"))

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

def test_qdrant_initialization():
    """Test Qdrant database initialization."""
    qdrant_path = "vector_db"
    collection_name = "test_collection"
    vector_size = 384
    
    print(f"Testing Qdrant initialization with path: {qdrant_path}")
    
    # Ensure the path exists
    os.makedirs(qdrant_path, exist_ok=True)
    print(f"Created directory: {qdrant_path}")
    
    try:
        # Initialize client
        print("Initializing Qdrant client...")
        client = QdrantClient(path=qdrant_path)
        print("Qdrant client initialized successfully")
        
        # Try to create a collection
        print(f"Creating collection: {collection_name}")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        )
        print(f"Collection '{collection_name}' created successfully")
        
        # Try to get the collection
        print(f"Getting collection: {collection_name}")
        collection_info = client.get_collection(collection_name)
        print(f"Collection info: {collection_info}")
        
        # Clean up - delete the collection
        print(f"Deleting collection: {collection_name}")
        client.delete_collection(collection_name)
        print(f"Collection '{collection_name}' deleted successfully")
        
        print("Qdrant initialization test passed!")
        return True
        
    except Exception as e:
        print(f"Qdrant initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_qdrant_initialization()