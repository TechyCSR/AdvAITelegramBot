import logging
import asyncio
import sys
from datetime import datetime, timedelta
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ChatType
from pymongo import MongoClient
from config import DATABASE_URL, ADMINS, OWNER_ID
from modules.chatlogs import channel_log, error_log
from modules.core.database import get_history_collection, get_user_collection
import os
import json
from typing import List, Dict, Optional, Union

# Set up logger
logger = logging.getLogger(__name__)

# Connect to MongoDB using the database service
history_collection = get_history_collection()
users_collection = get_user_collection()

# Ensure datetime module is correctly loaded
logger.info(f"Datetime module loaded. Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Number of messages per page for pagination
MESSAGES_PER_PAGE = 5

async def get_user_chat_history(bot: Client, message: Message, user_id: int, status_msg: Message) -> None:
    """
    Retrieve and provide chat history for a specific user
    
    Args:
        bot: The Telegram bot client
        message: The command message
        user_id: The user ID to get history for
        status_msg: Status message to update with progress
    """
    try:
        # Test datetime functionality - using global datetime from import
        current_time = datetime.now()
        logger.info(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        logger.info(f"Retrieving chat history for user {user_id}")
        
        # Check if user exists
        user_data = users_collection.find_one({"user_id": user_id})
        if not user_data:
            logger.error(f"User not found in users collection: {user_id}")
            # Try with integer user_id
            user_data = users_collection.find_one({"user_id": int(user_id)})
            if not user_data:
                await status_msg.edit_text(f"❌ **User Not Found**\n\nNo data found for user ID {user_id}.")
                return
            
        # Add debug logging
        logger.info(f"Found user: {user_data.get('first_name', '')} {user_data.get('last_name', '')}")
        
        # Get chat history from the correct collection
        user_history = history_collection.find_one({"user_id": user_id})
        if not user_history:
            # Try with integer user_id
            user_history = history_collection.find_one({"user_id": int(user_id)})
        
        chat_logs = []
        if user_history and 'history' in user_history:
            # Extract the history from the document
            history_data = user_history['history']
            
            # Filter to only include user and assistant messages (skip system messages)
            for entry in history_data:
                if entry.get('role') in ['user', 'assistant']:
                    chat_logs.append({
                        'role': entry.get('role'),
                        'content': entry.get('content', ''),
                        # Since we don't have timestamps, use the current time
                        'timestamp': datetime.now() 
                    })
            
            logger.info(f"Found {len(chat_logs)} chat entries for user {user_id}")
        else:
            logger.info(f"No chat history found for user {user_id}")
        
        if not chat_logs:
            # Create a test entry
            current_time = datetime.now()
            test_entry = {
                'role': 'user',
                'content': 'This is a test message as no chat history was found.',
                'timestamp': current_time
            }
            chat_logs = [test_entry]
            
            await status_msg.edit_text(
                f"ℹ️ **No Chat History Found**\n\n"
                f"No chat history found for user ID {user_id}.\n"
                f"User info: {user_data.get('first_name', '')} {user_data.get('last_name', '')}"
                f" (@{user_data.get('username', 'no_username')})"
            )
        else:
            # Update status message
            await status_msg.edit_text(
                f"🔍 **Retrieving Chat History**\n\n"
                f"Found {len(chat_logs)} messages for user {user_id}.\n"
                f"Preparing chat history file..."
            )
        
        # Create chat history text file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"user_{user_id}_history_{timestamp}.txt"
        
        with open(filename, "w", encoding="utf-8") as f:
            # Write user info header
            f.write(f"Chat History for User ID: {user_id}\n")
            f.write(f"Name: {user_data.get('first_name', '')} {user_data.get('last_name', '')}\n")
            f.write(f"Username: @{user_data.get('username', 'None')}\n")
            f.write(f"First seen: {user_data.get('first_seen', 'Unknown')}\n")
            f.write(f"Last activity: {user_data.get('last_active', 'Unknown')}\n\n")
            f.write("-" * 50 + "\n\n")
            
            # Write chat logs in conversation format
            for i, log in enumerate(chat_logs):
                role = log.get('role', '')
                content = log.get('content', '')
                
                # Use timestamp if available, otherwise use "Unknown time"
                timestamp = log.get("timestamp", "Unknown time")
                if isinstance(timestamp, datetime):
                    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    timestamp_str = str(timestamp)
                
                if role == 'user':
                    f.write(f"[{timestamp_str}] USER:\n{content}\n\n")
                elif role == 'assistant':
                    f.write(f"[{timestamp_str}] BOT:\n{content}\n\n")
                    f.write("-" * 50 + "\n\n")
        
        # Create interactive keyboard for pagination
        keyboard = [
            [
                InlineKeyboardButton("📄 View Latest", callback_data=f"history_user_{user_id}"),
                InlineKeyboardButton("⬅️ Back", callback_data="history_search")
            ]
        ]
        
        # Send the file
        await bot.send_document(
            chat_id=message.chat.id,
            document=filename,
            caption=f"📋 **Chat History for User {user_id}**\n\n"
                   f"User: {user_data.get('first_name', '')} {user_data.get('last_name', '')}\n"
                   f"Username: @{user_data.get('username', 'None')}\n"
                   f"Total messages: {len(chat_logs)}\n\n"
                   f"You can view the latest messages interactively using the button below:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Remove the temporary file
        try:
            os.remove(filename)
        except Exception as e:
            logger.error(f"Error removing temporary file: {e}")
            
        # Update status message
        await status_msg.delete()
            
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        logger.exception("Detailed error:")
        await status_msg.edit_text(f"❌ **Error retrieving chat history**: {str(e)}")
        await error_log(bot, "HISTORY_RETRIEVAL", str(e))

async def show_history_search_panel(client: Client, callback_query: CallbackQuery) -> None:
    """
    Show the history search panel in the admin dashboard
    
    Args:
        client: The Telegram bot client
        callback_query: The callback query
    """
    try:
        # Get users who have chat history
        users_with_history = list(history_collection.find({}, {"user_id": 1}))
        user_ids = [user.get("user_id") for user in users_with_history if user.get("user_id")]
        
        logger.info(f"Found {len(user_ids)} users with chat history")
        
        # Get user details for these users
        user_buttons = []
        for user_id in user_ids[:10]:  # Limit to 10 most recent users
            user_info = users_collection.find_one({"user_id": user_id})
            
            if user_info:
                name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}"
                username = user_info.get('username', 'No username')
                last_active = user_info.get("last_active", "Unknown")
                
                # Format last active time
                if isinstance(last_active, datetime):
                    time_diff = datetime.now() - last_active
                    if time_diff < timedelta(minutes=60):
                        last_active_str = f"{int(time_diff.total_seconds() / 60)}m ago"
                    elif time_diff < timedelta(hours=24):
                        last_active_str = f"{int(time_diff.total_seconds() / 3600)}h ago"
                    else:
                        last_active_str = f"{int(time_diff.total_seconds() / 86400)}d ago"
                else:
                    last_active_str = "Unknown"
                    
                # Create button text
                button_text = f"{name[:15]} (@{username[:10]}) - {last_active_str}"
                user_buttons.append([InlineKeyboardButton(
                    button_text, callback_data=f"history_user_{user_id}"
                )])
        
        # If no users found, add a message
        if not user_buttons:
            message_text = (
                "📋 **User Chat History**\n\n"
                "No users with chat history found.\n"
                "You can search for a specific user ID using the button below."
            )
        else:
            message_text = (
                "📋 **User Chat History**\n\n"
                "Select a user to view their chat history or search by user ID.\n"
                "Users with chat history:"
            )
        
        # Add help button and back button
        keyboard = user_buttons + [
            [
                InlineKeyboardButton("🔍 Search by ID", callback_data="admin_search_user"),
                InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin_panel")
            ]
        ]
        
        # Edit the message with the history search panel
        await callback_query.edit_message_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error showing history search panel: {e}")
        logger.exception("Detailed error in show_history_search_panel:")
        await callback_query.answer("Error loading history panel")

async def handle_history_user_selection(client: Client, callback_query: CallbackQuery, user_id: int) -> None:
    """
    Handle user selection for viewing chat history
    
    Args:
        client: The Telegram bot client
        callback_query: The callback query
        user_id: The selected user ID
    """
    try:
        # Show loading state
        await callback_query.edit_message_text(
            f"🔍 **Loading Chat History**\n\n"
            f"Retrieving messages for user {user_id}..."
        )
        
        # Get user info
        user_data = users_collection.find_one({"user_id": user_id})
        if not user_data:
            logger.error(f"User not found in users collection: {user_id}")
            await callback_query.edit_message_text(
                f"❌ **User Not Found**\n\n"
                f"No data found for user ID {user_id}.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="history_search")]
                ])
            )
            return
        
        # Get chat history from the correct collection
        user_history = history_collection.find_one({"user_id": user_id})
        if not user_history:
            # Try with integer user_id
            user_history = history_collection.find_one({"user_id": int(user_id)})
        
        chat_logs = []
        if user_history and 'history' in user_history:
            # Extract the history from the document
            history_data = user_history['history']
            
            # Filter to only include user and assistant messages (skip system messages)
            for entry in history_data:
                if entry.get('role') in ['user', 'assistant']:
                    chat_logs.append({
                        'role': entry.get('role'),
                        'content': entry.get('content', ''),
                        # Since we don't have timestamps, use the current time
                        'timestamp': datetime.now() 
                    })
            
            # Sort logs with newest first for display
            chat_logs.reverse()
            
            logger.info(f"Found {len(chat_logs)} chat entries for user {user_id}")
        else:
            logger.info(f"No chat history found for user {user_id}")
        
        if not chat_logs:
            # If no history found, show a message
            await callback_query.edit_message_text(
                f"ℹ️ **No Chat History**\n\n"
                f"No chat history found for user {user_id}.\n"
                f"User: {user_data.get('first_name', '')} {user_data.get('last_name', '')}"
                f" (@{user_data.get('username', 'None')})",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="history_search")]
                ])
            )
            return
        
        # Create chat history text file with the latest messages
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"user_{user_id}_latest_{timestamp}.txt"
        
        # Get the most recent messages (up to 20)
        recent_messages = chat_logs[:20]
        
        with open(filename, "w", encoding="utf-8") as f:
            # Write header
            f.write(f"=" * 80 + "\n")
            f.write(f"LATEST CHAT HISTORY FOR USER ID: {user_id}\n")
            f.write(f"=" * 80 + "\n\n")
            
            # Write user info
            f.write(f"User: {user_data.get('first_name', '')} {user_data.get('last_name', '')}\n")
            f.write(f"Username: @{user_data.get('username', 'None')}\n")
            f.write(f"Total conversations: {len(chat_logs)}\n\n")
            f.write(f"=" * 80 + "\n\n")
            
            # Write most recent messages
            f.write(f"RECENT MESSAGES (NEWEST FIRST):\n\n")
            
            for i, log in enumerate(recent_messages):
                role = log.get('role', '')
                content = log.get('content', '')
                
                if role == 'user':
                    f.write(f"USER: {content}\n\n")
                elif role == 'assistant':
                    f.write(f"BOT: {content}\n\n")
                    f.write("-" * 80 + "\n\n")
        
        # Create pagination keyboard
        total_pages = (len(chat_logs) + MESSAGES_PER_PAGE - 1) // MESSAGES_PER_PAGE
        
        keyboard = [
            [
                InlineKeyboardButton("📄 Browse Page 1", callback_data=f"history_page_{user_id}_1"),
                InlineKeyboardButton("📥 Download All", callback_data=f"history_download_{user_id}")
            ],
            [
                InlineKeyboardButton("⬅️ Back", callback_data="history_search")
            ]
        ]
        
        # Send the text file with latest messages
        await client.send_document(
            chat_id=callback_query.message.chat.id,
            document=filename,
            caption=f"📋 **Latest Chat History for User {user_id}**\n\n"
                   f"User: {user_data.get('first_name', '')} {user_data.get('last_name', '')}\n"
                   f"Username: @{user_data.get('username', 'None')}\n"
                   f"Total messages: {len(chat_logs)}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Update the original message
        await callback_query.edit_message_text(
            f"✅ **Chat History Loaded**\n\n"
            f"User: {user_data.get('first_name', '')} {user_data.get('last_name', '')}\n"
            f"The latest messages have been sent as a text file above.\n"
            f"You can also browse the history page by page or download the full history.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Remove the temporary file
        try:
            os.remove(filename)
        except Exception as e:
            logger.error(f"Error removing temporary file: {e}")
        
    except Exception as e:
        logger.error(f"Error handling history user selection: {e}")
        logger.exception("Detailed error:")
        await callback_query.answer("Error loading history", show_alert=True)
        await callback_query.edit_message_text(
            f"❌ **Error**\n\n"
            f"Failed to retrieve chat history. Please try again later.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="history_search")]
            ])
        )

