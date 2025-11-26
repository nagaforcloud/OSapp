# app/auth.py
"""
Authentication module for the Onestream RAG application.
Handles user authentication, session management, and security features.
"""

import streamlit as st
import hashlib
import secrets
import time
from typing import Dict, Optional
from datetime import datetime, timedelta

class AuthError(Exception):
    """Custom exception for authentication errors"""
    pass

def hash_password(password: str, salt: str) -> str:
    """
    Hash a password with salt using SHA-256.
    
    Args:
        password: Plain text password
        salt: Salt to use for hashing
        
    Returns:
        Hashed password
    """
    return hashlib.sha256((password + salt).encode()).hexdigest()

def generate_session_token() -> str:
    """
    Generate a secure session token.
    
    Returns:
        Secure random token
    """
    return secrets.token_urlsafe(32)

def authenticate(max_attempts: int = 5, lockout_minutes: int = 15) -> bool:
    """
    Enhanced password-based authentication with session management and security features.
    
    Args:
        max_attempts: Maximum failed login attempts before lockout
        lockout_minutes: Lockout duration in minutes after max attempts
        
    Returns:
        Authentication status
    """
    # Initialize session state variables
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        
    if "login_attempts" not in st.session_state:
        st.session_state.login_attempts = 0
        
    if "last_attempt_time" not in st.session_state:
        st.session_state.last_attempt_time = None
        
    if "session_token" not in st.session_state:
        st.session_state.session_token = None
        
    # Check if account is locked
    if (st.session_state.login_attempts >= max_attempts and 
        st.session_state.last_attempt_time and
        datetime.now() - st.session_state.last_attempt_time < timedelta(minutes=lockout_minutes)):
        remaining_time = timedelta(minutes=lockout_minutes) - (datetime.now() - st.session_state.last_attempt_time)
        minutes_left = int(remaining_time.total_seconds() // 60)
        st.sidebar.error(f"🔒 Account locked. Try again in {minutes_left} minutes.")
        return False
    
    # Show login form
    login = st.sidebar.expander("🔐 Login", expanded=not st.session_state.authenticated)
    with login:
        pwd = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            try:
                # Validate input
                if not pwd or len(pwd.strip()) == 0:
                    st.error("Password cannot be empty")
                    return False
                
                # Check password
                if pwd == st.secrets["ADMIN_PASSWORD"]:
                    # Reset failed attempts
                    st.session_state.login_attempts = 0
                    st.session_state.last_attempt_time = None
                    
                    # Set authentication
                    st.session_state.authenticated = True
                    st.session_state.session_token = generate_session_token()
                    st.session_state.login_time = datetime.now()
                    
                    # Force refresh
                    st.rerun()
                else:
                    # Increment failed attempts
                    st.session_state.login_attempts += 1
                    st.session_state.last_attempt_time = datetime.now()
                    
                    if st.session_state.login_attempts >= max_attempts:
                        st.error(f"🔒 Too many failed attempts. Account locked for {lockout_minutes} minutes.")
                    else:
                        remaining = max_attempts - st.session_state.login_attempts
                        st.error(f"Invalid password. {remaining} attempts remaining.")
            except Exception as e:
                st.error(f"Authentication error: {str(e)}")
                return False
                
    return st.session_state.get("authenticated", False)

def logout():
    """Logout and clear session data."""
    # Clear all authentication-related session state
    auth_keys = [
        "authenticated", "login_attempts", "last_attempt_time", 
        "session_token", "login_time"
    ]
    
    for key in auth_keys:
        if key in st.session_state:
            del st.session_state[key]
            
    st.rerun()

def is_session_valid(session_timeout_hours: int = 24) -> bool:
    """
    Check if the current session is still valid.
    
    Args:
        session_timeout_hours: Session timeout in hours
        
    Returns:
        Whether session is valid
    """
    if not st.session_state.get("authenticated", False):
        return False
        
    # Check session timeout
    login_time = st.session_state.get("login_time")
    if login_time:
        if datetime.now() - login_time > timedelta(hours=session_timeout_hours):
            logout()
            return False
            
    return True

def get_current_user() -> Optional[str]:
    """
    Get current authenticated user identifier.
    
    Returns:
        User identifier or None if not authenticated
    """
    if st.session_state.get("authenticated", False):
        return "admin"  # In a more complex system, this would return actual user info
    return None
