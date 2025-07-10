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

# Telegram Bot Configuration for Mini App Authentication
BOT_TOKEN = os.getenv('BOT_TOKEN') or ""

# Alternative: Load from environment variable (recommended for production)
if os.environ.get('POLLINATIONS_KEY'):
    POLLINATIONS_KEY = os.environ.get('POLLINATIONS_KEY')

if os.environ.get('BOT_TOKEN'):
    BOT_TOKEN = os.environ.get('BOT_TOKEN')

# =============================================================================
# WEBAPP CONFIGURATION
# =============================================================================

# Flask Configuration
FLASK_SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-change-this')
FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

# Telegram Mini App Configuration
TELEGRAM_MINI_APP_REQUIRED = True  # Set to False to disable Telegram authentication
SESSION_TIMEOUT = 24 * 60 * 60  # 24 hours in seconds

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
    issues = []
    
    if not POLLINATIONS_KEY or POLLINATIONS_KEY == "your_pollinations_api_key_here":
        issues.append("⚠️  WARNING: POLLINATIONS_KEY not configured!")
        issues.append("   Please set your API key in config.py or as environment variable")
        issues.append("   Get your key from: https://pollinations.ai/")
    
    if TELEGRAM_MINI_APP_REQUIRED and (not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token"):
        issues.append("⚠️  WARNING: BOT_TOKEN not configured!")
        issues.append("   Telegram Mini App authentication requires BOT_TOKEN")
        issues.append("   Please set your bot token in config.py or as environment variable")
    
    if issues:
        for issue in issues:
            print(issue)
        return False
    return True

# Auto-validate on import
if __name__ != "__main__":
    validate_config()
