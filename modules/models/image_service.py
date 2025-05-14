import os
import time
import asyncio
import uuid
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from modules.core.database import get_user_images_collection, get_prompt_storage_collection

# Configure logging
logger = logging.getLogger(__name__)

class ImageService:
    """
    Service class for handling image generation and management
    with efficient database operations and caching
    """
    
    # Common image styles for the bot UI
    AVAILABLE_STYLES = {
        "photorealistic": "📸 Photorealistic",
        "anime": "🎭 Anime Style",
        "3d_render": "🧊 3D Render",
        "cartoon": "🎨 Cartoon",
        "pixel_art": "👾 Pixel Art",
        "oil_painting": "🖼️ Oil Painting",
        "watercolor": "💦 Watercolor",
        "sketch": "✏️ Sketch",
        "vector_art": "📊 Vector Art",
        "cyberpunk": "🤖 Cyberpunk",
        "fantasy": "🧙‍♂️ Fantasy",
        "steampunk": "⚙️ Steampunk",
        "neon": "✨ Neon"
    }
    
    @staticmethod
    def get_image_styles_keyboard() -> InlineKeyboardMarkup:
        """
        Get a keyboard markup with available image styles
        
        Returns:
            InlineKeyboardMarkup with style buttons
        """
        # Create a multi-row keyboard with styles
        keyboard = []
        row = []
        
        for i, (style_id, style_name) in enumerate(ImageService.AVAILABLE_STYLES.items()):
            if i > 0 and i % 2 == 0:  # Two buttons per row
                keyboard.append(row)
                row = []
            row.append(InlineKeyboardButton(style_name, callback_data=f"img_style_{style_id}"))
        
        # Add remaining buttons in the last row
        if row:
            keyboard.append(row)
            
        # Add regenerate and feedback buttons in new rows
        keyboard.append([InlineKeyboardButton("🔄 Regenerate", callback_data="img_regenerate_default")])
        keyboard.append([InlineKeyboardButton("⭐ Rate this image", callback_data="img_feedback_default")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def generate_unique_filename(user_id: int, style: Optional[str] = None) -> str:
        """
        Generate a unique filename for an image
        
        Args:
            user_id: User ID for the image
            style: Optional style for the image
            
        Returns:
            Unique filename string
        """
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        style_suffix = f"_{style}" if style else ""
        
        return f"{user_id}_{timestamp}{style_suffix}_{unique_id}.jpg"
    
    @staticmethod
    async def store_user_image(user_id: int, filename: str, prompt: str, 
                               style: Optional[str] = None) -> None:
        """
        Store image metadata in database for user-specific caching
        
        Args:
            user_id: Telegram user ID
            filename: Generated image filename
            prompt: Text prompt used to generate the image
            style: Optional style used for generation
        """
        try:
            # Get collection from DatabaseService
            user_images_collection = get_user_images_collection()
            
            # Create or update user's image cache
            user_images_collection.update_one(
                {"user_id": user_id},
                {"$push": {
                    "images": {
                        "filename": filename,
                        "prompt": prompt,
                        "style": style,
                        "timestamp": datetime.now(),
                        "file_id": None  # Will be updated when we have a Telegram file_id
                    }
                }},
                upsert=True
            )
            logger.info(f"Stored image metadata for user {user_id}: {filename}")
            
        except Exception as e:
            logger.error(f"Error storing user image metadata: {str(e)}")
    
    @staticmethod
    async def update_image_file_id(user_id: int, filename: str, file_id: str) -> None:
        """
        Update an image entry with the Telegram file_id for future reuse
        
        Args:
            user_id: Telegram user ID
            filename: Original image filename
            file_id: Telegram file_id for the image
        """
        try:
            # Get collection from DatabaseService
            user_images_collection = get_user_images_collection()
            
            # Update the file_id in the image cache
            user_images_collection.update_one(
                {"user_id": user_id, "images.filename": filename},
                {"$set": {"images.$.file_id": file_id}}
            )
            logger.info(f"Updated file_id for image {filename} (user {user_id})")
            
        except Exception as e:
            logger.error(f"Error updating image file_id: {str(e)}")
    
    @staticmethod
    async def get_user_recent_images(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent images for a user from cache
        
        Args:
            user_id: Telegram user ID
            limit: Maximum number of images to retrieve
            
        Returns:
            List of image metadata dictionaries
        """
        try:
            # Get collection from DatabaseService
            user_images_collection = get_user_images_collection()
            
            # Find the user's image cache
            user_cache = user_images_collection.find_one({"user_id": user_id})
            
            if not user_cache or "images" not in user_cache:
                return []
            
            # Get the most recent images and reverse to have newest first
            recent_images = user_cache["images"][-limit:]
            recent_images.reverse()
            
            return recent_images
            
        except Exception as e:
            logger.error(f"Error retrieving user images: {str(e)}")
            return []
    
    @staticmethod
    async def clear_user_image_cache(user_id: int) -> bool:
        """
        Clear a user's image cache
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get collection from DatabaseService
            user_images_collection = get_user_images_collection()
            
            # Remove the user's image cache
            result = user_images_collection.delete_one({"user_id": user_id})
            
            if result.deleted_count > 0:
                logger.info(f"Cleared image cache for user {user_id}")
                return True
            
            logger.info(f"No image cache found for user {user_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error clearing user image cache: {str(e)}")
            return False
    
    @staticmethod
    async def store_prompt(user_id: int, prompt: str, context: Optional[str] = None) -> None:
        """
        Store a prompt in the database for future reference
        
        Args:
            user_id: Telegram user ID
            prompt: The prompt text
            context: Optional context or category for the prompt
        """
        try:
            # Get collection from DatabaseService
            prompt_storage = get_prompt_storage_collection()
            
            # Store the prompt
            prompt_storage.insert_one({
                "user_id": user_id,
                "prompt": prompt,
                "context": context,
                "timestamp": datetime.now()
            })
            
        except Exception as e:
            logger.error(f"Error storing prompt: {str(e)}")
    
    @staticmethod
    async def delete_local_image(filename: str) -> None:
        """
        Delete a local image file after it's been sent to Telegram
        
        Args:
            filename: Image file path to delete
        """
        try:
            # Use os.path to ensure we're safely handling paths
            if os.path.exists(filename) and os.path.isfile(filename):
                os.remove(filename)
                logger.info(f"Deleted local image file: {filename}")
        except Exception as e:
            logger.error(f"Error deleting local image file {filename}: {str(e)}") 