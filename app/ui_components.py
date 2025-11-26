# app/ui_components.py
"""
UI components and styling for the Onestream RAG application.
Provides modern, clean UI elements with consistent styling.
"""

import streamlit as st

def apply_modern_ui_styling():
    """Apply modern CSS styling to the entire application."""
    st.markdown("""
    <style>
    /* Main app styling */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Headers */
    h1, h2, h3 {
        color: #1f3a93;
        font-weight: 600;
    }
    
    /* Cards and containers */
    .stMarkdown, .stDataFrame, .stDataFrameContainer {
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        padding: 20px;
        margin-bottom: 20px;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #4285f4;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    .stButton>button:hover {
        background-color: #3367d6;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    .stButton>button:active {
        transform: translateY(0);
    }
    
    /* Input fields */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        padding: 10px;
    }
    
    /* Select boxes */
    .stSelectbox>div>div {
        border: 1px solid #e0e0e0;
        border-radius: 6px;
    }
    
    /* Sliders */
    .stSlider>div>div {
        background-color: #e0e0e0;
    }
    
    .stSlider>div>div>div {
        background-color: #4285f4;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #f1f3f4;
        border-radius: 6px;
    }
    
    .streamlit-expanderContent {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-top: none;
        border-radius: 0 0 6px 6px;
    }
    
    /* Progress bar */
    .stProgress>div>div {
        background-color: #4285f4;
    }
    
    /* Alerts */
    .stAlert {
        border-radius: 8px;
        border: none;
    }
    
    /* Success alert */
    .stAlert.success {
        background-color: #e8f5e9;
        color: #2e7d32;
    }
    
    /* Warning alert */
    .stAlert.warning {
        background-color: #fff8e1;
        color: #e65100;
    }
    
    /* Error alert */
    .stAlert.error {
        background-color: #ffebee;
        color: #c62828;
    }
    
    /* Info alert */
    .stAlert.info {
        background-color: #e3f2fd;
        color: #1565c0;
    }
    
    /* Metrics */
    .stMetric>div {
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        padding: 15px;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #ffffff;
    }
    
    /* Radio buttons */
    .stRadio>div {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 10px;
    }
    
    /* Checkboxes */
    .stCheckbox>label>div {
        background-color: #f8f9fa;
        border-radius: 6px;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

def render_header():
    """Render the main application header with modern styling."""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1f3a93 0%, #3953c5 100%); padding: 30px; border-radius: 15px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap;">
            <div>
                <h1 style="color: white; margin: 0; font-size: 2.5rem;">🤖 Onestream RAG Assistant</h1>
                <p style="color: #e0e0e0; margin: 10px 0 0 0; font-size: 1.2rem;">🔍 Search & analyze Onestream documentation with AI</p>
            </div>
            <div style="font-size: 3rem;">
                🤖
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar_header():
    """Render the sidebar header with modern styling."""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1f3a93 0%, #3953c5 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center;">
        <h2 style="color: white; margin: 0; font-size: 1.8rem;">⚙️ Control Panel</h2>
        <p style="color: #e0e0e0; margin: 10px 0 0 0; font-size: 1rem;">Configure your assistant</p>
    </div>
    """, unsafe_allow_html=True)

def render_footer(version: str):
    """Render the application footer with version information."""
    st.markdown(f"""
    <div style="background-color: #f1f3f4; padding: 20px; border-radius: 10px; margin-top: 30px; text-align: center;">
        <p style="margin: 0; color: #5f6368;">
            🤖 Onestream RAG Assistant v{version} | Built with ❤️ using Streamlit
        </p>
        <p style="margin: 5px 0 0 0; color: #9aa0a6; font-size: 0.9rem;">
            Secure, auditable, production-ready RAG platform
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_modern_chat_interface():
    """Render a modern chat interface with message bubbles."""
    # Custom CSS for chat interface
    st.markdown("""
    <style>
    /* Chat container */
    .chat-container {
        display: flex;
        flex-direction: column;
        height: 60vh;
        overflow-y: auto;
        padding: 20px;
        border-radius: 10px;
        background-color: #ffffff;
        margin-bottom: 20px;
        scroll-behavior: smooth;
        border: 1px solid #e0e0e0;
    }
    
    /* Message bubbles */
    .message {
        max-width: 80%;
        padding: 15px;
        margin-bottom: 15px;
        border-radius: 18px;
        line-height: 1.5;
        position: relative;
        animation: fadeIn 0.3s ease-in-out;
    }
    
    /* User messages (right-aligned) */
    .user-message {
        background-color: #4285f4;
        color: white;
        align-self: flex-end;
        border-bottom-right-radius: 5px;
    }
    
    /* AI messages (left-aligned) */
    .ai-message {
        background-color: #f1f3f4;
        color: #333333;
        align-self: flex-start;
        border-bottom-left-radius: 5px;
    }
    
    /* Message sender */
    .message-sender {
        font-weight: 600;
        margin-bottom: 5px;
        font-size: 0.9rem;
    }
    
    /* Input container */
    .input-container {
        display: flex;
        padding: 10px;
        background-color: white;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin-bottom: 20px;
    }
    
    /* Input field */
    .chat-input {
        flex: 1;
        padding: 12px 15px;
        border: none;
        border-radius: 24px;
        outline: none;
        font-size: 1rem;
        background-color: #f8f9fa;
    }
    
    /* Send button */
    .send-button {
        background-color: #4285f4;
        color: white;
        border: none;
        border-radius: 50%;
        width: 45px;
        height: 45px;
        margin-left: 10px;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    
    .send-button:hover {
        background-color: #3367d6;
    }
    
    /* Send button icon */
    .send-icon {
        font-size: 1.2rem;
    }
    
    /* Welcome message */
    .welcome-message {
        text-align: center;
        color: #666;
        font-style: italic;
        margin: 20px 0;
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
    </style>
    """, unsafe_allow_html=True)

def show_welcome_message():
    """Display a welcoming message for new users."""
    st.markdown("""
    <div style="text-align: center; padding: 30px; background-color: #e3f2fd; border-radius: 10px; margin-bottom: 20px;">
        <h2 style="color: #1565c0; margin-bottom: 15px;">👋 Welcome to Onestream Assistant!</h2>
        <p style="font-size: 1.1rem; color: #333;">
            I'm here to help you search and understand Onestream documentation. 
            Ask me anything about Onestream features, best practices, or troubleshooting.
        </p>
        <div style="margin-top: 20px; font-size: 3rem;">
            🤖✨
        </div>
    </div>
    """, unsafe_allow_html=True)