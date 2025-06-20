import os
import logging
import json
from datetime import datetime, timedelta
from config import LOG_CHANNEL, DATABASE_URL
from modules.core.database import db_service

# Setup logging
logger = logging.getLogger(__name__)

# Simple channel logging
async def channel_log(bot, message, action_type, additional_info=None, level="INFO"):
    """
    Send a standardized log message to the log channel
    """
    try:
        # Handle both Message and CallbackQuery objects
        is_callback = hasattr(message, 'message') and message.message is not None
        
        actual_message = message.message if is_callback else message
        user = message.from_user

        user_id = user.id if user else None
        username = user.username if user else None
        user_mention = user.mention if user else "Unknown"
        
        chat_id = actual_message.chat.id if actual_message and actual_message.chat else None
        chat_type = actual_message.chat.type if actual_message and actual_message.chat else None
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Format for channel logging
        tags = f"#{level}"
        if action_type.startswith('/'):
            tags += " #Command"
            command = action_type.split()[0].replace("/", "")
            tags += f" #{command.capitalize()}"
        else:
            action_category = action_type.split('_')[0] if '_' in action_type else action_type
            tags += f" #{action_category.capitalize()}"
        
        log_message = (
            f"{tags}\n"
            f"**User**: {user_mention}\n"
            f"**User ID**: `{user_id}`\n"
            f"**Action**: `{action_type}`\n"
            f"**Chat**: `{chat_id} ({chat_type})`\n"
            f"**Time**: {timestamp}\n"
        )
        
        if additional_info:
            log_message += f"**Details**: {additional_info}\n"
            
        # Send to channel
        await bot.send_message(LOG_CHANNEL, log_message)
        
        # Log it locally too
        if level == "INFO":
            logger.info(f"CHANNEL_LOG: {action_type} by user {user_id}")
        elif level == "WARNING":
            logger.warning(f"CHANNEL_LOG: {action_type} by user {user_id} - {additional_info}")
        elif level == "ERROR":
            logger.error(f"CHANNEL_LOG: {action_type} by user {user_id} - {additional_info}")
            
    except Exception as e:
        logger.error(f"Failed to log to channel: {str(e)}")

async def user_log(bot, message, query, response=None):
    """
    Log user interactions, especially AI queries and responses
    """
    try:
        user_id = message.from_user.id if message.from_user else None
        chat_id = message.chat.id if message.chat else None
        chat_type = message.chat.type if message.chat else None
        timestamp = datetime.now()
        
        # Truncate query and response for logging
        truncated_query = query[:500] + "..." if query and len(query) > 500 else query
        truncated_response = response[:500] + "..." if response and len(response) > 500 else response
        
        # Log to channel only if in direct chat (for privacy)
        if str(chat_type) == "private":
            channel_msg = (
                f"#UserQuery\n"
                f"**User**: {message.from_user.mention}\n"
                f"**User ID**: `{user_id}`\n"
                f"**Time**: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"**Query**: ```{truncated_query}```\n"
            )
            
            if truncated_response:
                channel_msg += f"**Response**: ```{truncated_response}```\n"
                
            await bot.send_message(LOG_CHANNEL, channel_msg)
        
        # Local logging
        log_entry = f"User {user_id} in {chat_id} ({chat_type}): {truncated_query}"
        logger.info(log_entry)
        
        # Save to database - ensure user_id is consistently stored as integer
        logs_collection = db_service.get_collection('user_logs')
        
        # Store the log with user_id as integer and chat_type as string
        log_data = {
            "user_id": int(user_id) if user_id else None,
            "chat_id": chat_id,
            "chat_type": str(chat_type),
            "message": query,
            "response": response,
            "timestamp": timestamp
        }
        
        logs_collection.insert_one(log_data)
        logger.debug(f"Saved log to database for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to log user interaction: {str(e)}")
        logger.exception("Detailed error in user_log:")

async def error_log(bot, error_type, error_message, context=None, user_id=None):
    """
    Log errors to channel
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Log to channel
        channel_msg = (
            f"#ERROR #{error_type}\n"
            f"**Time**: {timestamp}\n"
            f"**Error**: `{error_message}`\n"
        )
        
        if context:
            channel_msg += f"**Context**: ```{context}```\n"
            
        if user_id:
            channel_msg += f"**User ID**: `{user_id}`\n"
            
        await bot.send_message(LOG_CHANNEL, channel_msg)
        
        # Local logging
        logger.error(f"BOT_ERROR: {error_type} - {error_message}")
        
    except Exception as e:
        logger.error(f"Failed to log error: {str(e)}")