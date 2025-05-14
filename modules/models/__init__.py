"""
Models package for the Advanced AI Telegram Bot

This package contains the core data models and service classes for the bot.
"""

from modules.models.ai_res import aires, new_chat
from modules.models.user_db import (
    check_and_add_user, 
    check_and_add_username, 
    get_user_ids, 
    get_user_language
)
from modules.models.image_service import ImageService 