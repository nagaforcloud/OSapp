# gradio_app.py
"""
Gradio interface for Onestream RAG Assistant.
This application provides a clean, modern chat interface for querying Onestream documentation
using Retrieval-Augmented Generation (RAG) with local LLM.
"""

import os
import sys
from pathlib import Path

# Add the app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

import gradio as gr
from app.config import *
from app.vector_store_manager import VectorStoreManager, VectorStoreError
from app.local_llm_adapter import LocalLLMAdapter, LocalLLMError
from app.input_validator import InputValidator
from langchain_core.prompts import PromptTemplate

class RAGChatbot:
    """RAG Chatbot that integrates with existing Onestream components"""
    
    def __init__(self):
        self.llm = None
        self.vectorstore = None
        self.initialized = False
        self.history = []
    
    def initialize(self):
        """Initialize the RAG system"""
        if self.initialized:
            return True
            
        try:
            # Initialize local LLM adapter
            adapter = LocalLLMAdapter()
            
            # Validate model paths
            if not adapter.validate_model_path(LOCAL_LLM_MODEL_PATH):
                raise Exception(f"LLM model not found: {LOCAL_LLM_MODEL_PATH}")
                
            if not adapter.validate_model_path(LOCAL_EMBEDDING_MODEL_PATH):
                raise Exception(f"Embedding model not found: {LOCAL_EMBEDDING_MODEL_PATH}")
            
            # Load embeddings
            embeddings = adapter.load_local_embeddings(
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
                self.vectorstore = vector_manager.get_vectorstore(embeddings)
            else:
                raise Exception("Vector store not ready. Please index documents first.")
            
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"Error initializing RAG system: {e}")
            return False
    
    def get_response(self, message, history):
        """Get RAG response for a message"""
        if not self.initialized:
            return "System not initialized. Please wait for initialization to complete."
        
        try:
            # Validate input
            is_valid, error_msg = InputValidator.validate_question(message)
            if not is_valid:
                return f"Invalid input: {error_msg}"
            
            # Sanitize input
            sanitized_input = InputValidator.sanitize_text(message)
            
            # Retrieve context
            context_docs = self.vectorstore.similarity_search(sanitized_input, k=TOP_K)
            
            if not context_docs:
                return "I couldn't find any relevant information to answer your question."
            
            # Format context
            context_text = "\n\n".join([doc.page_content for doc in context_docs if hasattr(doc, "page_content")])
            
            # Create prompt
            prompt = PromptTemplate.from_template(RAG_PROMPT)
            formatted_prompt = prompt.invoke({"question": sanitized_input, "context": context_text})
            
            # Generate response
            response = self.llm.invoke(formatted_prompt)
            
            # Handle response format
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
                
        except Exception as e:
            return f"Error generating response: {str(e)}"

# Initialize RAG chatbot
rag_chatbot = RAGChatbot()

# Gradio interface
with gr.Blocks(
    title="Onestream RAG Assistant",
    theme=gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="stone",
        neutral_hue="gray",
    ),
    css="""
    .header {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #1f3a93 0%, #3953c5 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .header h1 {
        font-size: 2rem;
        margin-bottom: 0.5rem;
        font-weight: 600;
    }
    .header p {
        font-size: 1.1rem;
        opacity: 0.9;
    }
    .status {
        text-align: center;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .status-ready {
        background-color: #e8f7f0;
        color: #27ae60;
        border: 1px solid #c8e6c9;
    }
    .status-initializing {
        background-color: #fff8e1;
        color: #f39c12;
        border: 1px solid #ffecb3;
    }
    .chatbot-container {
        height: 500px;
        overflow-y: auto;
    }
    """
) as demo:
    
    # Header
    with gr.Row():
        with gr.Column():
            gr.Markdown("""
            <div class="header">
                <h1>🤖 Onestream RAG Assistant</h1>
                <p>AI-powered search and analysis for Onestream documentation</p>
            </div>
            """)
    
    # Status indicator
    status = gr.Markdown("", elem_classes=["status", "status-initializing"])
    
    # Chat interface
    chatbot = gr.Chatbot(
        label="Conversation",
        bubble_full_width=False,
        avatar_images=(
            "https://cdn-icons-png.flaticon.com/512/847/847969.png",  # User avatar
            "https://cdn-icons-png.flaticon.com/512/4712/4712035.png"   # Bot avatar
        ),
        elem_classes=["chatbot-container"]
    )
    
    # Input
    msg = gr.Textbox(
        label="Your Question",
        placeholder="Ask about Onestream features, best practices, or troubleshooting...",
        container=False
    )
    
    # Clear button
    clear = gr.Button("Clear Chat")
    
    # Initialize RAG system
    def initialize_system():
        """Initialize the RAG system and update status"""
        if rag_chatbot.initialize():
            return gr.Markdown.update(
                value="<div class='status status-ready'>✅ System Ready - Ask me anything about Onestream!</div>",
                elem_classes=["status", "status-ready"]
            )
        else:
            return gr.Markdown.update(
                value="<div class='status status-initializing'>❌ Initialization Failed - Check logs for details</div>",
                elem_classes=["status", "status-initializing"]
            )
    
    # Initialize on load
    demo.load(initialize_system, None, status)
    
    # Chat response function
    def respond(message, chat_history):
        """Handle chat responses"""
        if message.strip() == "":
            return "", chat_history
        
        # Get response from RAG system
        bot_message = rag_chatbot.get_response(message, chat_history)
        
        # Update chat history
        chat_history.append((message, bot_message))
        
        return "", chat_history
    
    # Connect events
    msg.submit(respond, [msg, chatbot], [msg, chatbot])
    clear.click(lambda: None, None, chatbot, queue=False)

if __name__ == "__main__":
    demo.launch(server_port=8501, server_name="0.0.0.0")