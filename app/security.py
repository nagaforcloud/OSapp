# app/security.py
"""
Enhanced security module for the Onestream RAG application.
Provides rate limiting, authentication, input validation, and security monitoring.
"""

import time
import hashlib
import hmac
import secrets
import re
from typing import Dict, Optional, List, Any, Callable
from functools import wraps
from dataclasses import dataclass
from collections import defaultdict, deque
import threading
from datetime import datetime, timedelta

try:
    from flask import request, g, session, abort
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

from app.enhanced_logger import get_current_context, info, warning, error, debug


@dataclass
class SecurityEvent:
    """Security event for monitoring."""
    event_type: str
    timestamp: datetime
    source_ip: str
    user_id: Optional[str] = None
    details: Dict[str, Any] = None
    severity: str = "INFO"  # INFO, WARNING, ERROR, CRITICAL


class RateLimiter:
    """Advanced rate limiting with multiple strategies."""

    def __init__(self, redis_client=None):
        """
        Initialize rate limiter.

        Args:
            redis_client: Redis client for distributed rate limiting
        """
        self.redis_client = redis_client
        self.local_limits: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.lock = threading.Lock()

        # Default rate limits
        self.default_limits = {
            'global': {'requests': 1000, 'window': 3600},  # 1000 requests per hour
            'per_ip': {'requests': 100, 'window': 300},    # 100 requests per 5 minutes
            'per_user': {'requests': 200, 'window': 1800},  # 200 requests per 30 minutes
            'auth_attempts': {'requests': 5, 'window': 900},  # 5 login attempts per 15 minutes
            'document_upload': {'requests': 10, 'window': 3600}  # 10 uploads per hour
        }

    def _get_key(self, identifier: str, limit_type: str) -> str:
        """Generate rate limit key."""
        return f"rate_limit:{limit_type}:{identifier}"

    def _is_allowed_redis(self, key: str, limit: Dict[str, int]) -> bool:
        """Check rate limit using Redis."""
        try:
            pipe = self.redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, limit['window'])
            current_count = pipe.execute()[0]
            return current_count <= limit['requests']
        except Exception as e:
            warning(f"Redis rate limit check failed: {e}", fallback=True)
            return True  # Fail open

    def _is_allowed_local(self, identifier: str, limit: Dict[str, int]) -> bool:
        """Check rate limit using local memory."""
        current_time = time.time()
        key = f"{identifier}_{limit_type}"

        with self.lock:
            # Remove old entries
            cutoff_time = current_time - limit['window']
            while (self.local_limits[key] and
                   self.local_limits[key][0] < cutoff_time):
                self.local_limits[key].popleft()

            # Check if under limit
            if len(self.local_limits[key]) < limit['requests']:
                self.local_limits[key].append(current_time)
                return True

        return False

    def is_allowed(self, identifier: str, limit_type: str = 'global') -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            limit_type: Type of rate limit

        Returns:
            True if request is allowed
        """
        if limit_type not in self.default_limits:
            limit_type = 'global'

        limit = self.default_limits[limit_type]
        key = self._get_key(identifier, limit_type)

        if self.redis_client:
            return self._is_allowed_redis(key, limit)
        else:
            return self._is_allowed_local(identifier, limit)

    def get_remaining_requests(self, identifier: str, limit_type: str = 'global') -> int:
        """Get remaining requests for given limit."""
        if limit_type not in self.default_limits:
            limit_type = 'global'

        limit = self.default_limits[limit_type]
        key = self._get_key(identifier, limit_type)

        if self.redis_client:
            try:
                current = int(self.redis_client.get(key) or 0)
                return max(0, limit['requests'] - current)
            except:
                return limit['requests']
        else:
            # For local storage, calculate from memory
            with self.lock:
                local_key = f"{identifier}_{limit_type}"
                current_time = time.time()
                cutoff_time = current_time - limit['window']

                # Clean old entries
                while (self.local_limits[local_key] and
                       self.local_limits[local_key][0] < cutoff_time):
                    self.local_limits[local_key].popleft()

                return max(0, limit['requests'] - len(self.local_limits[local_key]))


class InputValidator:
    """Input validation and sanitization."""

    def __init__(self):
        """Initialize input validator."""
        # Common dangerous patterns
        self.dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS
            r'javascript:',                # JavaScript URLs
            r'on\w+\s*=',                # Event handlers
            r'eval\s*\(',                # eval() function
            r'document\.cookie',          # Cookie access
            r'union.*select',            # SQL injection
            r'drop\s+table',             # SQL injection
            r'insert\s+into',            # SQL injection
            r'delete\s+from',           # SQL injection
            r'<iframe[^>]*>',            # Iframe injection
            r'<object[^>]*>',            # Object injection
            r'<embed[^>]*>',             # Embed injection
        ]

        self.max_lengths = {
            'text_input': 10000,
            'filename': 255,
            'query': 1000,
            'username': 50,
            'email': 254
        }

    def sanitize_input(self, input_text: str, input_type: str = 'text_input') -> str:
        """
        Sanitize user input.

        Args:
            input_text: Input text to sanitize
            input_type: Type of input for length limits

        Returns:
            Sanitized input text
        """
        if not input_text:
            return ""

        # Check length limit
        max_length = self.max_lengths.get(input_type, self.max_lengths['text_input'])
        if len(input_text) > max_length:
            input_text = input_text[:max_length]

        # Remove dangerous patterns
        sanitized = input_text
        for pattern in self.dangerous_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)

        # HTML encode if needed
        if input_type in ['text_input', 'query']:
            sanitized = sanitized.replace('&', '&amp;')
            sanitized = sanitized.replace('<', '&lt;')
            sanitized = sanitized.replace('>', '&gt;')
            sanitized = sanitized.replace('"', '&quot;')
            sanitized = sanitized.replace("'", '&#x27;')

        return sanitized.strip()

    def validate_file_upload(self, filename: str, file_size: int,
                           allowed_extensions: List[str] = None) -> Dict[str, Any]:
        """
        Validate file upload.

        Args:
            filename: Uploaded filename
            file_size: File size in bytes
            allowed_extensions: List of allowed file extensions

        Returns:
            Validation result
        """
        allowed_extensions = allowed_extensions or [
            'pdf', 'txt', 'md', 'docx', 'doc',
            'xlsx', 'xls', 'pptx', 'ppt'
        ]

        # Check filename
        if not filename:
            return {'valid': False, 'error': 'No filename provided'}

        # Check file extension
        file_extension = filename.lower().split('.')[-1]
        if file_extension not in allowed_extensions:
            return {
                'valid': False,
                'error': f'File type .{file_extension} not allowed',
                'allowed_extensions': allowed_extensions
            }

        # Check file size (50MB limit)
        max_size = 50 * 1024 * 1024
        if file_size > max_size:
            return {
                'valid': False,
                'error': f'File size {file_size} exceeds maximum {max_size}'
            }

        # Check filename for dangerous characters
        dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in filename for char in dangerous_chars):
            return {
                'valid': False,
                'error': 'Filename contains invalid characters'
            }

        return {'valid': True, 'sanitized_filename': self.sanitize_input(filename, 'filename')}

    def validate_query(self, query: str) -> Dict[str, Any]:
        """
        Validate search query.

        Args:
            query: Search query string

        Returns:
            Validation result
        """
        if not query:
            return {'valid': False, 'error': 'Empty query'}

        sanitized_query = self.sanitize_input(query, 'query')

        if len(sanitized_query) < 3:
            return {'valid': False, 'error': 'Query too short (minimum 3 characters)'}

        if len(sanitized_query) > self.max_lengths['query']:
            return {'valid': False, 'error': 'Query too long'}

        return {
            'valid': True,
            'sanitized_query': sanitized_query,
            'original_length': len(query),
            'sanitized_length': len(sanitized_query)
        }


class SecurityMonitor:
    """Security monitoring and event logging."""

    def __init__(self):
        """Initialize security monitor."""
        self.events: List[SecurityEvent] = []
        self.event_counts = defaultdict(int)
        self.blocked_ips: Dict[str, datetime] = {}
        self.lock = threading.Lock()

    def log_event(self, event_type: str, source_ip: str,
                  user_id: Optional[str] = None, details: Dict[str, Any] = None,
                  severity: str = "INFO"):
        """
        Log security event.

        Args:
            event_type: Type of security event
            source_ip: Source IP address
            user_id: User identifier
            details: Additional event details
            severity: Event severity level
        """
        event = SecurityEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            source_ip=source_ip,
            user_id=user_id,
            details=details or {},
            severity=severity
        )

        with self.lock:
            self.events.append(event)
            self.event_counts[event_type] += 1

            # Keep only last 10000 events in memory
            if len(self.events) > 10000:
                self.events = self.events[-10000:]

        # Log to application logger
        log_message = f"Security event: {event_type}"
        if user_id:
            log_message += f" (user: {user_id})"
        if details:
            log_message += f" - {details}"

        context = get_current_context()
        if severity == "CRITICAL":
            error(log_message, security_event=event_type, severity=severity, **context)
        elif severity == "ERROR":
            error(log_message, security_event=event_type, severity=severity, **context)
        elif severity == "WARNING":
            warning(log_message, security_event=event_type, severity=severity, **context)
        else:
            debug(log_message, security_event=event_type, severity=severity, **context)

    def is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is blocked."""
        with self.lock:
            if ip in self.blocked_ips:
                block_expiry = self.blocked_ips[ip]
                if datetime.now() < block_expiry:
                    return True
                else:
                    # Unblock expired
                    del self.blocked_ips[ip]
        return False

    def block_ip(self, ip: str, duration_hours: int = 24):
        """Block IP for specified duration."""
        block_expiry = datetime.now() + timedelta(hours=duration_hours)
        with self.lock:
            self.blocked_ips[ip] = block_expiry

        self.log_event(
            "ip_blocked",
            source_ip=ip,
            details={"duration_hours": duration_hours, "expiry": block_expiry.isoformat()},
            severity="WARNING"
        )

    def get_security_summary(self) -> Dict[str, Any]:
        """Get security monitoring summary."""
        with self.lock:
            recent_events = [
                event for event in self.events
                if event.timestamp > datetime.now() - timedelta(hours=24)
            ]

            return {
                'total_events': len(self.events),
                'recent_events_24h': len(recent_events),
                'event_counts': dict(self.event_counts),
                'blocked_ips': len(self.blocked_ips),
                'critical_events': len([e for e in recent_events if e.severity == "CRITICAL"]),
                'error_events': len([e for e in recent_events if e.severity == "ERROR"])
            }