async def handle_history_pagination(client: Client, callback_query: CallbackQuery, user_id: int, page: int) -> None:
    """
    Handle pagination for viewing chat history
    
    Args:
        client: The Telegram bot client
        callback_query: The callback query
        user_id: The user ID to view history for
        page: The page number to display
    """
    try:
        # Calculate skip amount based on page
        skip = (page - 1) * MESSAGES_PER_PAGE
        
        # Get user info
        user_data = users_collection.find_one({"user_id": user_id})
        if not user_data:
            logger.error(f"User not found in users collection: {user_id}")
            await callback_query.answer("User not found", show_alert=True)
            await callback_query.edit_message_text(
                "❌ **User Not Found**\n\nThis user no longer exists in the database."
            )
            return
        
        # Get chat history from the correct collection
        user_history = history_collection.find_one({"user_id": user_id})
        if not user_history:
            # Try with integer user_id
            user_history = history_collection.find_one({"user_id": int(user_id)})
        
        chat_logs = []
        if user_history and 'history' in user_history:
            # Extract the history from the document
            history_data = user_history['history']
            
            # Filter to only include user and assistant messages (skip system messages)
            for entry in history_data:
                if entry.get('role') in ['user', 'assistant']:
                    chat_logs.append({
                        'role': entry.get('role'),
                        'content': entry.get('content', ''),
                        # Since we don't have timestamps, use the current time
                        'timestamp': datetime.now() 
                    })
            
            logger.info(f"Found {len(chat_logs)} chat entries for user {user_id}")
        else:
            logger.info(f"No chat history found for user {user_id}")
        
        if not chat_logs:
            # Create a test entry
            current_time = datetime.now()
            test_entry = {
                'role': 'user',
                'content': 'This is a test message as no chat history was found.',
                'timestamp': current_time
            }
            chat_logs = [test_entry]
            
            await callback_query.edit_message_text(
                f"ℹ️ **No Chat History Found**\n\n"
                f"No chat history found for user ID {user_id}.\n"
                f"User info: {user_data.get('first_name', '')} {user_data.get('last_name', '')}"
                f" (@{user_data.get('username', 'no_username')})",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="history_search")]
                ])
            )
            return
        
        # Apply pagination
        start_idx = skip
        end_idx = min(skip + MESSAGES_PER_PAGE, len(chat_logs))
        
        # Get paginated chat logs
        paginated_logs = chat_logs[start_idx:end_idx]
        
        # Calculate total pages
        total_pages = (len(chat_logs) + MESSAGES_PER_PAGE - 1) // MESSAGES_PER_PAGE
        
        # Create formatted message
        message_text = f"📋 **Chat History for User {user_id}**\n\n"
        message_text += f"**User**: {user_data.get('first_name', '')} {user_data.get('last_name', '')}"
        if user_data.get('username'):
            message_text += f" (@{user_data.get('username')})"
        message_text += f"\n📊 Page {page}/{total_pages} (Total: {len(chat_logs)} messages)\n\n"
        
        # Add chat logs
        for log in paginated_logs:
            role = log.get('role', '')
            content = log.get('content', '')
            
            # Use timestamp if available, otherwise use "Unknown time"
            timestamp = log.get("timestamp", "Unknown time")
            if isinstance(timestamp, datetime):
                timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                timestamp_str = str(timestamp)
                
            # Truncate message if too long - reduce from 150 to 100 chars
            message_text_content = content
            if len(message_text_content) > 100:
                message_text_content = message_text_content[:97] + "..."
                
            if role == 'user':
                message_text += f"🗣️ **USER**:\n{message_text_content}\n\n"
            elif role == 'assistant':
                message_text += f"🤖 **BOT**:\n{message_text_content}\n\n"
        
        # Check if message is too long (Telegram limit is ~4000 chars)
        if len(message_text) > 3800:
            # If too long, truncate the message and add a note
            message_text = message_text[:3700] + "\n\n⚠️ *Some messages truncated due to length limits*"
        
        # Create keyboard for navigation
        keyboard = []
        nav_row = []
        
        # Add navigation buttons
        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"history_page_{user_id}_{page-1}"))
        if page < total_pages:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"history_page_{user_id}_{page+1}"))
        if nav_row:
            keyboard.append(nav_row)
            
        # Add action buttons
        action_row = [
            InlineKeyboardButton("📥 Download", callback_data=f"history_download_{user_id}"),
            InlineKeyboardButton("⬅️ Back", callback_data="history_search")
        ]
        keyboard.append(action_row)
        
        # Edit message with paginated history
        await callback_query.edit_message_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
            
    except Exception as e:
        logger.error(f"Error handling history pagination: {e}")
        logger.exception("Detailed error:")
        await callback_query.answer("Error displaying history", show_alert=True)
        await callback_query.edit_message_text(
            "❌ **Error Displaying History**\n\nAn error occurred while retrieving chat history.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="history_search")]
            ])
        )

