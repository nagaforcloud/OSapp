# tests/test_security.py
"""
Security tests for the Onestream RAG application.
"""

import pytest
import time
from unittest.mock import Mock, patch

from app.security import (
    SecurityMonitor, RateLimiter, InputValidator,
    security_monitor, input_validator, rate_limiter
)


class TestSecurityMonitor:
    """Test security monitoring functionality."""

    @pytest.fixture
    def monitor(self):
        """Create a fresh security monitor for each test."""
        return SecurityMonitor()

    def test_log_event_creation(self, monitor):
        """Test security event logging."""
        monitor.log_event(
            event_type="test_event",
            source_ip="127.0.0.1",
            user_id="test_user",
            details={"test": True},
            severity="INFO"
        )

        assert len(monitor.events) == 1
        event = monitor.events[0]
        assert event.event_type == "test_event"
        assert event.source_ip == "127.0.0.1"
        assert event.user_id == "test_user"
        assert event.severity == "INFO"
        assert event.details["test"] is True

    def test_event_counter(self, monitor):
        """Test event counting functionality."""
        for i in range(5):
            monitor.log_event("test_event", "127.0.0.1")

        assert monitor.event_counts["test_event"] == 5

    def test_ip_blocking(self, monitor):
        """Test IP blocking functionality."""
        ip_address = "192.168.1.100"

        # Initially not blocked
        assert not monitor.is_ip_blocked(ip_address)

        # Block IP for 1 hour
        monitor.block_ip(ip_address, duration_hours=1)
        assert monitor.is_ip_blocked(ip_address)

        # Mock time to test expiry
        with patch('app.security.datetime') as mock_datetime:
            # Simulate 2 hours later
            mock_datetime.now.return_value = (
                monitor.blocked_ips[ip_address] +
                pd.Timedelta(hours=2)
            )
            assert not monitor.is_ip_blocked(ip_address)

    def test_security_summary(self, monitor):
        """Test security summary generation."""
        # Add various events
        monitor.log_event("login_attempt", "127.0.0.1", severity="INFO")
        monitor.log_event("login_failed", "127.0.0.1", severity="WARNING")
        monitor.log_event("unauthorized_access", "127.0.0.1", severity="ERROR")
        monitor.log_event("security_breach", "127.0.0.1", severity="CRITICAL")

        summary = monitor.get_security_summary()

        assert summary['total_events'] == 4
        assert summary['critical_events'] == 1
        assert summary['error_events'] == 1
        assert summary['event_counts']['login_attempt'] == 1


