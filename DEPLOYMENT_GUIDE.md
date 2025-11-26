# 📋 GitHub Repository Setup Guide

This document provides step-by-step instructions for creating and uploading the Onestream RAG Assistant to GitHub.

## 🎯 Repository Creation Steps

### 1. Create New GitHub Repository

1. **Sign in to GitHub** at https://github.com
2. **Click the "+" icon** in the top right corner
3. **Select "New repository"**
4. **Repository settings:**
   - **Repository name**: `onestream-rag-assistant`
   - **Description**: `🤖 A comprehensive RAG system for querying Onestream documentation with advanced AI capabilities`
   - **Visibility**: Choose Public or Private
   - **Do NOT initialize** with README, .gitignore, or license (we have these already)
5. **Click "Create repository"**

### 2. Prepare Local Repository

**Navigate to your project directory:**
```bash
cd /Users/nagashankar/pythonScripts/OSApp
```

**Initialize Git repository:**
```bash
git init
```

**Create and switch to version1 branch:**
```bash
git checkout -b version1
```

### 3. Configure Git (if not already configured)

```bash
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### 4. Add Remote Repository

```bash
# Replace with your actual GitHub username
git remote add origin https://github.com/yourusername/onestream-rag-assistant.git
```

### 5. Add Files and Make Initial Commit

```bash
# Add all files (respecting .gitignore)
git add .

# Make initial commit
git commit -m "🚀 Initial commit: Onestream RAG Assistant v1.0

✨ Features:
- Multi-model AI support (Local LLMs + Cloud APIs)
- Comprehensive document processing (PDF, Word, Excel, PowerPoint)
- Advanced semantic search with Qdrant vector database
- Multiple user interfaces (Streamlit, Flask REST API, Gradio)
- Modern responsive UI with dark mode support
- Docker deployment ready
- Enhanced security and authentication

🔧 Tech Stack:
- Python 3.11+, Flask, Streamlit, Gradio
- LangChain, Qdrant, LLaMA.cpp
- PyPDF2, python-docx, openpyxl, python-pptx
- Docker, Docker Compose

📦 Ready for production deployment with comprehensive documentation
"
```

### 6. Push to GitHub

```bash
# Push to the version1 branch
git push -u origin version1
```

### 7. Switch to Main Branch (Optional but Recommended)

If you want to make version1 your main branch:

```bash
# Switch to main branch (create if doesn't exist)
git checkout main

# Merge version1 into main
git merge version1

# Push main branch
git push -u origin main

# Set main as default branch in GitHub repository settings
```

## 📁 Repository Structure After Upload

```
onestream-rag-assistant/
├── .gitignore                    # Comprehensive Python .gitignore
├── LICENSE                       # MIT License
├── README.md                     # Comprehensive documentation
├── DEPLOYMENT_GUIDE.md          # This guide
├── requirements.txt              # Python dependencies with versions
├── pyproject.toml               # Project configuration
├── docker-compose.yml           # Docker orchestration
├── Dockerfile                   # Docker image configuration
├── app.py                       # Main Flask application
├── streamlit_app.py             # Streamlit interface
├── gradio_app.py                # Gradio interface
├── .env.example                 # Environment variables template
└── app/                         # Application modules
    ├── adapters/                 # AI model adapters
    ├── managers/                 # System managers
    ├── utils/                    # Utility functions
    └── ...                      # Other application files
```

## 🔐 Security Checklist

Before pushing, ensure these files are properly handled:

- ✅ `.env` - Contains API keys (already in .gitignore)
- ✅ `.streamlit/secrets.toml` - Contains secrets (already in .gitignore)
- ✅ Model files (*.gguf) - Large files handled by .gitignore
- ✅ Log files - Temporary files excluded
- ✅ Vector database files - Excluded from version control

## 🎯 GitHub Repository Features

### README.md Highlights

- **Project overview** with clear feature list
- **Installation instructions** with step-by-step guide
- **Configuration guide** for environment variables
- **Usage examples** for all interfaces
- **Architecture diagram** and project structure
- **Docker deployment** instructions
- **Troubleshooting guide**

### License

- **MIT License** for maximum flexibility
- Allows commercial use, modification, distribution
- Includes copyright notice and warranty disclaimer

### Git History

The initial commit includes:
- Comprehensive commit message with emojis and clear description
- All source files properly organized
- Documentation files
- Configuration files
- Docker setup files

## 🚀 Post-Upload Actions

1. **Verify Repository**: Check all files are uploaded correctly
2. **Set up GitHub Pages** (optional): For hosting documentation
3. **Add Topics**: Add relevant tags like `rag`, `ai`, `python`, `streamlit`
4. **Enable Issues** and **Discussions** for community engagement
5. **Set up GitHub Actions** for CI/CD (optional)
6. **Add Contributors** section as team members join

## 🔄 Workflow for Future Changes

```bash
# Make changes to your code
# Stage and commit changes
git add .
git commit -m "feat: add new feature description"

# Push to GitHub
git push origin version1

# For major releases, create tags
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

## 📝 Commit Message Guidelines

- Use **conventional commit format**: `type: description`
- **Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- **Examples**:
  - `feat: add real-time collaboration features`
  - `fix: resolve memory leak in document processing`
  - `docs: update API documentation`
  - `chore: update dependencies`

## 🎉 Success!

Your Onestream RAG Assistant is now on GitHub!

**Repository URL**: `https://github.com/yourusername/onestream-rag-assistant`

**Next Steps**:
1. Share with team members
2. Set up automated testing
3. Configure deployment pipelines
4. Start gathering feedback from users