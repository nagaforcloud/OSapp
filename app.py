from flask import Flask, render_template, request, jsonify, session
import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

# Add the app directory to path to allow imports
sys.path.append(str(Path(__file__).parent / "app"))

# Import our RAG modules
try:
    from app.config import *
    from app.document_processor import DocumentProcessor, DocumentProcessingResult
    from app.input_validator import InputValidator
    from app.vector_store_manager import VectorStoreManager, VectorStoreError
    from app.local_llm_adapter import LocalLLMAdapter, LocalLLMError
    from langchain_core.prompts import PromptTemplate
    from langchain_core.documents import Document
except Exception as e:
    print(f"Failed to import modules: {e}")

app = Flask(__name__)
app.secret_key = 'onestream-rag-secret-key'

# In-memory storage for chat history (in production, use a database)
chat_storage = {}

class RAGSystem:
    """RAG System that integrates with local LLM and vector database"""
    
    def __init__(self):
        self.llm = None
        self.embeddings = None
        self.vectorstore = None
        self.initialized = False
        
    def initialize(self):
        """Initialize the RAG system with LLM and vector store"""
        if self.initialized:
            return True
            
        try:
            # Load LLM and embeddings
            adapter = LocalLLMAdapter()
            
            if not adapter.validate_model_path(LOCAL_LLM_MODEL_PATH):
                print(f"Local LLM model file not found: {LOCAL_LLM_MODEL_PATH}")
                return False
                
            if not adapter.validate_model_path(LOCAL_EMBEDDING_MODEL_PATH):
                print(f"Local embedding model file not found: {LOCAL_EMBEDDING_MODEL_PATH}")
                return False
            
            # Load local embeddings
            self.embeddings = adapter.load_local_embeddings(
                model_path=LOCAL_EMBEDDING_MODEL_PATH,
                n_ctx=LOCAL_LLM_CONTEXT_SIZE
            )
            
            # Load local LLM
            self.llm = adapter.load_local_llm(
                model_path=LOCAL_LLM_MODEL_PATH,
                temperature=LOCAL_LLM_TEMPERATURE,
                max_tokens=LOCAL_LLM_MAX_TOKENS,
                n_ctx=LOCAL_LLM_CONTEXT_SIZE,
                verbose=False
            )
            
            # Load vector store
            vector_manager = VectorStoreManager(QDRANT_PATH, DEFAULT_COLLECTION, VECTOR_SIZE)
            vector_manager.initialize_client()
            
            if vector_manager.collection_exists() and vector_manager.collection_has_documents():
                self.vectorstore = vector_manager.get_vectorstore(self.embeddings)
                self.initialized = True
                return True
            else:
                print("Vector store is not ready. Please ensure documents are indexed.")
                return False
                
        except Exception as e:
            print(f"Error initializing RAG system: {e}")
            return False
    
    def get_response(self, question):
        """Get RAG response for a question"""
        if not self.initialized:
            return "RAG system not initialized"
            
        try:
            # Retrieve context
            context_docs = self.vectorstore.similarity_search(question, k=TOP_K)
            
            if not context_docs:
                return "I couldn't find any relevant information to answer your question."
            
            # Format context
            context_text = "\n\n".join([doc.page_content for doc in context_docs if hasattr(doc, "page_content")])
            
            # Create prompt
            prompt = PromptTemplate.from_template(RAG_PROMPT)
            formatted_prompt = prompt.invoke({"question": question, "context": context_text})
            
            # Generate response
            response = self.llm.invoke(formatted_prompt)
            
            # Handle both string responses and message objects
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
                
        except Exception as e:
            return f"Sorry, I encountered an error while generating: {str(e)}"

# Initialize RAG system
rag_system = RAGSystem()

@app.route('/')
def index():
    # Initialize session if not exists
    if 'session_id' not in session:
        session['session_id'] = os.urandom(16).hex()
    
    # Initialize chat history for this session
    if session['session_id'] not in chat_storage:
        chat_storage[session['session_id']] = []
    
    # Initialize RAG system if not already done
    if not rag_system.initialized:
        rag_system.initialize()
    
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    if not rag_system.initialized:
        return jsonify({'error': 'RAG system not initialized'}), 500
        
    user_message = request.json.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    # Add user message to chat history
    chat_history = chat_storage.get(session['session_id'], [])
    chat_history.append({
        'sender': 'user',
        'message': user_message,
        'timestamp': datetime.now().isoformat()
    })
    
    # Get RAG response
    ai_response = rag_system.get_response(user_message)
    
    # Add AI response to chat history
    ai_message = {
        'sender': 'ai',
        'message': ai_response,
        'timestamp': datetime.now().isoformat()
    }
    chat_history.append(ai_message)
    
    # Update chat storage
    chat_storage[session['session_id']] = chat_history
    
    return jsonify({
        'user_message': user_message,
        'ai_response': ai_response
    })

@app.route('/history')
def history():
    chat_history = chat_storage.get(session['session_id'], [])
    return jsonify(chat_history)

@app.route('/clear')
def clear():
    session_id = session.get('session_id')
    if session_id and session_id in chat_storage:
        chat_storage[session_id] = []
    return jsonify({'status': 'success'})

@app.route('/status')
def status():
    return jsonify({
        'initialized': rag_system.initialized,
        'model_path': LOCAL_LLM_MODEL_PATH if rag_system.initialized else None,
        'embedding_path': LOCAL_EMBEDDING_MODEL_PATH if rag_system.initialized else None
    })

if __name__ == '__main__':
    # Initialize the RAG system
    print("Initializing RAG system...")
    if rag_system.initialize():
        print("RAG system initialized successfully")
    else:
        print("Failed to initialize RAG system")
    
    app.run(debug=True, port=8501, host='0.0.0.0')
