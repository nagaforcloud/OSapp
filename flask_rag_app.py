# flask_rag_app.py
"""
Flask RAG application for Onestream documentation.
This application provides a web interface for querying Onestream documentation
using Retrieval-Augmented Generation (RAG) with local LLM.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add the app directory to path for imports
sys.path.append(str(Path(__file__).parent / "app"))

from flask import Flask, render_template, request, jsonify, session

# Import RAG components
from app.config import *
from app.vector_store_manager import VectorStoreManager, VectorStoreError
from app.local_llm_adapter import LocalLLMAdapter, LocalLLMError
from app.input_validator import InputValidator
from langchain_core.prompts import PromptTemplate

app = Flask(__name__)
app.secret_key = 'onestream-rag-secret-key'

class RAGSystem:
    """RAG System that integrates with the existing Onestream components"""
    
    def __init__(self):
        self.llm = None
        self.embeddings = None
        self.vectorstore = None
        self.initialized = False
    
    def initialize(self):
        """Initialize the RAG system with local LLM and embeddings"""
        if self.initialized:
            return True, "Already initialized"
            
        try:
            # Initialize local LLM adapter
            adapter = LocalLLMAdapter()
            
            # Validate model paths
            if not adapter.validate_model_path(LOCAL_LLM_MODEL_PATH):
                return False, f"LLM model not found: {LOCAL_LLM_MODEL_PATH}"
                
            if not adapter.validate_model_path(LOCAL_EMBEDDING_MODEL_PATH):
                return False, f"Embedding model not found: {LOCAL_EMBEDDING_MODEL_PATH}"
            
            # Load embeddings
            self.embeddings = adapter.load_local_embeddings(
                model_path=LOCAL_EMBEDDING_MODEL_PATH,
                n_ctx=LOCAL_LLM_CONTEXT_SIZE
            )
            
            # Load LLM
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
                return True, "RAG system initialized successfully"
            else:
                return False, "Vector store not ready. Please index documents first."
            
        except Exception as e:
            return False, f"Error initializing RAG system: {str(e)}"
    
    def get_response(self, question):
        """Get RAG response for a question"""
        if not self.initialized:
            return "System not initialized"
        
        try:
            # Retrieve context
            context_docs = self.vectorstore.similarity_search(question, k=TOP_K)
            
            if not context_docs:
                return "I couldn't find any relevant information to answer your question."
            
            # Format context
            context_text = "\n\n".join([doc.page_content for doc in context_docs if hasattr(doc, "page_content")])
            
            # Create prompt using the RAG prompt template from config
            prompt = PromptTemplate.from_template(RAG_PROMPT)
            formatted_prompt = prompt.invoke({"question": question, "context": context_text})
            
            # Generate response - convert to string if needed
            response = self.llm.invoke(formatted_prompt.to_string() if hasattr(formatted_prompt, 'to_string') else str(formatted_prompt))
            
            # Handle response format
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
                
        except Exception as e:
            return f"Error generating response: {str(e)}"

# Initialize RAG system
rag_system = RAGSystem()

# In-memory storage for chat history (in production, use a database)
chat_storage = {}

@app.route('/')
def index():
    # Initialize session if not exists
    if 'session_id' not in session:
        session['session_id'] = os.urandom(16).hex()
    
    # Initialize chat history for this session
    if session['session_id'] not in chat_storage:
        chat_storage[session['session_id']] = []
    
    return render_template('index.html')

@app.route('/initialize')
def initialize():
    """Initialize the RAG system"""
    success, message = rag_system.initialize()
    if success:
        return jsonify({
            'status': 'success',
            'message': message
        })
    else:
        return jsonify({
            'status': 'error',
            'message': message
        }), 500

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages with RAG"""
    user_message = request.json.get('message', '').strip()
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    # Validate input
    is_valid, error_msg = InputValidator.validate_question(user_message)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    # Sanitize input
    sanitized_input = InputValidator.sanitize_text(user_message)
    
    # Add user message to chat history
    chat_history = chat_storage.get(session['session_id'], [])
    chat_history.append({
        'sender': 'user',
        'message': sanitized_input,
        'timestamp': datetime.now().isoformat()
    })
    
    # Get RAG response
    ai_response = rag_system.get_response(sanitized_input)
    
    # Add AI response to chat history
    chat_history.append({
        'sender': 'ai',
        'message': ai_response,
        'timestamp': datetime.now().isoformat()
    })
    
    # Update chat storage
    chat_storage[session['session_id']] = chat_history
    
    return jsonify({
        'user_message': sanitized_input,
        'ai_response': ai_response
    })

@app.route('/history')
def history():
    """Get chat history"""
    chat_history = chat_storage.get(session['session_id'], [])
    return jsonify(chat_history)

@app.route('/clear')
def clear():
    """Clear chat history"""
    session_id = session.get('session_id')
    if session_id and session_id in chat_storage:
        chat_storage[session_id] = []
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True, port=8501, host='0.0.0.0')