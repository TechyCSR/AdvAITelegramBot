import os
import logging
import json
from datetime import datetime, timedelta
from config import LOG_CHANNEL
from pymongo import MongoClient

# Setup logging
logger = logging.getLogger(__name__)

# Simple channel logging
async def channel_log(bot, message, action_type, additional_info=None, level="INFO"):
    """
    Send a standardized log message to the log channel
    """
    try:
        user_id = message.from_user.id if message.from_user else None
        username = message.from_user.username if message.from_user else None
        chat_id = message.chat.id if message.chat else None
        chat_type = message.chat.type if message.chat else None
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
            f"**User**: {message.from_user.mention if message.from_user else 'Unknown'}\n"
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
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Truncate query and response for logging
        truncated_query = query[:500] + "..." if query and len(query) > 500 else query
        truncated_response = response[:500] + "..." if response and len(response) > 500 else response
        
        # Log to channel only if in direct chat (for privacy)
        if chat_type == "private":
            channel_msg = (
                f"#UserQuery\n"
                f"**User**: {message.from_user.mention}\n"
                f"**User ID**: `{user_id}`\n"
                f"**Time**: {timestamp}\n"
                f"**Query**: ```{truncated_query}```\n"
            )
            
            if truncated_response:
                channel_msg += f"**Response**: ```{truncated_response}```\n"
                
            await bot.send_message(LOG_CHANNEL, channel_msg)
        
        # Local logging
        log_entry = f"User {user_id} in {chat_id} ({chat_type}): {truncated_query}"
        logger.info(log_entry)
        
    except Exception as e:
        logger.error(f"Failed to log user interaction: {str(e)}")

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

