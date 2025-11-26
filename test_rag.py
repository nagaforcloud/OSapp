#!/usr/bin/env python3
"""
Corrected RAG test script for Onestream documentation.
This script tests the RAG functionality directly without web server overhead.
"""

import sys
import os
from pathlib import Path

# Add the app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

# Import required modules at module level
try:
    from app.config import *
    from app.vector_store_manager import VectorStoreManager, VectorStoreError
    from app.local_llm_adapter import LocalLLMAdapter, LocalLLMError
    from app.config import RAG_PROMPT
    from langchain_core.prompts import PromptTemplate
    from sentence_transformers import SentenceTransformer
except Exception as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def test_rag_functionality():
    """Test RAG functionality directly"""
    try:
        print("🧪 Testing RAG functionality...")
        
        print("✅ Modules imported successfully")
        
        # Test 1: Check if local models exist
        print("\n🔍 Testing local model paths...")
        adapter = LocalLLMAdapter()
        
        if adapter.validate_model_path(LOCAL_LLM_MODEL_PATH):
            print(f"✅ LLM model found: {LOCAL_LLM_MODEL_PATH}")
        else:
            print(f"❌ LLM model not found: {LOCAL_LLM_MODEL_PATH}")
            return False
            
        if adapter.validate_model_path(LOCAL_EMBEDDING_MODEL_PATH):
            print(f"✅ Embedding model found: {LOCAL_EMBEDDING_MODEL_PATH}")
        else:
            print(f"❌ Embedding model not found: {LOCAL_EMBEDDING_MODEL_PATH}")
            return False
        
        # Test 2: Initialize embeddings
        print("\n🧠 Initializing embeddings...")
        try:
            embeddings = adapter.load_local_embeddings(
                model_path=LOCAL_EMBEDDING_MODEL_PATH,
                n_ctx=LOCAL_LLM_CONTEXT_SIZE
            )
            print("✅ Embeddings initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize embeddings: {e}")
            return False
        
        # Test 3: Check vector store
        print("\n📂 Checking vector store...")
        try:
            vector_manager = VectorStoreManager(QDRANT_PATH, DEFAULT_COLLECTION, VECTOR_SIZE)
            vector_manager.initialize_client()
            
            if vector_manager.collection_exists():
                print("✅ Vector store collection exists")
                if vector_manager.collection_has_documents():
                    print("✅ Vector store has documents")
                    vectorstore = vector_manager.get_vectorstore(embeddings)
                    print("✅ Vector store loaded successfully")
                else:
                    print("❌ Vector store collection exists but has no documents")
                    return False
            else:
                print("❌ Vector store collection does not exist")
                return False
        except VectorStoreError as e:
            print(f"❌ Vector store error: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error with vector store: {e}")
            return False
        
        # Test 4: Simple retrieval test
        print("\n🔍 Testing document retrieval...")
        try:
            # Search for a simple query
            results = vectorstore.similarity_search("cube view", k=2)
            if results:
                print(f"✅ Retrieved {len(results)} documents")
                print(f"📝 Sample context: {results[0].page_content[:200]}...")
            else:
                print("❌ No documents retrieved")
                return False
        except Exception as e:
            print(f"❌ Retrieval failed: {e}")
            return False
        
        # Test 5: Test LLM loading (simple test)
        print("\n🤖 Testing LLM loading...")
        try:
            llm = adapter.load_local_llm(
                model_path=LOCAL_LLM_MODEL_PATH,
                temperature=0.7,
                max_tokens=500,  # Smaller for testing
                n_ctx=LOCAL_LLM_CONTEXT_SIZE,
                verbose=False
            )
            print("✅ LLM loaded successfully")
        except LocalLLMError as e:
            print(f"❌ Failed to load LLM: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error loading LLM: {e}")
            return False
        
        # Test 6: Corrected generation test
        print("\n💬 Testing simple generation...")
        try:
            # Retrieve context for a test query
            test_query = "What is a cube view in Onestream?"
            context_docs = vectorstore.similarity_search(test_query, k=TOP_K)
            context_text = "\n\n".join([doc.page_content for doc in context_docs if hasattr(doc, "page_content")])
            
            # Create prompt using the RAG prompt template
            prompt = PromptTemplate.from_template(RAG_PROMPT)
            formatted_prompt = prompt.invoke({"question": test_query, "context": context_text})
            
            # Generate response (invoke with the formatted prompt string)
            response = llm.invoke(formatted_prompt.to_string())
            
            if response:
                print("✅ Generation successful")
                if hasattr(response, 'content'):
                    print(f"📝 Sample response: {response.content[:200]}...")
                else:
                    print(f"📝 Sample response: {str(response)[:200]}...")
            else:
                print("❌ No response generated")
                return False
        except Exception as e:
            print(f"❌ Generation failed: {e}")
            return False
        
        print("\n🎉 All RAG functionality tests passed!")
        print("\n🚀 You can now run the Streamlit app with:")
        print("   streamlit run app/streamlit_app.py")
        return True
        
    except Exception as e:
        print(f"💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_rag_functionality()
    if success:
        print("\n✅ RAG system is ready!")
        sys.exit(0)
    else:
        print("\n❌ RAG system has issues!")
        sys.exit(1)