class TestRateLimiter:
    """Test rate limiting functionality."""

    @pytest.fixture
    def limiter(self, mock_redis_client):
        """Create rate limiter with mocked Redis."""
        return RateLimiter(redis_client=mock_redis_client)

    def test_default_limits_configuration(self, limiter):
        """Test default rate limit configuration."""
        assert 'global' in limiter.default_limits
        assert 'per_ip' in limiter.default_limits
        assert 'per_user' in limiter.default_limits
        assert 'auth_attempts' in limiter.default_limits

    def test_redis_rate_limiting(self, limiter, mock_redis_client):
        """Test rate limiting using Redis."""
        identifier = "test_user_123"
        limit_type = "per_user"

        # Configure Redis mock to simulate rate limiting
        call_count = 0

        def mock_incr(key):
            nonlocal call_count
            call_count += 1
            return call_count

        def mock_execute():
            return [call_count]

        mock_redis_client.pipeline.return_value.incr.side_effect = mock_incr
        mock_redis_client.pipeline.return_value.execute.return_value = [1]
        mock_redis_client.pipeline.return_value.expire.return_value = True

        # First request should be allowed
        assert limiter.is_allowed(identifier, limit_type)

        # Requests within limit should be allowed
        for _ in range(limiter.default_limits[limit_type]['requests'] - 1):
            assert limiter.is_allowed(identifier, limit_type)

        # Next request should be denied
        mock_redis_client.pipeline.return_value.execute.return_value = [
            limiter.default_limits[limit_type]['requests'] + 1
        ]
        assert not limiter.is_allowed(identifier, limit_type)

    def test_local_rate_limiting(self):
        """Test rate limiting using local memory."""
        limiter = RateLimiter(redis_client=None)
        identifier = "test_ip_127.0.0.1"
        limit_type = "per_ip"

        limit = limiter.default_limits[limit_type]

        # Requests within limit should be allowed
        for _ in range(limit['requests']):
            assert limiter.is_allowed(identifier, limit_type)

        # Next request should be denied
        assert not limiter.is_allowed(identifier, limit_type)

    def test_remaining_requests_calculation(self, limiter, mock_redis_client):
        """Test calculation of remaining requests."""
        identifier = "test_user_456"
        limit_type = "global"

        # Mock Redis to return current count
        mock_redis_client.get.return_value = b"5"
        remaining = limiter.get_remaining_requests(identifier, limit_type)

        expected_remaining = limiter.default_limits[limit_type]['requests'] - 5
        assert remaining == expected_remaining

    def test_rate_limit_key_generation(self, limiter):
        """Test rate limit key generation."""
        identifier = "test_identifier"
        limit_type = "per_user"
        key = limiter._get_key(identifier, limit_type)

        assert key.startswith(f"rate_limit:{limit_type}:")
        assert identifier not in key  # Should be hashed

    def test_different_limit_types(self, limiter):
        """Test different types of rate limits."""
        # Test auth attempts limit (very restrictive)
        assert limiter.is_allowed("user123", "auth_attempts")

        # Test document upload limit
        assert limiter.is_allowed("user123", "document_upload")

        # Test global limit
        assert limiter.is_allowed("user123", "global")


