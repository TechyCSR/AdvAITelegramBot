#!/usr/bin/env python3
"""
Telegram Logging System for WebApp
Logs image generations and user activities to Telegram log channel
"""

import os
import logging
import asyncio
import requests
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any

# Import config for LOG_CHANNEL and BOT_TOKEN
try:
    from config import LOG_CHANNEL, BOT_TOKEN
except ImportError:
    LOG_CHANNEL = os.environ.get('LOG_CHANNEL', '')
    BOT_TOKEN = os.environ.get('BOT_TOKEN', '')

# Configure logging
logger = logging.getLogger(__name__)

class TelegramLogger:
    """Handle logging to Telegram log channel"""
    
    def __init__(self):
        self.bot_token = BOT_TOKEN
        # Fix channel format - use the correct numeric ID from test
        self.log_channel = self._fix_channel_format(LOG_CHANNEL)
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def _fix_channel_format(self, channel):
        """Fix the channel format to use the correct ID"""
        if not channel:
            return channel
        
        # If it's just the channel name without @, add @
        if not channel.startswith('@') and not channel.startswith('-') and not channel.isdigit():
            if channel == "advchatgptlogs":
                # Use the correct numeric ID found from the test
                return "-1002842298904"
            else:
                return f"@{channel}"
        
        return channel
        
    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Send a text message to the log channel"""
        try:
            if not self.bot_token or not self.log_channel:
                logger.warning("Bot token or log channel not configured")
                return False
            
            logger.info(f"Sending message to channel: {self.log_channel}")
            
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.log_channel,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                logger.info("Successfully sent message to log channel")
                return True
            else:
                logger.error(f"Failed to send message to log channel: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message to log channel: {str(e)}")
            return False
    
    def send_photo(self, photo_url: str, caption: str = "", parse_mode: str = "Markdown") -> bool:
        """Send a photo to the log channel"""
        try:
            if not self.bot_token or not self.log_channel:
                logger.warning("Bot token or log channel not configured")
                return False
            
            logger.info(f"Sending photo to channel: {self.log_channel}")
            
            url = f"{self.base_url}/sendPhoto"
            data = {
                "chat_id": self.log_channel,
                "photo": photo_url,
                "caption": caption,
                "parse_mode": parse_mode
            }
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                logger.info("Successfully sent photo to log channel")
                return True
            else:
                logger.error(f"Failed to send photo to log channel: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending photo to log channel: {str(e)}")
            return False
    
    def send_media_group(self, media_list: List[Dict], caption: str = "") -> bool:
        """Send multiple photos as a media group to the log channel"""
        try:
            if not self.bot_token or not self.log_channel:
                logger.warning("Bot token or log channel not configured")
                return False
            
            logger.info(f"Sending media group to channel: {self.log_channel}")
            
            # Prepare media group
            media = []
            for i, media_item in enumerate(media_list):
                media_data = {
                    "type": "photo",
                    "media": media_item["url"]
                }
                # Add caption to first image only
                if i == 0 and caption:
                    media_data["caption"] = caption
                    media_data["parse_mode"] = "Markdown"
                    
                media.append(media_data)
            
            url = f"{self.base_url}/sendMediaGroup"
            data = {
                "chat_id": self.log_channel,
                "media": media
            }
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                logger.info("Successfully sent media group to log channel")
                return True
            else:
                logger.error(f"Failed to send media group to log channel: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending media group to log channel: {str(e)}")
            return False
    
    def log_image_generation(self, user: Any, prompt: str, style: str, 
                                 image_urls: List[str], generation_data: Dict) -> bool:
        """Log image generation to the log channel"""
        try:
            generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            generation_id = f"webapp_{user.id}_{int(datetime.now().timestamp())}"
            
            # Create user mention
            user_mention = self.get_user_mention(user)
            
            # Send images first (if any)
            if image_urls:
                if len(image_urls) == 1:
                    # Single image
                    self.send_photo(
                        image_urls[0],
                        f"#WebAppImgLog #Generated\n**Generated via WebApp**"
                    )
                else:
                    # Multiple images as media group
                    media_list = [{"url": url} for url in image_urls]
                    self.send_media_group(
                        media_list,
                        f"#WebAppImgLog #Generated\n**Generated via WebApp**"
                    )
            
            # Send metadata
            metadata_text = (
                f"#WebAppImgLog #Generated\n"
                f"**Source**: WebApp\n"
                f"**Prompt**: `{prompt}`\n"
                f"**Style**: `{style}`\n"
                f"**User**: {user_mention}\n"
                f"**User ID**: `{user.id}`\n"
                f"**Auth Type**: `{user.auth_type}`\n"
                f"**Time**: {generation_time}\n"
                f"**Images**: {len(image_urls)}\n"
                f"**Size**: `{generation_data.get('size', 'N/A')}`\n"
                f"**Model**: `{generation_data.get('model', 'N/A')}`\n"
                f"**Generation ID**: `{generation_id}`"
            )
            
            self.send_message(metadata_text)
            
            logger.info(f"Logged image generation for user {user.id} to channel")
            return True
            
        except Exception as e:
            logger.error(f"Error logging image generation: {str(e)}")
            return False
    
    def log_error(self, error_type: str, error_message: str, user_id: Optional[int] = None, 
                       context: Optional[str] = None) -> bool:
        """Log an error to the log channel"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            error_text = (
                f"#WebAppError #{error_type}\n"
                f"**Source**: WebApp\n"
                f"**Time**: {timestamp}\n"
                f"**Error**: `{error_message}`\n"
            )
            
            if user_id:
                error_text += f"**User ID**: `{user_id}`\n"
                
            if context:
                error_text += f"**Context**: ```{context}```\n"
            
            self.send_message(error_text)
            
            logger.info(f"Logged error to channel: {error_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging error to channel: {str(e)}")
            return False
    
    def log_user_activity(self, user: Any, activity: str, details: Optional[str] = None) -> bool:
        """Log general user activity"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            user_mention = self.get_user_mention(user)
            
            activity_text = (
                f"#WebAppActivity\n"
                f"**Source**: WebApp\n"
                f"**User**: {user_mention}\n"
                f"**User ID**: `{user.id}`\n"
                f"**Auth Type**: `{user.auth_type}`\n"
                f"**Activity**: `{activity}`\n"
                f"**Time**: {timestamp}\n"
            )
            
            if details:
                activity_text += f"**Details**: {details}\n"
            
            self.send_message(activity_text)
            
            logger.info(f"Logged user activity for user {user.id}: {activity}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging user activity: {str(e)}")
            return False
    
    def get_user_mention(self, user: Any) -> str:
        """Create a user mention string"""
        try:
            if hasattr(user, 'username') and user.username:
                return f"@{user.username}"
            elif hasattr(user, 'display_name') and user.display_name:
                return f"[{user.display_name}](tg://user?id={user.id})"
            elif hasattr(user, 'first_name') and user.first_name:
                name = user.first_name
                if hasattr(user, 'last_name') and user.last_name:
                    name += f" {user.last_name}"
                return f"[{name}](tg://user?id={user.id})"
            else:
                return f"User {user.id}"
        except Exception as e:
            logger.error(f"Error creating user mention: {str(e)}")
            return f"User {getattr(user, 'id', 'Unknown')}"

# Create global instance
telegram_logger = TelegramLogger()

# Background wrapper functions for easy use
def log_image_generation(user: Any, prompt: str, style: str, 
                        image_urls: List[str], generation_data: Dict) -> None:
    """Log image generation to Telegram channel in background"""
    def _log():
        try:
            telegram_logger.log_image_generation(user, prompt, style, image_urls, generation_data)
        except Exception as e:
            logger.error(f"Background logging failed: {str(e)}")
    
    # Run in background thread
    thread = threading.Thread(target=_log, daemon=True)
    thread.start()

def log_error(error_type: str, error_message: str, user_id: Optional[int] = None, 
              context: Optional[str] = None) -> None:
    """Log error to Telegram channel in background"""
    def _log():
        try:
            telegram_logger.log_error(error_type, error_message, user_id, context)
        except Exception as e:
            logger.error(f"Background error logging failed: {str(e)}")
    
    # Run in background thread
    thread = threading.Thread(target=_log, daemon=True)
    thread.start()

def log_user_activity(user: Any, activity: str, details: Optional[str] = None) -> None:
    """Log user activity to Telegram channel in background"""
    def _log():
        try:
            telegram_logger.log_user_activity(user, activity, details)
        except Exception as e:
            logger.error(f"Background activity logging failed: {str(e)}")
    
    # Run in background thread
    thread = threading.Thread(target=_log, daemon=True)
    thread.start() 