# tests/conftest.py
"""
Pytest configuration and shared fixtures for testing the Onestream RAG application.
"""

import pytest
import tempfile
import shutil
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app import create_app
from app.config import Config
from app.cache_manager import CacheManager
from app.security import SecurityMonitor, RateLimiter
from app.enhanced_logger import EnhancedLogger


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_config():
    """Create test configuration."""
    return {
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'QDRANT_HOST': 'localhost',
        'QDRANT_PORT': 6333,
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': 6379,
        'LOG_LEVEL': 'DEBUG',
        'CACHE_TTL': 60,
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
    }


@pytest.fixture
def app(test_config):
    """Create Flask application for testing."""
    app = create_app()
    app.config.update(test_config)

    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create CLI test runner."""
    return app.test_cli_runner()


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for testing."""
    mock_client = Mock()
    mock_client.get_collections.return_value = Mock()
    mock_client.search.return_value = []
    mock_client.upsert.return_value = Mock()
    return mock_client


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock_client = Mock()
    mock_client.ping.return_value = True
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    mock_client.setex.return_value = True
    mock_client.delete.return_value = 1
    return mock_client


@pytest.fixture
def cache_manager(mock_redis_client):
    """Create cache manager with mocked Redis."""
    return CacheManager(redis_url="redis://localhost:6379/0")


@pytest.fixture
def security_monitor():
    """Create security monitor for testing."""
    return SecurityMonitor()


@pytest.fixture
def rate_limiter(mock_redis_client):
    """Create rate limiter with mocked Redis."""
    return RateLimiter(redis_client=mock_redis_client)


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    return EnhancedLogger(log_file="test.log")


@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    return [
        {
            'id': 'doc1',
            'content': 'This is a test document about Onestream.',
            'metadata': {'source': 'test', 'type': 'pdf'},
            'timestamp': '2024-01-01T00:00:00Z'
        },
        {
            'id': 'doc2',
            'content': 'Another document with different content.',
            'metadata': {'source': 'test', 'type': 'docx'},
            'timestamp': '2024-01-02T00:00:00Z'
        }
    ]


@pytest.fixture
def sample_queries():
    """Sample queries for testing."""
    return [
        'What is Onestream?',
        'How do I create a business rule?',
        'What are the system requirements?',
        'How to configure the application?'
    ]


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return {
        'response': 'This is a test response from the language model.',
        'model': 'test-model',
        'usage': {
            'prompt_tokens': 100,
            'completion_tokens': 50,
            'total_tokens': 150
        },
        'timestamp': '2024-01-01T12:00:00Z'
    }


@pytest.fixture
def mock_user_data():
    """Mock user data for authentication testing."""
    return {
        'user_id': 'test-user-123',
        'username': 'testuser',
        'email': 'test@example.com',
        'role': 'user',
        'session_id': 'test-session-456',
        'permissions': ['read', 'write']
    }


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv('TESTING', 'True')
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key')
    monkeypatch.setenv('QDRANT_HOST', 'localhost')
    monkeypatch.setenv('QDRANT_PORT', '6333')
    monkeypatch.setenv('REDIS_HOST', 'localhost')
    monkeypatch.setenv('REDIS_PORT', '6379')
    monkeypatch.setenv('LOG_LEVEL', 'DEBUG')


@pytest.fixture
def sample_pdf_file(temp_dir):
    """Create a sample PDF file for testing."""
    import pdfkit

    html_content = """
    <html>
    <head><title>Test Document</title></head>
    <body>
        <h1>Test PDF Document</h1>
        <p>This is a test document created for testing purposes.</p>
        <p>It contains multiple paragraphs and headings.</p>
        <h2>Section 1</h2>
        <p>Some content in section 1.</p>
        <h2>Section 2</h2>
        <p>Some content in section 2.</p>
    </body>
    </html>
    """

    pdf_path = os.path.join(temp_dir, 'test_document.pdf')
    try:
        pdfkit.from_string(html_content, pdf_path)
    except Exception:
        # If pdfkit is not available, create a simple text file
        with open(pdf_path, 'w') as f:
            f.write("Test document content for testing purposes.")

    return pdf_path