class TestInputValidator:
    """Test input validation functionality."""

    def test_text_sanitization(self):
        """Test text input sanitization."""
        dangerous_input = '<script>alert("xss")</script>Hello <b>world</b>'
        sanitized = input_validator.sanitize_input(dangerous_input, 'text_input')

        assert '<script>' not in sanitized
        assert '<b>' not in sanitized  # Should be HTML encoded
        assert 'Hello' in sanitized

    def test_length_limits(self):
        """Test input length limits."""
        long_text = "a" * 1500  # Exceeds default 1000 limit
        sanitized = input_validator.sanitize_input(long_text, 'query')

        assert len(sanitized) <= 1000

    def test_xss_prevention(self):
        """Test XSS prevention."""
        xss_attempts = [
            '<script>alert("xss")</script>',
            'javascript:alert("xss")',
            '<img src="x" onerror="alert(\'xss\')">',
            '<iframe src="javascript:alert(\'xss\')"></iframe>',
            'eval("alert(\'xss\')")'
        ]

        for xss in xss_attempts:
            sanitized = input_validator.sanitize_input(xss, 'text_input')
            assert 'javascript:' not in sanitized.lower()
            assert '<script>' not in sanitized.lower()
            assert 'eval(' not in sanitized.lower()

    def test_sql_injection_prevention(self):
        """Test SQL injection prevention."""
        sql_injections = [
            "'; DROP TABLE users; --",
            "UNION SELECT * FROM users",
            "' OR '1'='1",
            "'; INSERT INTO users VALUES('hacker', 'password'); --"
        ]

        for injection in sql_injections:
            sanitized = input_validator.sanitize_input(injection, 'query')
            # Should not contain dangerous SQL keywords in uppercase
            assert 'DROP TABLE' not in sanitized.upper()
            assert 'UNION SELECT' not in sanitized.upper()
            assert 'INSERT INTO' not in sanitized.upper()

    def test_file_upload_validation(self):
        """Test file upload validation."""
        # Valid file
        valid_result = input_validator.validate_file_upload(
            filename="document.pdf",
            file_size=1024 * 1024,  # 1MB
            allowed_extensions=['pdf', 'txt', 'docx']
        )
        assert valid_result['valid'] is True

        # Invalid extension
        invalid_ext_result = input_validator.validate_file_upload(
            filename="malicious.exe",
            file_size=1024,
            allowed_extensions=['pdf', 'txt', 'docx']
        )
        assert invalid_ext_result['valid'] is False
        assert 'File type .exe not allowed' in invalid_ext_result['error']

        # File too large
        large_file_result = input_validator.validate_file_upload(
            filename="large.pdf",
            file_size=100 * 1024 * 1024,  # 100MB
            allowed_extensions=['pdf']
        )
        assert large_file_result['valid'] is False
        assert 'exceeds maximum' in large_file_result['error']

        # Dangerous filename
        dangerous_name_result = input_validator.validate_file_upload(
            filename="../../../etc/passwd",
            file_size=1024,
            allowed_extensions=['pdf']
        )
        assert dangerous_name_result['valid'] is False
        assert 'invalid characters' in dangerous_name_result['error']

    def test_query_validation(self):
        """Test search query validation."""
        # Valid query
        valid_result = input_validator.validate_query("What is Onestream?")
        assert valid_result['valid'] is True
        assert 'sanitized_query' in valid_result

        # Empty query
        empty_result = input_validator.validate_query("")
        assert empty_result['valid'] is False
        assert 'Empty query' in empty_result['error']

        # Too short query
        short_result = input_validator.validate_query("Hi")
        assert short_result['valid'] is False
        assert 'too short' in short_result['error']

        # Too long query
        long_query = "What is " * 200  # Very long query
        long_result = input_validator.validate_query(long_query)
        assert long_result['valid'] is False
        assert 'too long' in long_result['error']

    def test_filename_sanitization(self):
        """Test filename sanititization."""
        dangerous_filename = '<script>alert("xss")</script>file.pdf'
        sanitized = input_validator.sanitize_input(dangerous_filename, 'filename')

        assert '<script>' not in sanitized
        assert '.pdf' in sanitized or '.PDF' in sanitized  # Extension should remain

    def test_html_encoding(self):
        """Test HTML character encoding."""
        html_input = 'Hello <b>world</b> & "quotes"'
        sanitized = input_validator.sanitize_input(html_input, 'text_input')

        assert '&lt;b&gt;' in sanitized or '<b>' not in sanitized
        assert '&amp;' in sanitized
        assert '&quot;' in sanitized


@pytest.mark.integration
class TestSecurityIntegration:
    """Integration tests for security components."""

    def test_rate_limiting_with_monitoring(self, limiter, monitor):
        """Test rate limiting with security monitoring."""
        ip_address = "192.168.1.200"

        # Simulate rapid requests that would trigger rate limiting
        for i in range(110):  # More than default 100 limit
            if not limiter.is_allowed(ip_address, "per_ip"):
                monitor.log_event(
                    "rate_limit_exceeded",
                    source_ip=ip_address,
                    details={"request_count": i + 1},
                    severity="WARNING"
                )
                break

        # Verify security event was logged
        rate_limit_events = [
            event for event in monitor.events
            if event.event_type == "rate_limit_exceeded"
        ]
        assert len(rate_limit_events) > 0

    def test_file_upload_security_pipeline(self):
        """Test complete file upload security pipeline."""
        # Test with malicious filename and content
        malicious_filename = "<script>alert('xss')</script>.pdf"
        file_size = 1024

        # First validate filename
        validation_result = input_validator.validate_file_upload(
            filename=malicious_filename,
            file_size=file_size
        )

        # Then sanitize if valid
        if validation_result['valid']:
            sanitized_name = validation_result['sanitized_filename']
            assert '<script>' not in sanitized_name

    def test_multiple_security_checks(self):
        """Test application of multiple security measures."""
        user_input = {
            'query': '<script>alert("xss")</script>What is Onestream?',
            'filename': '../../../etc/passwd',
            'user_id': "'; DROP TABLE users; --"
        }

        # Apply all security checks
        sanitized_query = input_validator.validate_query(user_input['query'])
        file_validation = input_validator.validate_file_upload(
            user_input['filename'], 1024
        )
        sanitized_user_id = input_validator.sanitize_input(user_input['user_id'])

        # Verify all checks work together
        assert not sanitized_query['valid'] or '<script>' not in sanitized_query.get('sanitized_query', '')
        assert not file_validation['valid']
        assert 'DROP TABLE' not in sanitized_user_id.upper()


