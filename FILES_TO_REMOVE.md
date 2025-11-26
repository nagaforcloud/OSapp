# Files and Folders to Remove from Onestream Project

This document lists files and folders that are not relevant or unused in the onestream folder and should be removed for better project organization and security.

## Files to Remove

### 1. Security Risk Files
- `app/key.py` - Contains hardcoded API keys which is a serious security risk. The application should use `app/keys.py` which properly loads keys from environment variables.
- `app/test.py` - Contains hardcoded API keys and appears to be a test file that should not be in production code.

### 2. Obsolete/Archived Files
- `archieve/rag_v1.py` - Old version of the RAG implementation, superseded by current implementation in `app/streamlit_app.py`
- `archieve/rag_v2.py` - Another old version of the RAG implementation, superseded by current implementation

### 3. Unused Files
- `.env` - This appears to be a copy of `.env.example` with placeholder values. The actual environment configuration should be in a properly secured `.env` file that is not committed to version control.

## Folders to Remove

### 1. Empty or Unused Directories
- `osenv/` - Appears to be an empty or unused directory
- `data/documents/community_html/` - Empty directory, community HTML files are stored in `downloaded_pdfs_from_search/community_html/`

## Files to Update/Secure

### 1. Configuration Files
- `.streamlit/secrets.toml` - Should be added to `.gitignore` to prevent accidental commit of sensitive information
- `.env` - Should be added to `.gitignore` and users should create their own from `.env.example`

## Recommendations

1. **Remove the identified files** to improve security and reduce clutter
2. **Update .gitignore** to prevent accidental commit of sensitive files
3. **Use only app/keys.py** for API key management, which properly uses environment variables
4. **Remove the archive folder** as the current implementation in app/streamlit_app.py is more comprehensive
5. **Clean up empty directories** that are not being used

## Command to Remove Files (Linux/Mac)
```bash
# Remove security risk files
rm app/key.py
rm app/test.py

# Remove archived files
rm archieve/rag_v1.py
rm archieve/rag_v2.py

# Remove empty directories
rmdir osenv/
rmdir data/documents/community_html/

# Note: The .env file should be kept but added to .gitignore
```

## Files to Add to .gitignore
```
.env
.streamlit/secrets.toml