@pytest.fixture
def sample_text_file(temp_dir):
    """Create a sample text file for testing."""
    text_path = os.path.join(temp_dir, 'test_document.txt')
    with open(text_path, 'w') as f:
        f.write("""
        Test Text Document

        This is a sample text document created for testing purposes.
        It contains multiple paragraphs and headings.

        Section 1: Introduction
        Some content in section 1.

        Section 2: Main Content
        Some content in section 2.

        Section 3: Conclusion
        Some content in section 3.
        """)

    return text_path


@pytest.fixture
def sample_markdown_file(temp_dir):
    """Create a sample Markdown file for testing."""
    md_path = os.path.join(temp_dir, 'test_document.md')
    with open(md_path, 'w') as f:
        f.write("""
# Test Markdown Document

This is a sample Markdown document created for testing purposes.
It contains multiple paragraphs and headings.

## Section 1: Introduction

Some content in section 1.

## Section 2: Main Content

Some content in section 2.

### Subsection 2.1

More detailed content here.

## Section 3: Conclusion

Some content in section 3.

- Bullet point 1
- Bullet point 2
- Bullet point 3

1. Numbered item 1
2. Numbered item 2
3. Numbered item 3

**Bold text** and *italic text*.
""")

    return md_path


@pytest.fixture
def mock_file_uploads(temp_dir):
    """Create mock file uploads for testing."""
    files = {}

    # Create various file types
    files['pdf'] = sample_pdf_file(temp_dir)
    files['txt'] = sample_text_file(temp_dir)
    files['md'] = sample_markdown_file(temp_dir)

    return files


@pytest.fixture
def mock_embeddings():
    """Mock embedding vectors for testing."""
    import numpy as np

    return [
        np.random.rand(384).tolist() for _ in range(5)  # 5 sample embeddings
    ]


@pytest.fixture
def mock_search_results():
    """Mock search results for testing."""
    return [
        {
            'id': 'result1',
            'score': 0.95,
            'payload': {
                'content': 'Relevant content for query result 1',
                'source': 'test_document.pdf',
                'page': 1
            }
        },
        {
            'id': 'result2',
            'score': 0.87,
            'payload': {
                'content': 'Relevant content for query result 2',
                'source': 'test_document.docx',
                'page': 2
            }
        }
    ]


@pytest.fixture
def mock_chat_history():
    """Mock chat history for testing."""
    return [
        {
            'role': 'user',
            'content': 'What is Onestream?',
            'timestamp': '2024-01-01T12:00:00Z',
            'session_id': 'test-session-456'
        },
        {
            'role': 'assistant',
            'content': 'Onestream is a financial planning and analysis platform...',
            'timestamp': '2024-01-01T12:00:05Z',
            'session_id': 'test-session-456'
        }
    ]


@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Cleanup temporary files after tests."""
    yield
    # Any additional cleanup can be added here


# Custom markers for different test categories
pytest_plugins = []

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security-related"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance-related"
    )


@pytest.fixture
def authenticated_client(client, mock_user_data):
    """Create an authenticated test client."""
    with client.session_transaction() as sess:
        sess['user_id'] = mock_user_data['user_id']
        sess['username'] = mock_user_data['username']
        sess['session_id'] = mock_user_data['session_id']

    return client


# Helper functions for tests
def create_test_file(content: str, filename: str, temp_dir: str) -> str:
    """Create a test file with given content."""
    file_path = os.path.join(temp_dir, filename)
    with open(file_path, 'w') as f:
        f.write(content)
    return file_path


def assert_valid_response(response, status_code=200):
    """Assert response has valid structure."""
    assert response.status_code == status_code
    assert response.headers.get('Content-Type') is not None
    return response


def assert_valid_json(response):
    """Assert response contains valid JSON."""
    assert response.status_code in [200, 201]
    assert response.headers.get('Content-Type') == 'application/json'
    return response.get_json()


def mock_streamlit_run():
    """Mock Streamlit run function for testing."""
    with patch('streamlit.run') as mock_run:
        mock_run.return_value = None
        yield mock_run