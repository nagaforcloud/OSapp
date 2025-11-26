# 🤖 Onestream RAG Assistant

A comprehensive Retrieval-Augmented Generation (RAG) system for querying Onestream documentation with advanced AI capabilities, multiple model support, and intuitive web interfaces.

## ✨ Features

- 🔍 **Multi-Model Support**: Local LLMs via LLaMA.cpp + Cloud APIs (DeepSeek, MistralAI, OpenAI)
- 📚 **Comprehensive Document Processing**: PDF, Word, Excel, PowerPoint, Markdown, and more
- 🎯 **Advanced Search**: Semantic vector search with Qdrant database
- 🌐 **Multiple Interfaces**: Streamlit, Flask REST API, and Gradio UI options
- 🧠 **Intelligent Querying**: Context-aware responses with source citations
- ⚡ **Local Processing**: Offline capable with privacy-focused local models
- 🐳 **Docker Ready**: Complete containerization support
- 🔐 **Enhanced Security**: Role-based authentication with session management
- 📎 **Automated Document Ingestion**: Download from OneStream docs and community forums
- 📤 **Export Capabilities**: Chat history to Excel/PDF formats
- 🎨 **Modern UI/UX**: Professional responsive design with dark mode support
- 🛡️ **Robust Error Handling**: Comprehensive retry mechanisms and validation

## 🏗️ Architecture

```
📥 Document Processing
    ├── PDF (PyPDF2)
    ├── Word (python-docx)
    ├── Excel (openpyxl)
    ├── PowerPoint (python-pptx)
    ├── Markdown (Unstructured)
    └── Text Files

🧠 AI Models
    ├── Local: Mistral 7B Instruct (GGUF)
    ├── Local: BGE Small v1.5 Embeddings
    ├── Cloud: DeepSeek API
    ├── Cloud: MistralAI API
    └── Cloud: OpenAI Compatible APIs

🔍 Search & Retrieval
    ├── Qdrant Vector Database
    ├── LangChain Text Splitters
    └── Semantic Search

🌐 User Interfaces
    ├── Streamlit (Primary)
    ├── Flask REST API
    └── Gradio ML Interface
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker (optional, for Qdrant)
- API keys for cloud models (optional)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/onestream-rag-assistant.git
cd onestream-rag-assistant
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Usage

#### Option 1: Streamlit Interface (Recommended)
```bash
streamlit run app/streamlit_app.py --server.port 8501
```
Access at: `http://localhost:8501`

#### Option 2: Flask REST API
```bash
python app.py
```
API endpoints at: `http://localhost:5000`

#### Option 3: Gradio Interface
```bash
python gradio_app.py
```
Access at: `http://localhost:7860`

## 📋 Environment Configuration

Create a `.env` file with the following variables:

```env
# Local Model Configuration
LOCAL_LLM_MODEL_PATH=./models/mistral-7b-instruct.gguf
LOCAL_EMBEDDING_MODEL_PATH=./models/bge-small-v1.5.gguf

# Cloud API Keys (Optional)
DEEPSEEK_API_KEY=your_deepseek_api_key
MISTRAL_API_KEY=your_mistral_api_key
OPENAI_API_KEY=your_openai_api_key
QWEN_CODER_API_KEY=your_qwen_api_key

# Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Application
LOG_LEVEL=INFO
MAX_TOKENS=2048
TEMPERATURE=0.7
ADMIN_PASSWORD=admin
```

## 🔑 API Key Configuration

To use the application with cloud AI models, you need to obtain API keys:

1. **Mistral AI API Key** (required for Mistral mode):
   - Sign up at https://console.mistral.ai/
   - Generate an API key
   - Add it to your `.env` file as `MISTRAL_API_KEY=your_actual_key_here`

2. **DeepSeek API Key** (required for DeepSeek mode):
   - Sign up at https://platform.deepseek.com/
   - Generate an API key
   - Add it to your `.env` file as `DEEPSEEK_API_KEY=your_actual_key_here`

