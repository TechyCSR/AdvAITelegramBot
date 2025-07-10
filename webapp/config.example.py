#!/usr/bin/env python3
"""
AdvAI Image Generator - Configuration File Example
Webapp-specific configuration for API keys and settings
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# REQUIRED CONFIGURATION
# =============================================================================

# Pollinations AI API Key for image generation
POLLINATIONS_KEY = os.getenv('POLLINATIONS_KEY') or "your_pollinations_api_key_here"

# Telegram Bot Token for Mini App Authentication
BOT_TOKEN = os.getenv('BOT_TOKEN') or "your_telegram_bot_token"

# Flask Secret Key for session management
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY') or "your-secret-key-change-this-in-production"

# =============================================================================
# WEBAPP CONFIGURATION
# =============================================================================

# Flask Configuration
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

# Telegram Mini App Configuration
TELEGRAM_MINI_APP_REQUIRED = True  # Set to False to disable Telegram authentication
SESSION_TIMEOUT = 24 * 60 * 60  # 24 hours in seconds

# Image Generation Settings
MAX_IMAGES_PER_REQUEST = 4
MAX_PROMPT_LENGTH = 1000
SUPPORTED_IMAGE_FORMATS = ['jpg', 'jpeg', 'png', 'webp']

# File Upload Settings
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
UPLOAD_FOLDER = 'static/uploads'
GENERATED_FOLDER = 'static/generated'

# =============================================================================
# ENVIRONMENT VARIABLES FOR DEPLOYMENT
# =============================================================================

"""
For production deployment, set these environment variables:

POLLINATIONS_KEY=your_actual_pollinations_api_key
BOT_TOKEN=your_actual_telegram_bot_token
FLASK_SECRET_KEY=your_secure_random_secret_key
FLASK_DEBUG=False
TELEGRAM_MINI_APP_REQUIRED=True
SESSION_TIMEOUT=86400

For Vercel deployment, add these to your environment variables in the dashboard.
For other platforms, consult their documentation for setting environment variables.
"""

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
        issues.append("   Get your token from: @BotFather on Telegram")
    
    if FLASK_SECRET_KEY == "your-secret-key-change-this-in-production":
        issues.append("⚠️  WARNING: FLASK_SECRET_KEY using default value!")
        issues.append("   Please change FLASK_SECRET_KEY for production deployment")
        issues.append("   Use a cryptographically secure random string")
    
    if issues:
        for issue in issues:
            print(issue)
        return False
    return True

# Auto-validate on import
if __name__ != "__main__":
    validate_config() 