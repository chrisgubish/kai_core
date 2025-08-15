#!/usr/bin/env python3
"""
Development startup script for Kai Chat Application
Run this to start the backend server with proper CORS and debugging enabled.
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def main():
    print("Starting Kai Chat Backend Server...")
    print("Project root:", project_root)
    
    # Check for required environment variables
    env_file = project_root / ".env"
    if not env_file.exists():
        print("No .env file found. Creating a basic one...")
        with open(env_file, "w") as f:
            f.write("SECRET_KEY=your-super-secret-key-change-in-production\n")
            f.write("HF_TOKEN=your-huggingface-token-here\n")
        print("Basic .env file created. Please update with your actual tokens.")
    
    # Start the server
    try:
        uvicorn.run(
            "backend.persona_api:app",  # Updated to match your file structure
            host="127.0.0.1",
            port=8000,
            reload=True,
            reload_dirs=[str(project_root)],
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Failed to start server: {e}")
        print("Make sure you have all dependencies installed:")
        print("pip install fastapi uvicorn python-multipart python-jose[cryptography] passlib[bcrypt]")

if __name__ == "__main__":
    main()