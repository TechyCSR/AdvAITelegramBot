#!/usr/bin/env python3
"""
AdvAI Image Generator - Configuration File
Webapp-specific configuration for API keys and settings
"""

import os
from typing import Optional
from dotenv import load_dotenv



# Load environment variables from .env file
load_dotenv()

# Get API keys from environment variables
POLLINATIONS_KEY = os.getenv('POLLINATIONS_KEY') or ""
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY') or ""
FLASK_DEBUG = os.getenv('FLASK_DEBUG') or ""


# Alternative: Load from environment variable (recommended for production)
if os.environ.get('POLLINATIONS_KEY'):
    POLLINATIONS_KEY = os.environ.get('POLLINATIONS_KEY')

# =============================================================================
# WEBAPP CONFIGURATION
# =============================================================================

# Flask Configuration
FLASK_SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-change-this')
FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

# Image Generation Settings
MAX_IMAGES_PER_REQUEST = 4
MAX_PROMPT_LENGTH = 500
SUPPORTED_IMAGE_FORMATS = ['jpg', 'jpeg', 'png', 'webp']

# File Upload Settings
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
UPLOAD_FOLDER = 'static/uploads'
GENERATED_FOLDER = 'static/generated'

# =============================================================================
# VALIDATION
# =============================================================================

def validate_config():
    """Validate configuration settings"""
    if not POLLINATIONS_KEY or POLLINATIONS_KEY == "your_pollinations_api_key_here":
        print("⚠️  WARNING: POLLINATIONS_KEY not configured!")
        print("   Please set your API key in config.py or as environment variable")
        print("   Get your key from: https://pollinations.ai/")
        return False
    return True

# Auto-validate on import
if __name__ != "__main__":
    validate_config()
