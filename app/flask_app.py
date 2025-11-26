# app/flask_app.py
"""
Expert-level Flask RAG application for Onestream documentation.
This application provides a sophisticated, professional interface for querying Onestream documentation
using Retrieval-Augmented Generation (RAG) with local LLMs, following industry best practices.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import json
import logging

# Add the current directory to path to allow direct imports
sys.path.append(str(Path(__file__).parent))

from flask import Flask, render_template, request, jsonify, session

# Import our modules with proper error handling
try:
    from config import *
    from document_processor import DocumentProcessor, DocumentProcessingResult
    from input_validator import InputValidator
    from vector_store_manager import VectorStoreManager, VectorStoreError
    from local_llm_adapter import LocalLLMAdapter, LocalLLMError
    from langchain_core.prompts import PromptTemplate
except Exception as e:
    print(f"❌ Failed to initialize application: {e}")
    sys.exit(1)

# Configure logging with professional settings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'onestream-rag-expert-secret-key-here'

# In-memory storage for chat history (in production, use a database)
chat_storage = {}

class RAGSystem:
    """Expert-level RAG System that integrates with the existing Onestream components"""
    
    def __init__(self):
        self.llm = None
        self.embeddings = None
        self.vectorstore = None
        self.initialized = False
        self.logger = logging.getLogger(__name__)
    
    def initialize(self):
        """Initialize the RAG system with expert-level error handling and logging"""
        if self.initialized:
            self.logger.info("RAG system already initialized")
            return True, "Already initialized"
            
        try:
            self.logger.info("Initializing RAG system")
            
            # Initialize local LLM adapter
            adapter = LocalLLMAdapter()
            self.logger.info("Local LLM adapter initialized")
            
            # Validate model paths with detailed logging
            local_model_path = os.getenv("LOCAL_LLM_MODEL_PATH", LOCAL_LLM_MODEL_PATH)
            local_embedding_path = os.getenv("LOCAL_EMBEDDING_MODEL_PATH", LOCAL_EMBEDDING_MODEL_PATH)
            
            self.logger.info(f"Validating LLM model path: {local_model_path}")
            if not adapter.validate_model_path(local_model_path):
                error_msg = f"LLM model file not found: {local_model_path}"
                self.logger.error(error_msg)
                return False, error_msg
                
            self.logger.info(f"Validating embedding model path: {local_embedding_path}")
            if not adapter.validate_model_path(local_embedding_path):
                error_msg = f"Embedding model file not found: {local_embedding_path}"
                self.logger.error(error_msg)
                return False, error_msg
            
            # Load embeddings with logging
            self.logger.info("Loading local embeddings")
            self.embeddings = adapter.load_local_embeddings(
                model_path=local_embedding_path,
                n_ctx=LOCAL_LLM_CONTEXT_SIZE
            )
            self.logger.info("Local embeddings loaded successfully")
            
            # Load LLM with logging
            self.logger.info("Loading local LLM")
            self.llm = adapter.load_local_llm(
                model_path=local_model_path,
                temperature=LOCAL_LLM_TEMPERATURE,
                max_tokens=LOCAL_LLM_MAX_TOKENS,
                n_ctx=LOCAL_LLM_CONTEXT_SIZE,
                verbose=False
            )
            self.logger.info("Local LLM loaded successfully")
            
            # Load vector store with detailed logging
            self.logger.info("Initializing vector store manager")
            vector_manager = VectorStoreManager(QDRANT_PATH, DEFAULT_COLLECTION, VECTOR_SIZE)
            vector_manager.initialize_client()
            self.logger.info("Vector store client initialized")
            
            if vector_manager.collection_exists() and vector_manager.collection_has_documents():
                self.logger.info("Vector store collection exists and has documents")
                # Collection exists and has documents, use existing vector store
                self.vectorstore = vector_manager.get_vectorstore(self.embeddings)
                self.logger.info("Vector store loaded successfully")
            else:
                error_msg = "Vector store not ready. Please index documents first."
                self.logger.warning(error_msg)
                return False, error_msg
            
            self.initialized = True
            self.logger.info("RAG system initialized successfully")
            return True, "RAG system initialized successfully"
            
        except LocalLLMError as e:
            error_msg = f"Failed to load local LLM or embeddings: {e}"
            self.logger.error(error_msg)
            return False, error_msg
        except VectorStoreError as e:
            error_msg = f"Vector store error: {e}"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error initializing RAG system: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def get_response(self, question):
        """Get RAG response for a question with expert-level error handling"""
        if not self.initialized:
            self.logger.warning("RAG system not initialized")
            return "System not initialized"
        
        try:
            self.logger.info(f"Processing question: {question[:50]}...")
            
            # Validate and sanitize input with logging
            is_valid, error_msg = InputValidator.validate_question(question)
            if not is_valid:
                self.logger.warning(f"Invalid input: {error_msg}")
                return f"Invalid input: {error_msg}"
            
            sanitized_input = InputValidator.sanitize_text(question)
            self.logger.info("Input validated and sanitized")
            
            # Retrieve context with logging
            self.logger.info("Retrieving context from vector store")
            context_docs = self.vectorstore.similarity_search(sanitized_input, k=TOP_K)
            self.logger.info(f"Retrieved {len(context_docs)} context documents")
            
            if not context_docs:
                self.logger.warning("No context documents found")
                return "I couldn't find any relevant information to answer your question."
            
            # Format context with logging
            self.logger.info("Formatting context")
            context_text = "\n\n".join([doc.page_content for doc in context_docs if hasattr(doc, "page_content")])
            
            # Create prompt with logging
            self.logger.info("Creating prompt")
            prompt = PromptTemplate.from_template(RAG_PROMPT)
            formatted_prompt = prompt.invoke({"question": sanitized_input, "context": context_text})
            
            # Generate response with logging
            self.logger.info("Generating response")
            response = self.llm.invoke(formatted_prompt)
            self.logger.info("Response generated successfully")
            
            # Handle response format with logging
            if hasattr(response, 'content'):
                self.logger.info("Returning response with content attribute")
                return response.content
            else:
                self.logger.info("Returning string response")
                return str(response)
                
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            self.logger.error(error_msg)
            return error_msg

# Initialize RAG system
rag_system = RAGSystem()

@app.route('/')
def index():
    """Render the main chat interface"""
    # Initialize session if not exists
    if 'session_id' not in session:
        session['session_id'] = os.urandom(16).hex()
        logger.info(f"New session created: {session['session_id']}")
    
    # Initialize chat history for this session
    if session['session_id'] not in chat_storage:
        chat_storage[session['session_id']] = []
        logger.info(f"Chat history initialized for session: {session['session_id']}")
    
    logger.info(f"Serving index page for session: {session['session_id']}")
    return render_template('index.html')

@app.route('/initialize')
def initialize():
    """Initialize the RAG system"""
    logger.info("Initializing RAG system via API")
    success, message = rag_system.initialize()
    if success:
        logger.info("RAG system initialized successfully via API")
        return jsonify({
            'status': 'success',
            'message': message
        })
    else:
        logger.error(f"RAG system initialization failed: {message}")
        return jsonify({
            'status': 'error',
            'message': message
        }), 500

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages with RAG"""
    data = request.get_json()
    user_message = data.get('message', '').strip()
    
    logger.info(f"Received chat message: {user_message[:50]}...")
    
    if not user_message:
        logger.warning("Empty message received")
        return jsonify({'error': 'No message provided'}), 400
    
    # Validate input
    is_valid, error_msg = InputValidator.validate_question(user_message)
    if not is_valid:
        logger.warning(f"Invalid input: {error_msg}")
        return jsonify({'error': error_msg}), 400
    
    # Sanitize input
    sanitized_input = InputValidator.sanitize_text(user_message)
    logger.info("Input validated and sanitized")
    
    # Add user message to chat history
    chat_history = chat_storage.get(session['session_id'], [])
    chat_history.append({
        'sender': 'user',
        'message': sanitized_input,
        'timestamp': datetime.now().isoformat()
    })
    logger.info("User message added to chat history")
    
    # Get RAG response
    logger.info("Requesting RAG response")
    ai_response = rag_system.get_response(sanitized_input)
    logger.info("RAG response received")
    
    # Add AI response to chat history
    chat_history.append({
        'sender': 'ai',
        'message': ai_response,
        'timestamp': datetime.now().isoformat()
    })
    logger.info("AI response added to chat history")
    
    # Update chat storage
    chat_storage[session['session_id']] = chat_history
    logger.info("Chat storage updated")
    
    return jsonify({
        'user_message': sanitized_input,
        'ai_response': ai_response
    })

@app.route('/history')
def history():
    """Get chat history"""
    chat_history = chat_storage.get(session['session_id'], [])
    logger.info(f"Retrieved chat history for session: {session['session_id']}")
    return jsonify(chat_history)

@app.route('/clear')
def clear():
    """Clear chat history"""
    session_id = session.get('session_id')
    if session_id and session_id in chat_storage:
        chat_storage[session_id] = []
        logger.info(f"Cleared chat history for session: {session_id}")
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')