3. **Qwen Coder Plus API Key** (required for Qwen mode):
   - Sign up at Alibaba Cloud DashScope (https://dashscope.console.aliyun.com/)
   - Generate an API key
   - Add it to your `.env` file as `QWEN_CODER_API_KEY=your_actual_key_here`

4. **LangChain API Key** (optional but recommended):
   - Sign up at https://smith.langchain.com/
   - Generate an API key
   - Add it to your `.env` file as `LANGCHAIN_API_KEY=your_actual_key_here`

### Local LLM Option

You can use local LLMs without API keys (this is the default):
1. Download a GGUF model file (e.g., from Hugging Face)
2. Set `LOCAL_LLM_MODEL_PATH` in your `.env` file to point to your model
3. In the application UI, ensure "Local" LLM type is selected

## 📁 Project Structure

```
onestream-rag-assistant/
├── 📄 app.py                    # Main Flask application
├── 📄 streamlit_app.py          # Streamlit interface
├── 📄 gradio_app.py             # Gradio interface
├── 📁 app/                      # Application modules
│   ├── __init__.py
│   ├── rag.py                   # RAG system implementation
│   ├── flask_rag_app.py         # Flask routes
│   ├── adapters/                # AI model adapters
│   │   ├── __init__.py
│   │   ├── base_adapter.py      # Base adapter interface
│   │   ├── deepseek_adapter.py  # DeepSeek API adapter
│   │   ├── llamacpp_adapter.py  # LLaMA.cpp local adapter
│   │   ├── mistral_adapter.py   # MistralAI API adapter
│   │   └── qwen_adapter.py      # Qwen API adapter
│   ├── managers/                # System managers
│   │   ├── __init__.py
│   │   ├── document_manager.py  # Document processing
│   │   ├── vector_store_manager.py # Vector database
│   │   └── config_manager.py    # Configuration management
│   └── utils/                   # Utility functions
│       ├── __init__.py
│       ├── error_handlers.py    # Error handling
│       ├── validation.py        # Input validation
│       └── logger.py            # Logging configuration
├── 📁 models/                   # AI model storage
├── 📁 data/                     # Data storage
│   └── documents/               # Document repository
├── 📁 logs/                     # Application logs
├── 📄 requirements.txt          # Python dependencies
├── 📄 .env.example              # Environment template
├── 📄 docker-compose.yml        # Docker configuration
└── 📄 README.md                 # This file
```

## 🧠 Local LLM Support

The application supports running local LLMs using llama.cpp, allowing you to run models on your machine without API costs:

### Recommended Models

For optimal performance with a balance of quality and resource usage, we recommend these models:

1. **LLM Model**:
   - `Mistral-7B-Instruct-v0.2-Q4_K_M.gguf` (4.13B parameters)
   - Download from: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF

2. **Embedding Model** (optional, can use the same model):
   - `bge-small-en-v1.5-q4_k_m.gguf` (774M parameters)
   - Download from: https://huggingface.co/CompendiumLabs/bge-small-en-v1.5-gguf

### Setup Instructions

1. Create a directory for your models:
   ```bash
   mkdir -p models
   ```

2. Download the recommended models using the provided script:
   ```bash
   python download_models.py
   ```

   Or manually download the models:
   ```bash
   # Download the LLM model
   wget -O models/mistral-7b-instruct-v0.2.Q4_K_M.gguf https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf

   # Download the embedding model
   wget -O models/bge-small-en-v1.5-q4_k_m.gguf https://huggingface.co/CompendiumLabs/bge-small-en-v1.5-gguf/resolve/main/bge-small-en-v1.5-q4_k_m.gguf
   ```

3. Update your `.env` file:
   ```bash
   LOCAL_LLM_MODEL_PATH=models/mistral-7b-instruct-v0.2.Q4_K_M.gguf
   LOCAL_EMBEDDING_MODEL_PATH=models/bge-small-en-v1.5-q4_k_m.gguf
   ```

### System Requirements

For running local models:

- **RAM**: Minimum 8GB, recommended 16GB or more
- **CPU**: Multi-core processor (4+ cores recommended)
- **Storage**: At least 5GB free space for model files
- **OS**: Windows, macOS, or Linux

## 🐳 Docker Deployment

### Quick Start with Docker

```bash
# Clone and build
git clone https://github.com/yourusername/onestream-rag-assistant.git
cd onestream-rag-assistant
docker-compose up --build
```

### Docker Compose Configuration

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8501:8501"
    environment:
      - QDRANT_HOST=qdrant
    depends_on:
      - qdrant

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  qdrant_data:
```

## 📎 Document Processing

### Supported Formats

- **PDF**: `.pdf` files using PyPDF2
- **Microsoft Word**: `.docx` files using python-docx
- **Microsoft Excel**: `.xlsx` files using openpyxl
- **Microsoft PowerPoint**: `.pptx` files using python-pptx
- **Markdown**: `.md` files
- **Plain Text**: `.txt` files

### Adding Documents

1. **Via Streamlit Interface:**
   - Use the document upload sidebar
   - Supported formats are automatically processed

2. **Manual Placement:**
   ```bash
   # Copy documents to the data directory
   cp your-document.pdf data/documents/
   ```

3. **PDF Download Feature:**
   - Automatically download from OneStream documentation
   - Scrape community forum discussions
   - Convert web content to PDF format

## 🔧 Troubleshooting

If you encounter import errors with Qdrant, try:
```bash
pip install qdrant-client
```

The application now uses `langchain_community.vectorstores.Qdrant` instead of the deprecated `langchain_qdrant` package.

## 🎨 Modern UI/UX

The application features a completely modernized user interface with professional styling and improved usability:

### Design Features
- **Professional Color Scheme**: Corporate blue/gray palette with accent colors
- **Card-Based Layout**: Organized content sections with subtle shadows and rounded corners
- **Responsive Design**: Adapts to different screen sizes
- **Enhanced Sidebar**: Structured navigation with expandable sections
- **Custom Components**: Styled buttons, status indicators, and metric cards
- **Dark Mode Support**: Automatic theme switching based on system preferences

### UI Components
- **Modern Header**: With application title and description
- **Status Indicators**: Visual feedback for system status
- **Styled Buttons**: With hover effects and color variations
- **Expandable Sections**: Organized settings in collapsible cards
- **Metric Displays**: Enhanced data visualization
- **Professional Footer**: With version information

### Usability Improvements
- **Clear Navigation**: Structured sidebar with logical grouping
- **Visual Feedback**: Loading indicators and status messages
- **Consistent Styling**: Unified design language throughout the application
- **Accessibility**: Proper contrast and readable typography

## 🤖 Local LLM Support

The application now supports running local LLMs using llama.cpp, allowing you to run models on your machine without API keys:

### Recommended 4B Parameter Models

For optimal performance with a balance of quality and resource usage, we recommend these 4B parameter models:

1. **LLM Model**: 
   - `Mistral-7B-Instruct-v0.2-Q4_K_M.gguf` (4.13B parameters)
   - Download from: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF

2. **Embedding Model** (optional, can use the same model):
   - `bge-small-en-v1.5-q4_k_m.gguf` (774M parameters)
   - Download from: https://huggingface.co/CompendiumLabs/bge-small-en-v1.5-gguf

### Setup Instructions

1. Create a directory for your models:
   ```bash
   mkdir -p models
   ```

2. Download the recommended models using the provided script:
   ```bash
   python download_models.py
   ```

   Or manually download the models:
   ```bash
   # Download the LLM model
   wget -O models/mistral-7b-instruct-v0.2.Q4_K_M.gguf https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf
   
   # Download the embedding model
   wget -O models/bge-small-en-v1.5-q4_k_m.gguf https://huggingface.co/CompendiumLabs/bge-small-en-v1.5-gguf/resolve/main/bge-small-en-v1.5-q4_k_m.gguf
   ```

3. Update your `.env` file:
   ```bash
   LOCAL_LLM_MODEL_PATH=models/mistral-7b-instruct-v0.2.Q4_K_M.gguf
   LOCAL_EMBEDDING_MODEL_PATH=models/bge-small-en-v1.5-q4_k_m.gguf
   ```

4. In the application UI, ensure "Local" LLM type is selected

### System Requirements

For running the recommended 4B parameter models:

- **RAM**: Minimum 8GB, recommended 16GB or more
- **CPU**: Multi-core processor (4+ cores recommended)
- **Storage**: At least 5GB free space for model files
- **OS**: Windows, macOS, or Linux

The models will automatically use available CPU cores for processing. You can adjust the context size and other parameters in the application to balance performance and resource usage.

### Key Benefits

- **Privacy**: No data leaves your machine
- **Cost**: No API costs
- **Customization**: Use any compatible model
- **Offline**: Works without internet connection

### Requirements

1. **GGUF Model Files**: Download compatible GGUF model files (e.g., Llama, Mistral, etc.)
2. **llama-cpp-python**: Installed automatically with requirements.txt

### Supported Models
- Llama 2 / Llama 3 family
- Mistral family
- Any model converted to GGUF format

### Configuration
1. Set `LOCAL_LLM_MODEL_PATH` in your `.env` file to point to your GGUF model
2. Optionally set `LOCAL_EMBEDDING_MODEL_PATH` for a separate embedding model
3. In the UI, switch from "Mistral" to "Local" LLM type
4. Adjust advanced parameters as needed (temperature, context size, etc.)

### Key Benefits

- **Privacy**: No data leaves your machine
- **Cost**: No API costs
- **Customization**: Use any compatible model
- **Offline**: Works without internet connection

## 📎 PDF Download Functionality

The application includes built-in functionality to automatically download OneStream documentation PDFs:

1. **Official Documentation**: Download PDFs from the official OneStream documentation site
2. **Community Forums**: Scrape and convert community forum threads to PDFs

### Scraping Modes

- **Basic Mode**: Standard scraping of visible threads. Faster execution with good coverage.
- **Comprehensive Mode**: Enhanced scraping with:
  - Pagination support to capture all pages in categories
  - Discovery of all available categories automatically
  - Multiple CSS selectors for better content extraction
  - Retry mechanisms for failed requests
  - Rate limiting to avoid server blocking
  - Better handling of different forum layouts
  - Support for scraping specific thread URLs

### Enhanced Features

The enhanced community scraper now supports:
- Scraping specific thread URLs (e.g., `https://community.onestreamsoftware.com/discussions/Rules/transformation-rule-for-a-specific-entity/21396`)
- Better handling of different URL formats in the community forum
- Improved content extraction with multiple fallback selectors
- Duplicate detection to avoid saving the same content multiple times
- Comprehensive HTML formatting with styling for better readability

### Authentication Requirement

Note: The OneStream community forum requires authentication to access most discussions. 
The scraper may encounter "Access denied" errors when trying to scrape protected content.
To scrape private discussions, you may need to:
1. Log in to the community forum in your browser
2. Obtain valid session cookies
3. Configure the scraper with appropriate authentication headers

For public discussions that don't require authentication, the scraper should work without additional configuration.

To use this feature:
1. Expand the "Download PDFs" section in the sidebar
2. Click "Download Official PDFs" to download documentation
3. Choose scraping mode (Basic or Comprehensive)
4. Optionally enter a specific thread URL to scrape
5. Click "Scrape Community Threads" to convert forum discussions to PDFs
6. Rebuild the index to include newly downloaded documents

## 🛡️ Security Features

- Password-based authentication with account lockout after failed attempts
- Session timeout management
- Input validation and sanitization
- Secure API key handling
- Structured logging with user context tracking

## 🧪 Robustness Features

- Comprehensive error handling throughout the application
- Retry mechanisms for API calls with exponential backoff
- Health checks for monitoring system status
- Proper resource cleanup and context management
- Type hints and documentation for code maintainability
