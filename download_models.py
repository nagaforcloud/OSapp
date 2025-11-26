#!/usr/bin/env python3
"""
Script to download recommended 4B parameter models for local LLM usage.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def check_wget():
    """Check if wget is available."""
    try:
        subprocess.run(["wget", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_curl():
    """Check if curl is available."""
    try:
        subprocess.run(["curl", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def download_file(url, filename, downloader="wget"):
    """Download a file using wget or curl."""
    print(f"Downloading {filename}...")
    
    if downloader == "wget":
        cmd = ["wget", "-O", filename, url]
    else:  # curl
        cmd = ["curl", "-L", "-o", filename, url]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Successfully downloaded {filename}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to download {filename}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Download recommended 4B parameter models for local LLM usage")
    parser.add_argument("--models-dir", default="models", help="Directory to download models to (default: models)")
    parser.add_argument("--skip-llm", action="store_true", help="Skip downloading LLM model")
    parser.add_argument("--skip-embedding", action="store_true", help="Skip downloading embedding model")
    
    args = parser.parse_args()
    
    # Create models directory if it doesn't exist
    models_dir = Path(args.models_dir)
    models_dir.mkdir(exist_ok=True)
    
    # Check for download tools
    if check_wget():
        downloader = "wget"
    elif check_curl():
        downloader = "curl"
    else:
        print("Error: Neither wget nor curl is available. Please install one of them.")
        return 1
    
    success = True
    
    # Download LLM model if not skipped
    if not args.skip_llm:
        llm_url = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
        llm_filename = models_dir / "mistral-7b-instruct-v0.2.Q4_K_M.gguf"
        
        if llm_filename.exists():
            print(f"LLM model already exists: {llm_filename}")
        else:
            if not download_file(llm_url, str(llm_filename), downloader):
                success = False
    
    # Download embedding model if not skipped
    if not args.skip_embedding:
        embedding_url = "https://huggingface.co/CompendiumLabs/bge-small-en-v1.5-gguf/resolve/main/bge-small-en-v1.5-q4_k_m.gguf"
        embedding_filename = models_dir / "bge-small-en-v1.5-q4_k_m.gguf"
        
        if embedding_filename.exists():
            print(f"Embedding model already exists: {embedding_filename}")
        else:
            if not download_file(embedding_url, str(embedding_filename), downloader):
                success = False
    
    if success:
        print("\n✅ All models downloaded successfully!")
        print(f"\nUpdate your .env file with these paths:")
        print(f"LOCAL_LLM_MODEL_PATH={models_dir}/mistral-7b-instruct-v0.2.Q4_K_M.gguf")
        print(f"LOCAL_EMBEDDING_MODEL_PATH={models_dir}/bge-small-en-v1.5-q4_k_m.gguf")
        return 0
    else:
        print("\n❌ Some downloads failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