@pytest.mark.performance
class TestSecurityPerformance:
    """Performance tests for security components."""

    def test_rate_limiter_performance(self, limiter):
        """Test rate limiter performance under load."""
        import time

        start_time = time.time()
        iterations = 1000

        for i in range(iterations):
            limiter.is_allowed(f"user_{i % 100}", "per_user")

        duration = time.time() - start_time
        operations_per_second = iterations / duration

        # Should handle at least 1000 operations per second
        assert operations_per_second > 1000

    def test_input_validator_performance(self):
        """Test input validator performance under load."""
        import time

        inputs = ["test input " + str(i) for i in range(1000)]
        dangerous_inputs = [
            "<script>alert('xss')</script>input " + str(i)
            for i in range(1000)
        ]

        start_time = time.time()

        for input_text in inputs + dangerous_inputs:
            input_validator.sanitize_input(input_text, 'text_input')

        duration = time.time() - start_time
        operations_per_second = len(inputs + dangerous_inputs) / duration

        # Should handle at least 5000 sanitizations per second
        assert operations_per_second > 5000

    def test_security_monitor_performance(self, monitor):
        """Test security monitor performance under load."""
        import time

        start_time = time.time()
        iterations = 1000

        for i in range(iterations):
            monitor.log_event(
                f"event_type_{i % 10}",
                f"192.168.1.{i % 255}",
                user_id=f"user_{i % 100}",
                details={"iteration": i},
                severity="INFO"
            )

        duration = time.time() - start_time
        operations_per_second = iterations / duration

        # Should handle at least 2000 events per second
        assert operations_per_second > 2000

        # Verify memory usage doesn't grow unbounded
        assert len(monitor.events) <= 10000  # Should be limited


@pytest.mark.security
class TestSecurityEdgeCases:
    """Test security edge cases and boundary conditions."""

    def test_unicode_security(self):
        """Test security with Unicode characters."""
        unicode_inputs = [
            "Hello 世界",
            "🔥💯✨ emoji test",
            "Привет мир",  # Cyrillic
            "مرحبا بالعالم",  # Arabic
            "🏴‍☠️ test with unusual Unicode",
            "Test\x00\x01\x02 with control characters"
        ]

        for input_text in unicode_inputs:
            # Should not raise exceptions
            sanitized = input_validator.sanitize_input(input_text, 'text_input')
            assert isinstance(sanitized, str)

            # Should handle query validation
            query_result = input_validator.validate_query(input_text)
            assert isinstance(query_result, dict)

    def test_extreme_input_sizes(self):
        """Test security with extremely large inputs."""
        import sys

        # Very large input (1MB)
        large_input = "a" * (1024 * 1024)

        start_time = time.time()
        sanitized = input_validator.sanitize_input(large_input, 'text_input')
        duration = time.time() - start_time

        # Should handle large inputs quickly (under 1 second)
        assert duration < 1.0
        assert len(sanitized) <= input_validator.max_lengths['text_input']

    def test_concurrent_access(self):
        """Test thread safety of security components."""
        import threading
        import time

        results = []
        errors = []

        def worker():
            try:
                for i in range(100):
                    limiter.is_allowed(f"thread_{threading.current_thread().ident}", "per_user")
                    input_validator.sanitize_input(f"test {i}", 'text_input')
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should not have any threading errors
        assert len(errors) == 0