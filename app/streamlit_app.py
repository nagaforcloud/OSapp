# app/streamlit_app.py
"""
Onestream RAG Assistant with Local LLM Integration
This application provides a chat interface for querying Onestream documentation
using Retrieval-Augmented Generation (RAG) with local LLMs.
"""

import streamlit as st
import sys
from pathlib import Path

# Add the current directory to path to allow direct imports
sys.path.append(str(Path(__file__).parent))

# Import our modules
try:
    from config import *
    from document_processor import DocumentProcessor, DocumentProcessingResult
    from input_validator import InputValidator
    from vector_store_manager import VectorStoreManager, VectorStoreError
    from local_llm_adapter import LocalLLMAdapter, LocalLLMError
    from langchain_core.prompts import PromptTemplate
    from langchain_core.documents import Document
except Exception as e:
    st.error(f"❌ Failed to initialize application: {e}")
    st.stop()

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "vector_store_ready" not in st.session_state:
    st.session_state.vector_store_ready = False
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None

# --- Modern UI Styling ---
st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main app background */
    .stApp {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Main container */
    .main > div {
        max-width: 1200px;
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* App header */
    .app-header {
        text-align: center;
        padding: 1.5rem;
        margin-bottom: 1rem;
        background: white;
        border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border: 1px solid rgba(0, 0, 0, 0.05);
    }
    
    .app-header h1 {
        color: #2c3e50;
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #3498db 0%, #2c3e50 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .app-header p {
        color: #7f8c8d;
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        font-weight: 400;
    }
    
    /* Status card */
    .status-card {
        background: white;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        border: 1px solid rgba(0, 0, 0, 0.08);
        text-align: center;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.8rem;
    }
    
    .status-icon {
        font-size: 1.4rem;
    }
    
    .status-ready {
        color: #27ae60;
        background-color: #e8f7f0;
    }
    
    .status-building {
        color: #f39c12;
        background-color: #fef5e7;
    }
    
    /* Chat container */
    .chat-container {
        display: flex;
        flex-direction: column;
        height: 65vh;
        overflow-y: auto;
        padding: 1.5rem;
        border-radius: 16px;
        background: white;
        margin-bottom: 1.5rem;
        scroll-behavior: smooth;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        border: 1px solid rgba(0, 0, 0, 0.08);
    }
    
    /* Message bubbles */
    .message {
        max-width: 85%;
        padding: 1.2rem;
        margin-bottom: 1.2rem;
        border-radius: 18px;
        line-height: 1.6;
        position: relative;
        animation: fadeIn 0.3s ease-in-out;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    
    /* User messages (right-aligned) */
    .user-message {
        background: linear-gradient(135deg, #3498db 0%, #2c3e50 100%);
        color: white;
        align-self: flex-end;
        border-bottom-right-radius: 5px;
    }
    
    /* AI messages (left-aligned) */
    .ai-message {
        background-color: #f8f9fa;
        color: #2c3e50;
        align-self: flex-start;
        border-bottom-left-radius: 5px;
        border: 1px solid #e9ecef;
    }
    
    /* Message sender */
    .message-sender {
        font-weight: 600;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    
    /* Welcome message */
    .welcome-message {
        text-align: center;
        color: #7f8c8d;
        margin: 2rem auto;
        padding: 2rem;
        background: #f8f9fa;
        border-radius: 12px;
        max-width: 80%;
        border: 1px solid #e9ecef;
    }
    
    .welcome-message h3 {
        color: #2c3e50;
        margin-top: 0;
        font-weight: 600;
    }
    
    .welcome-message p {
        font-size: 1rem;
        line-height: 1.6;
    }
    
    /* Input area */
    .input-area {
        background: white;
        border-radius: 16px;
        padding: 1.2rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        border: 1px solid rgba(0, 0, 0, 0.08);
    }
    
    /* Input container */
    .input-container {
        display: flex;
        gap: 0.8rem;
    }
    
    /* Input field */
    .chat-input {
        flex: 1;
    }
    
    .stTextInput > div > div {
        border: 1px solid #d1d1d1;
        border-radius: 12px;
        padding: 0.8rem 1.2rem;
        font-size: 1rem;
        transition: all 0.2s ease;
    }
    
    .stTextInput > div > div:focus {
        border-color: #3498db;
        box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.2);
    }
    
    /* Send button */
    .stButton > button {
        background: linear-gradient(135deg, #3498db 0%, #2c3e50 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.8rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 6px rgba(52, 152, 219, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(52, 152, 219, 0.4);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* Animation */
    @keyframes fadeIn {
        from {opacity: 0; transform: translateY(10px);}
        to {opacity: 1; transform: translateY(0);}
    }
    
    /* Scrollbar styling */
    .chat-container::-webkit-scrollbar {
        width: 8px;
    }
    
    .chat-container::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    .chat-container::-webkit-scrollbar-thumb {
        background: #c1c1c1;
        border-radius: 10px;
    }
    
    .chat-container::-webkit-scrollbar-thumb:hover {
        background: #a8a8a8;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .main > div {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        
        .message {
            max-width: 90%;
            padding: 1rem;
        }
        
        .welcome-message {
            max-width: 95%;
            padding: 1.5rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown("""
<div class="app-header">
    <h1>🤖 Onestream RAG Assistant</h1>
    <p>AI-powered search and analysis for Onestream documentation</p>
</div>
""", unsafe_allow_html=True)

# --- LLM & Embeddings (Cached) ---
@st.cache_resource
def load_llm_and_embeddings():
    """Load local LLM and embeddings models with caching."""
    try:
        # Initialize local LLM adapter
        adapter = LocalLLMAdapter()
        
        # Validate model paths from config
        if not adapter.validate_model_path(LOCAL_LLM_MODEL_PATH):
            st.error(f"❌ Local LLM model file not found: {LOCAL_LLM_MODEL_PATH}")
            return None, None
            
        if not adapter.validate_model_path(LOCAL_EMBEDDING_MODEL_PATH):
            st.error(f"❌ Local embedding model file not found: {LOCAL_EMBEDDING_MODEL_PATH}")
            return None, None
        
        # Load local embeddings
        embeddings = adapter.load_local_embeddings(
            model_path=LOCAL_EMBEDDING_MODEL_PATH,
            n_ctx=LOCAL_LLM_CONTEXT_SIZE
        )
        
        # Load local LLM
        llm = adapter.load_local_llm(
            model_path=LOCAL_LLM_MODEL_PATH,
            temperature=LOCAL_LLM_TEMPERATURE,
            max_tokens=LOCAL_LLM_MAX_TOKENS,
            n_ctx=LOCAL_LLM_CONTEXT_SIZE,
            verbose=False
        )
        
        st.success("✅ AI models loaded successfully")
        return llm, embeddings
        
    except LocalLLMError as e:
        st.error(f"❌ Failed to load local LLM or embeddings: {e}")
        return None, None
    except Exception as e:
        st.error(f"❌ Unexpected error loading models: {e}")
        return None, None

# --- Vector Store Loader ---
def load_vectorstore(embeddings):
    """Load existing vector store or initialize if needed."""
    try:
        # Initialize vector store manager
        vector_manager = VectorStoreManager(QDRANT_PATH, DEFAULT_COLLECTION, VECTOR_SIZE)
        
        # Check if collection already exists and has documents
        vector_manager.initialize_client()
        
        if vector_manager.collection_exists() and vector_manager.collection_has_documents():
            # Collection exists and has documents, use existing vector store
            st.info("✅ Using existing vector store (already indexed)")
            return vector_manager.get_vectorstore(embeddings)
        else:
            st.error("❌ Vector store is not ready. Please ensure documents are indexed.")
            return None
            
    except VectorStoreError as e:
        st.error(f"❌ Vector store error: {e}")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error with vector store: {e}")
        return None

# --- RAG Functions ---
def retrieve_context(vectorstore, question, k=4):
    """Retrieve relevant documents based on the question."""
    try:
        return vectorstore.similarity_search(question, k=k)
    except Exception as e:
        st.error(f"Retrieval failed: {e}")
        return []

def generate_response(llm, context, question):
    """Generate an answer based on the retrieved context."""
    try:
        if not context:
            return "I couldn't find any relevant information to answer your question."
        
        # Format context
        context_text = "\n\n".join([doc.page_content for doc in context if hasattr(doc, "page_content")])
        
        # Create prompt
        prompt = PromptTemplate.from_template(RAG_PROMPT)
        formatted_prompt = prompt.invoke({"question": question, "context": context_text})
        
        # Generate response
        response = llm.invoke(formatted_prompt)
        
        # Handle both string responses and message objects
        if hasattr(response, 'content'):
            return response.content
        else:
            return str(response)
            
    except Exception as e:
        return f"Sorry, I encountered an error while generating: {str(e)}"

# Load LLM and embeddings
with st.spinner("🧠 Loading AI models..."):
    llm, embeddings = load_llm_and_embeddings()

# Safety check
if llm is None or embeddings is None:
    st.error("💥 Failed to initialize AI models.")
    st.stop()

# --- Vector Store Initialization ---
if not st.session_state.vector_store_ready:
    with st.spinner("📚 Loading document index..."):
        vectorstore = load_vectorstore(embeddings)
        if vectorstore:
            st.session_state.vectorstore = vectorstore
            st.session_state.vector_store_ready = True
            st.success("✅ Document index loaded successfully")
        else:
            st.error("Failed to load vector store. Please check your documents and try again.")
            st.stop()

# --- Main Chat Interface ---
# Status indicator
st.markdown('<div class="status-card status-ready"><span class="status-icon">✅</span> Assistant is ready</div>', unsafe_allow_html=True)

# Chat container
chat_container = st.container()

# Display chat messages
with chat_container:
    st.markdown('<div class="chat-container" id="chat-container">', unsafe_allow_html=True)
    
    # Show welcome message if no messages
    if not st.session_state.messages:
        st.markdown('''
        <div class="welcome-message">
            <h3>👋 Welcome to Onestream Assistant!</h3>
            <p>I'm your AI-powered assistant for Onestream documentation.</p>
            <p>Ask me anything about:</p>
            <ul style="text-align: left; display: inline-block;">
                <li>Onestream features and functionality</li>
                <li>Best practices and implementation guides</li>
                <li>Troubleshooting and error resolution</li>
                <li>Configuration and setup instructions</li>
            </ul>
            <p style="font-size: 2rem; margin-top: 1rem;">🤖✨</p>
        </div>
        ''', unsafe_allow_html=True)
    
    # Display chat history
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f"""
            <div class="message user-message">
                <div class="message-sender">👤 You</div>
                <div>{message["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="message ai-message">
                <div class="message-sender">🤖 Assistant</div>
                <div>{message["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Input area
with st.form(key="chat_form", clear_on_submit=True):
    st.markdown('<div class="input-area">', unsafe_allow_html=True)
    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    
    user_input = st.text_input("", placeholder="Ask a question about Onestream documentation...", key="user_input", label_visibility="collapsed")
    submit_button = st.form_submit_button("Send 🚀")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Process input when submitted
if submit_button and user_input:
    # Validate and sanitize user input
    is_valid, error_msg = InputValidator.validate_question(user_input)
    sanitized_input = InputValidator.sanitize_text(user_input)
    
    if not is_valid:
        st.error(f"❌ Invalid input: {error_msg}")
    else:
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": sanitized_input})
        
        # Rerun to show user message immediately
        st.rerun()

# Handle AI response (separate from user input to avoid double processing)
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.spinner("🧠 Thinking..."):
        # Retrieve context using RAG
        context = retrieve_context(st.session_state.vectorstore, st.session_state.messages[-1]["content"], k=TOP_K)
        
        # Generate response using LLM with context
        answer = generate_response(llm, context, st.session_state.messages[-1]["content"])
        
        # Add AI response to chat
        st.session_state.messages.append({"role": "assistant", "content": answer})
        
        # Rerun to show AI response
        st.rerun()