async def get_history_download(client: Client, callback_query: CallbackQuery, user_id: int) -> None:
    """
    Generate and send a downloadable chat history file
    
    Args:
        client: The Telegram bot client
        callback_query: The callback query
        user_id: The user ID to get history for
    """
    try:
        # Show processing message
        await callback_query.edit_message_text(
            f"⏳ **Preparing Download**\n\n"
            f"Generating chat history file for user {user_id}...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Cancel", callback_data=f"history_page_{user_id}_1")]
            ])
        )
        
        # Get user info
        user_data = users_collection.find_one({"user_id": user_id})
        if not user_data:
            logger.error(f"User not found in users collection: {user_id}")
            await callback_query.answer("User not found", show_alert=True)
            await callback_query.edit_message_text(
                "❌ **User Not Found**\n\nThis user no longer exists in the database."
            )
            return
        
        # Get chat history from the correct collection
        user_history = history_collection.find_one({"user_id": user_id})
        if not user_history:
            # Try with integer user_id
            user_history = history_collection.find_one({"user_id": int(user_id)})
        
        chat_logs = []
        if user_history and 'history' in user_history:
            # Extract the history from the document
            history_data = user_history['history']
            
            # Filter to only include user and assistant messages (skip system messages)
            for entry in history_data:
                if entry.get('role') in ['user', 'assistant']:
                    chat_logs.append({
                        'role': entry.get('role'),
                        'content': entry.get('content', ''),
                        # Since we don't have timestamps, use the current time
                        'timestamp': datetime.now() 
                    })
            
            logger.info(f"Found {len(chat_logs)} chat entries for user {user_id}")
        else:
            logger.info(f"No chat history found for user {user_id}")
        
        if not chat_logs:
            # Create a test entry
            current_time = datetime.now()
            test_entry = {
                'role': 'user',
                'content': 'This is a test message as no chat history was found.',
                'timestamp': current_time
            }
            chat_logs = [test_entry]
            
            await callback_query.edit_message_text(
                f"ℹ️ **No Chat History Found**\n\n"
                f"No chat history found for user ID {user_id}.\n"
                f"User info: {user_data.get('first_name', '')} {user_data.get('last_name', '')}"
                f" (@{user_data.get('username', 'no_username')})",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="history_search")]
                ])
            )
            return
        
        # Create chat history text file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"user_{user_id}_history_{timestamp}.txt"
        
        with open(filename, "w", encoding="utf-8") as f:
            # Write file header
            f.write(f"=" * 80 + "\n")
            f.write(f"CHAT HISTORY FOR USER ID: {user_id}\n")
            f.write(f"=" * 80 + "\n\n")
            
            # Write user info
            f.write(f"USER INFORMATION:\n")
            f.write(f"Name: {user_data.get('first_name', '')} {user_data.get('last_name', '')}\n")
            f.write(f"Username: @{user_data.get('username', 'None')}\n")
            f.write(f"First seen: {user_data.get('first_seen', 'Unknown')}\n")
            f.write(f"Last active: {user_data.get('last_active', 'Unknown')}\n")
            f.write(f"Total messages: {len(chat_logs)}\n\n")
            f.write(f"=" * 80 + "\n\n")
            
            # Write chat logs in conversational format
            f.write(f"CONVERSATION HISTORY:\n\n")
            
            # Group messages by conversation
            current_conversation = []
            for i, entry in enumerate(chat_logs):
                role = entry.get('role', '')
                content = entry.get('content', '')
                
                # Use timestamp if available, otherwise use "Unknown time"
                timestamp = entry.get("timestamp", "Unknown time")
                if isinstance(timestamp, datetime):
                    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    timestamp_str = str(timestamp)
                
                message_text = content
                if len(message_text) > 500:
                    message_text = message_text[:500] + "... [TRUNCATED]"
                
                if role == 'user':
                    f.write(f"USER [{timestamp_str}]:\n{message_text}\n\n")
                elif role == 'assistant':
                    f.write(f"BOT [{timestamp_str}]:\n{message_text}\n\n")
                    f.write("-" * 80 + "\n\n")
        
        # Send the file
        await client.send_document(
            chat_id=callback_query.message.chat.id,
            document=filename,
            caption=f"📋 **Complete Chat History for User {user_id}**\n\n"
                   f"User: {user_data.get('first_name', '')} {user_data.get('last_name', '')}\n"
                   f"Username: @{user_data.get('username', 'None')}\n"
                   f"Total messages: {len(chat_logs)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to History", callback_data=f"history_page_{user_id}_1")]
            ])
        )
        
        # Remove the temporary file
        try:
            os.remove(filename)
        except Exception as e:
            logger.error(f"Error removing temporary file: {e}")
        
        # Update success message
        await callback_query.edit_message_text(
            f"✅ **Download Complete**\n\n"
            f"Chat history for user {user_id} has been generated and sent as a file.\n"
            f"Total messages: {len(chat_logs)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to History", callback_data=f"history_page_{user_id}_1")]
            ])
        )
            
    except Exception as e:
        logger.error(f"Error generating history download: {e}")
        logger.exception("Detailed error:")
        await callback_query.answer("Error generating download", show_alert=True)
        await callback_query.edit_message_text(
            "❌ **Error Generating Download**\n\nAn error occurred while creating the chat history file.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data=f"history_page_{user_id}_1")]
            ])
        )

