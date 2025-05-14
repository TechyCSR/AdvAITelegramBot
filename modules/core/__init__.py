"""
Core package for the Advanced AI Telegram Bot

This package contains the core infrastructure and service components for the bot.
"""

from modules.core.database import (
    db_service,
    get_history_collection,
    get_user_collection,
    get_user_lang_collection,
    get_image_feedback_collection,
    get_prompt_storage_collection,
    get_user_images_collection
)

from modules.core.service_container import container, ServiceContainer 