# Global security components
security_monitor = SecurityMonitor()
input_validator = InputValidator()
rate_limiter = RateLimiter()


def require_auth(f: Callable) -> Callable:
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not FLASK_AVAILABLE:
            return f(*args, **kwargs)

        # Check if user is authenticated
        if not getattr(g, 'user', None) and 'user_id' not in session:
            security_monitor.log_event(
                "unauthorized_access_attempt",
                source_ip=get_remote_address(),
                severity="WARNING"
            )
            abort(401)

        return f(*args, **kwargs)
    return decorated_function


def rate_limit(limit_type: str = 'global', identifier_func: Callable = None):
    """Decorator for rate limiting."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not FLASK_AVAILABLE:
                return f(*args, **kwargs)

            # Get identifier for rate limiting
            if identifier_func:
                identifier = identifier_func()
            else:
                identifier = get_remote_address()

            # Check if IP is blocked
            if security_monitor.is_ip_blocked(identifier):
                security_monitor.log_event(
                    "blocked_ip_access_attempt",
                    source_ip=identifier,
                    severity="WARNING"
                )
                abort(403)

            # Check rate limit
            if not rate_limiter.is_allowed(identifier, limit_type):
                security_monitor.log_event(
                    "rate_limit_exceeded",
                    source_ip=identifier,
                    details={"limit_type": limit_type},
                    severity="WARNING"
                )
                abort(429)  # Too Many Requests

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def validate_json_input(f: Callable) -> Callable:
    """Decorator to validate JSON input."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not FLASK_AVAILABLE or not request.is_json:
            return f(*args, **kwargs)

        try:
            data = request.get_json()
            if data is None:
                security_monitor.log_event(
                    "invalid_json_input",
                    source_ip=get_remote_address(),
                    severity="WARNING"
                )
                abort(400, description="Invalid JSON")

            # Sanitize string inputs
            def sanitize_data(obj):
                if isinstance(obj, str):
                    return input_validator.sanitize_input(obj)
                elif isinstance(obj, dict):
                    return {k: sanitize_data(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [sanitize_data(item) for item in obj]
                else:
                    return obj

            sanitized_data = sanitize_data(data)
            # Add sanitized data to request context
            g.sanitized_json = sanitized_data

        except Exception as e:
            security_monitor.log_event(
                "json_validation_error",
                source_ip=get_remote_address(),
                details={"error": str(e)},
                severity="WARNING"
            )
            abort(400, description="Invalid JSON format")

        return f(*args, **kwargs)
    return decorated_function