async def show_user_search_form(client: Client, callback_query: CallbackQuery) -> None:
    """
    Show a form to search for user chat history by user ID
    
    Args:
        client: The Telegram bot client
        callback_query: The callback query
    """
    try:
        # Get the session collection
        from modules.core.database import get_session_collection
        session_collection = get_session_collection()
        
        # Clear any existing session first
        session_collection.update_one(
            {"user_id": callback_query.from_user.id},
            {"$unset": {
                "awaiting_user_id_for_history": "",
                "message_id": ""
            }},
            upsert=True
        )
        
        # Set the session flag for awaiting user ID input
        session_collection.update_one(
            {"user_id": callback_query.from_user.id},
            {"$set": {
                "awaiting_user_id_for_history": True,
                "message_id": callback_query.message.id
            }},
            upsert=True
        )
        
        # Show the search form
        await callback_query.edit_message_text(
            "🔍 **Search User Chat History**\n\n"
            "Please enter the user ID you want to search for in your next message.\n\n"
            "Example: `123456789`\n\n"
            "⚠️ **IMPORTANT**: Your next message will be treated as a user ID search.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="history_search")]
            ])
        )
        
        # Notify the user
        await callback_query.answer("Please enter a user ID in your next message")
        
    except Exception as e:
        logger.error(f"Error showing user search form: {e}")
        await callback_query.answer("Error showing search form")
        # Try to log detailed error
        logger.exception("Detailed error in show_user_search_form:") 