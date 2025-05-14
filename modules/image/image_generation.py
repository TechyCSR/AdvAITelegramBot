import os
import random
import asyncio
import logging
import time
from datetime import datetime
import json
from typing import Dict, List, Optional, Tuple, Union
import re
import hashlib

from pyrogram.types import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram import Client, filters
from pymongo import MongoClient
from ImgGenModel.g4f.client import Client as ImageClient
from ImgGenModel.g4f.Provider import PollinationsAI
from config import DATABASE_URL, LOG_CHANNEL

# Get the logger
logger = logging.getLogger(__name__)

# MongoDB setup
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
user_images_collection = db['user_images']
image_feedback_collection = db['image_feedback']
prompt_storage_collection = db['prompt_storage']  # New collection for storing prompts

# In-memory prompt storage as fallback (will be cached to DB)
prompt_storage = {}

# Constants for style definitions
STYLE_DEFINITIONS = {
    "realistic": {
        "name": "Realistic",
        "description": "Photo-realistic, detailed images",
        "prompt_additions": "ultra realistic, detailed, photographic quality",
        "button_text": "🖼️ Realistic"
    },
    "artistic": {
        "name": "Artistic",
        "description": "Creative, artistic style like a painting",
        "prompt_additions": "artistic style, creative, vibrant colors, painting-like",
        "button_text": "🎨 Artistic"
    },
    "sketch": {
        "name": "Sketch",
        "description": "Hand-drawn sketch or drawing style",
        "prompt_additions": "hand-drawn sketch, pencil drawing, line art, sketched appearance",
        "button_text": "✏️ Sketch"
    },
    "cartoon": {
        "name": "Cartoon",
        "description": "Fun cartoon or animated style",
        "prompt_additions": "cartoon style, animated look, colorful, simplified features",
        "button_text": "🧸 Cartoon"
    },
    "3d": {
        "name": "3D Render",
        "description": "3D rendered style with depth and texture",
        "prompt_additions": "3D render, volumetric lighting, high detail, realistic textures, depth",
        "button_text": "🌟 3D Render"
    }
}

# ====== PROMPT STORAGE FUNCTIONS ======

def store_prompt(user_id: int, prompt: str) -> str:
    """Store a prompt and return a short hash ID for callback data
    
    Args:
        user_id: The user's ID
        prompt: The prompt to store
        
    Returns:
        A short hash ID for use in callback data
    """
    # Create a hash of the prompt and user ID
    hash_object = hashlib.md5(f"{user_id}:{prompt}".encode())
    prompt_id = hash_object.hexdigest()[:8]  # Use first 8 chars of hash
    
    # Store in memory cache
    prompt_storage[prompt_id] = prompt
    
    # Also store in database for persistence
    try:
        prompt_storage_collection.update_one(
            {"prompt_id": prompt_id},
            {"$set": {
                "user_id": user_id,
                "prompt": prompt,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Failed to store prompt in database: {str(e)}")
    
    return prompt_id

def get_prompt(prompt_id: str) -> Optional[str]:
    """Retrieve a prompt from storage
    
    Args:
        prompt_id: The hash ID for the prompt
        
    Returns:
        The stored prompt or None if not found
    """
    # Try memory cache first
    if prompt_id in prompt_storage:
        return prompt_storage[prompt_id]
    
    # Fall back to database
    try:
        result = prompt_storage_collection.find_one({"prompt_id": prompt_id})
        if result and "prompt" in result:
            # Update memory cache
            prompt_storage[prompt_id] = result["prompt"]
            return result["prompt"]
    except Exception as e:
        logger.error(f"Failed to retrieve prompt from database: {str(e)}")
    
    return None

# ====== USER STATE MANAGEMENT ======

class UserGenerationState:
    """Tracks a user's current image generation state"""
    def __init__(self, user_id: int, prompt: str):
        self.user_id = user_id
        self.prompt = prompt
        self.style = None
        self.style_msg_id = None
        self.style_msg_chat_id = None
        self.is_processing = False
        self.created_at = time.time()
        
    def is_active(self) -> bool:
        """Check if this state is still valid and not expired"""
        return time.time() - self.created_at < 600  # 10 minute expiration
    
    def set_style(self, style: str) -> None:
        """Set the selected style"""
        if style in STYLE_DEFINITIONS:
            self.style = style
        else:
            self.style = "realistic"  # Default to realistic if invalid style
            
    def set_processing(self, is_processing: bool) -> None:
        """Set processing state"""
        self.is_processing = is_processing
        
    def set_style_message(self, message: Message) -> None:
        """Store reference to the style selection message"""
        if message and hasattr(message, 'id') and hasattr(message, 'chat'):
            self.style_msg_id = message.id
            self.style_msg_chat_id = message.chat.id

# Global state storage
user_states: Dict[int, UserGenerationState] = {}

# ====== CORE IMAGE GENERATION ======

async def generate_images(prompt: str, style: str, max_images: int = 3) -> Tuple[Optional[List[str]], Optional[str]]:
    """Generate images using available providers
    
    Args:
        prompt: The text prompt for image generation
        style: The style to apply (one of the keys in STYLE_DEFINITIONS)
        max_images: Maximum number of images to generate
        
    Returns:
        Tuple of (list of image URLs or None, error message or None)
    """
    logger.info(f"Generating images with prompt: '{prompt}', style: '{style}'")
    
    # Get style definition
    style_info = STYLE_DEFINITIONS.get(style, STYLE_DEFINITIONS["realistic"])
    
    # Create enhanced prompt with style additions
    enhanced_prompt = f"{prompt}, {style_info['prompt_additions']}"
    logger.info(f"Enhanced prompt: '{enhanced_prompt}'")
    
    generated_images = 0
    image_urls = []
    min_images = 2  # Always generate at least 2 images
    
    # Try providers in sequence - PollinationsAI first, then fallback to default
    providers = ["PollinationsAI", None]
    
    for provider in providers:
        if generated_images >= max_images:
            break
            
        client = ImageClient()
        try:
            # Prepare provider configuration
            provider_obj = None
            model_name = "dall-e-3"  # Default model
            
            if provider == "PollinationsAI":
                try:
                    provider_obj = PollinationsAI
                    model_name = None  # PollinationsAI uses its own model
                    logger.info(f"Using PollinationsAI provider")
                except Exception as e:
                    logger.error(f"Failed to use PollinationsAI provider: {str(e)}")
                    continue
            
            # Standard image size
            width = 1024
            height = 1024
            
            # Prepare generation parameters
            generation_kwargs = {
                "prompt": enhanced_prompt,
                "n": max_images - generated_images,
                "provider": provider_obj,
                "width": width,
                "height": height,
                "quality": "standard"
            }
            
            # Only add model parameter if specified
            if model_name:
                generation_kwargs["model"] = model_name
                
            # Generate with timeout
            logger.info(f"Sending generation request with provider {provider}")
            response = await asyncio.wait_for(
                client.images.async_generate(**generation_kwargs),
                timeout=30  # Longer timeout for better results
            )
            
            # Process response
            for image_data in response.data:
                image_urls.append(image_data.url)
                generated_images += 1
                
                if generated_images >= max_images:
                    break
                    
            # Stop if we have enough images
            if generated_images >= min_images:
                logger.info(f"Successfully generated {generated_images} images")
                break
                
        except asyncio.TimeoutError:
            logger.warning(f"Image generation timed out with provider {provider}")
            continue
        except Exception as e:
            logger.error(f"Error generating image with provider {provider}: {str(e)}")
            continue
    
    if not image_urls:
        return None, "Failed to generate images. Please try a different prompt or try again later."
    
    # Process URLs to local paths
    image_urls = [u.replace("/images/", "./generated_images/") for u in image_urls]
    return image_urls, None

# ====== UI COMPONENTS ======

async def update_generation_progress(client: Client, chat_id: int, message_id: int, prompt: str, style: str) -> None:
    """Show a dynamic progress indicator while generating images"""
    progress_stages = [
        "⏳ Analyzing your prompt...",
        "🧠 Crafting initial concepts...",
        "🎨 Applying artistic elements...", 
        "✨ Applying finishing touches...",
        "📷 Rendering final images..."
    ]
    
    style_info = STYLE_DEFINITIONS.get(style, STYLE_DEFINITIONS["realistic"])
    
    try:
        for i, stage in enumerate(progress_stages):
            # Wait between updates
            if i > 0:
                await asyncio.sleep(2.5)
            
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"🎭 **Generating Images**\n\n"
                f"Your prompt: `{prompt}`\n\n"
                f"Style: `{style_info['name']}`\n\n"
                f"{stage}"
            )
    except asyncio.CancelledError:
        logger.info("Progress updater cancelled as generation completed")
    except Exception as e:
        logger.error(f"Error updating generation progress: {str(e)}")

# ====== HANDLERS ======

async def handle_generate_command(client: Client, message: Message) -> None:
    """Handler for /generate, /gen, /image, /img commands"""
    if not isinstance(message, Message):
        logger.error(f"Invalid message object in handle_generate_command: {type(message)}")
        return
        
    user_id = message.from_user.id
    
    try:
        # Get the prompt from the message
        if len(message.text.split()) > 1:
            prompt = message.text.split(None, 1)[1]
        else:
            await message.reply_text(
                "🖼️ **Image Generation**\n\n"
                "Please provide a prompt to generate images.\n\n"
                "Example: `/generate a serene mountain landscape`\n\n"
                "You'll be able to choose from several artistic styles after entering your prompt."
            )
            return
            
        # Check if user already has an active generation
        if user_id in user_states and user_states[user_id].is_processing:
            await message.reply_text(
                "⏳ I'm already working on your previous image request. Please wait for it to complete."
            )
            return
            
        # Show style selection to start the process
        await show_style_selection(client, message, prompt)
        
    except Exception as e:
        logger.error(f"Error in image generation command handler: {str(e)}")
        await message.reply_text(f"❌ **Error**\n\nFailed to process image generation request: {str(e)}")

async def handle_feedback(client: Client, callback_query: CallbackQuery) -> None:
    """Handle feedback and regeneration callbacks"""
    data = callback_query.data
    user_id = callback_query.from_user.id
    feedback_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        parts = data.split("_")
        
        # Handle different callback types
        if data.startswith("img_style_"):
            # Style selection - handled by process_style_selection
            await process_style_selection(client, callback_query)
            return
            
        elif data.startswith("img_feedback_positive_"):
            # Positive feedback
            if len(parts) < 5:
                await callback_query.answer("Invalid feedback data.")
                return
                
            target_user_id = parts[3]
            generation_id = parts[4]
            
            await callback_query.answer("Thanks for your positive feedback!")
            await callback_query.message.edit_text(
                callback_query.message.text + "\n\n✅ *Feedback received: You liked the images!*",
                reply_markup=None
            )
            
            # Log positive feedback
            try:
                await client.send_message(
                    LOG_CHANNEL,
                    f"#ImgLog #Feedback #Positive\n**User ID**: {user_id}\n**Time**: {feedback_time}\n**Generation ID**: `{generation_id}`"
                )
                
                # Store in database
                image_feedback_collection.insert_one({
                    "generation_id": generation_id,
                    "user_id": user_id,
                    "feedback_type": "positive",
                    "timestamp": feedback_time
                })
            except Exception as e:
                logger.error(f"Failed to log positive feedback: {str(e)}")
                
        elif data.startswith("img_feedback_negative_"):
            # Negative feedback
            if len(parts) < 5:
                await callback_query.answer("Invalid feedback data.")
                return
                
            target_user_id = parts[3]
            generation_id = parts[4]
            
            await callback_query.answer("Thanks for your feedback. We'll improve!")
            await callback_query.message.edit_text(
                callback_query.message.text + "\n\n📝 *Feedback received: We'll work to improve our image generation.*",
                reply_markup=None
            )
            
            # Log negative feedback
            try:
                await client.send_message(
                    LOG_CHANNEL,
                    f"#ImgLog #Feedback #Negative\n**User ID**: {user_id}\n**Time**: {feedback_time}\n**Generation ID**: `{generation_id}`"
                )
                
                # Store in database
                image_feedback_collection.insert_one({
                    "generation_id": generation_id,
                    "user_id": user_id,
                    "feedback_type": "negative",
                    "timestamp": feedback_time
                })
            except Exception as e:
                logger.error(f"Failed to log negative feedback: {str(e)}")
                
        elif data.startswith("img_regenerate_"):
            # Regeneration request
            if len(parts) < 3:
                await callback_query.answer("Invalid regenerate data.")
                return
                
            target_user_id = int(parts[2])
            prompt_id = parts[3]
            
            # Retrieve the original prompt from storage
            prompt = get_prompt(prompt_id)
            if not prompt:
                logger.error(f"Failed to retrieve prompt with ID {prompt_id}")
                await callback_query.answer("Error: Could not find the original prompt. Please try a new image generation.")
                return
            
            # Verify user
            if user_id != target_user_id:
                await callback_query.answer("You can only regenerate your own images.")
                return
                
            # Check if already processing
            if user_id in user_states and user_states[user_id].is_processing:
                await callback_query.answer("Already generating images, please wait...")
                return
                
            # Delete the feedback message
            try:
                await callback_query.message.delete()
                logger.info(f"Deleted regeneration feedback message")
            except Exception as e:
                logger.error(f"Error deleting feedback message: {e}")
                
            # Log regeneration
            try:
                await client.send_message(
                    LOG_CHANNEL,
                    f"#ImgLog #Regenerate\n**User ID**: {user_id}\n**Time**: {feedback_time}\n**Prompt**: `{prompt}`"
                )
            except Exception as e:
                logger.error(f"Failed to log regeneration: {str(e)}")
                
            # Show style selection again - don't use message object approach
            # Instead, send a new style selection directly
            # Create or update the user's generation state first
            user_states[user_id] = UserGenerationState(user_id, prompt)
            
            # Create style selection buttons
            keyboard = []
            row = []
            
            for i, (style_id, style_info) in enumerate(STYLE_DEFINITIONS.items()):
                button = InlineKeyboardButton(
                    style_info["button_text"], 
                    callback_data=f"img_style_{style_id}_{user_id}"
                )
                
                row.append(button)
                if len(row) == 2 or i == len(STYLE_DEFINITIONS) - 1:
                    keyboard.append(row)
                    row = []
            
            style_markup = InlineKeyboardMarkup(keyboard)
            
            # Send the style selection message directly
            style_msg = await client.send_message(
                chat_id=callback_query.message.chat.id,
                text=f"🎭 **Choose Image Style for Regeneration**\n\n"
                f"Your prompt: `{prompt}`\n\n"
                f"Please select a style for your image:",
                reply_markup=style_markup
            )
            
            # Save message info in user state
            user_states[user_id].style_msg_id = style_msg.id
            user_states[user_id].style_msg_chat_id = style_msg.chat.id
            
            logger.info(f"Sent regeneration style selection for user {user_id} with prompt: '{prompt}'")
            
    except Exception as e:
        logger.error(f"Error handling feedback: {str(e)}")
        await callback_query.answer("Error processing your request.")

# ====== BACKWARD COMPATIBILITY FUNCTIONS ======

# Alias for backward compatibility with existing imports
generate_command = handle_generate_command
handle_image_feedback = handle_feedback

# Change callback data prefixes back to what's expected in run.py
async def show_style_selection(client: Client, message: Message, prompt: str) -> Message:
    """Show style selection buttons to the user"""
    user_id = message.from_user.id
    
    # Create or update the user's generation state
    user_states[user_id] = UserGenerationState(user_id, prompt)
    
    # Create style selection buttons
    keyboard = []
    row = []
    
    for i, (style_id, style_info) in enumerate(STYLE_DEFINITIONS.items()):
        button = InlineKeyboardButton(
            style_info["button_text"], 
            callback_data=f"img_style_{style_id}_{user_id}"  # Changed to match run.py expectations
        )
        
        row.append(button)
        if len(row) == 2 or i == len(STYLE_DEFINITIONS) - 1:
            keyboard.append(row)
            row = []
    
    style_markup = InlineKeyboardMarkup(keyboard)
    
    # Send the style selection message
    style_msg = await message.reply_text(
        f"🎭 **Choose Image Style**\n\n"
        f"Your prompt: `{prompt}`\n\n"
        f"Please select a style for your image:",
        reply_markup=style_markup
    )
    
    # Save message info in user state
    user_states[user_id].set_style_message(style_msg)
    
    logger.info(f"Sent style selection for user {user_id} with prompt: '{prompt}'")
    return style_msg

async def process_style_selection(client: Client, callback_query: CallbackQuery) -> None:
    """Process a style selection callback"""
    try:
        # Extract data from callback
        data = callback_query.data
        clicked_user_id = callback_query.from_user.id
        
        # Check callback format (img_style_{style}_{user_id})
        parts = data.split("_")
        if len(parts) < 4 or parts[0] != "img" or parts[1] != "style":
            await callback_query.answer("Invalid selection. Please try again.")
            return
            
        style = parts[2]  # The selected style
        target_user_id = int(parts[3])  # User this selection is for
        
        logger.info(f"Style selection: user={clicked_user_id}, style={style}, target={target_user_id}")
        
        # Only allow users to select styles for their own requests
        # For regeneration, we should always match the current user
        if clicked_user_id != target_user_id and target_user_id != clicked_user_id:
            logger.warning(f"User mismatch: clicked_user={clicked_user_id}, target_user={target_user_id}")
            await callback_query.answer("This isn't your image request.")
            return
            
        # Use the current user's ID as the real target (important for regeneration flow)
        real_user_id = clicked_user_id
            
        # Check if the user has an active state
        if real_user_id not in user_states:
            # If there's no state yet but this is a valid request from the user,
            # create a new state for them (helpful for regeneration flow)
            if callback_query.message and callback_query.message.text:
                # Try to extract prompt from the message text
                match = re.search(r"Your prompt: `(.*?)`", callback_query.message.text)
                if match:
                    prompt = match.group(1)
                    # Create a new state for this user
                    user_states[real_user_id] = UserGenerationState(real_user_id, prompt)
                    logger.info(f"Created new state for user {real_user_id} with prompt: {prompt}")
                else:
                    await callback_query.answer("Your request has expired. Please make a new request.")
                    return
            else:
                await callback_query.answer("Your request has expired. Please make a new request.")
                return
            
        # Get the user's state
        state = user_states[real_user_id]
        
        # Check if already processing
        if state.is_processing:
            await callback_query.answer("Already generating your images, please wait...")
            return
            
        # Set state to processing to prevent duplicate requests
        state.set_processing(True)
        state.set_style(style)
        
        # Get style info
        style_info = STYLE_DEFINITIONS.get(style, STYLE_DEFINITIONS["realistic"])
        
        # Acknowledge the selection
        await callback_query.answer(f"Generating images in {style_info['name']} style...")
        
        # Update the message to show processing
        await client.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.id,
            text=f"🎭 **Generating Images**\n\n"
            f"Your prompt: `{state.prompt}`\n\n"
            f"Style: `{style_info['name']}`\n\n"
            f"⏳ The AI is working its magic... Creating something special for you!"
        )
        
        # Start the progress updater
        progress_task = asyncio.create_task(
            update_generation_progress(
                client, 
                callback_query.message.chat.id, 
                callback_query.message.id, 
                state.prompt, 
                style
            )
        )
        
        # Start the actual image generation
        await generate_and_send_images(
            client,
            callback_query.message,  
            state.prompt,
            style,
            progress_task
        )
        
    except Exception as e:
        logger.error(f"Error processing style selection: {str(e)}")
        try:
            await callback_query.message.edit_text(
                f"❌ **Error**\n\nFailed to process style selection: {str(e)}"
            )
        except Exception:
            pass
            
        # Reset user state
        if clicked_user_id in user_states:
            user_states[clicked_user_id].set_processing(False)

async def generate_and_send_images(client: Client, message: Message, prompt: str, style: str, progress_task=None) -> None:
    """Generate images and send them to the user"""
    user_id = message.chat.id
    generation_id = f"{user_id}_{int(time.time())}"
    generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # Generate the images
        urls, error = await generate_images(prompt, style)
        
        # Cancel progress updater if it exists
        if progress_task and not progress_task.done():
            progress_task.cancel()
        
        # Handle generation errors
        if error:
            style_info = STYLE_DEFINITIONS.get(style, STYLE_DEFINITIONS["realistic"])
            await client.send_message(
                chat_id=message.chat.id,
                text=f"❌ **Image Generation Failed**\n\n{error}\n\nPlease try a different prompt or style."
            )
            
            # Log the error
            try:
                await client.send_message(
                    LOG_CHANNEL,
                    f"#ImgLog #Rejected\n**Prompt**: `{prompt}`\n**Style**: `{style_info['name']}`\n"\
                    f"**User ID**: {user_id}\n**Time**: {generation_time}\n**Error**: {error}"
                )
            except Exception as e:
                logger.error(f"Failed to log error to channel: {str(e)}")
                
            return
            
        # Delete the style/processing message
        try:
            if hasattr(message, 'id'):
                await client.delete_messages(message.chat.id, message.id)
        except Exception as e:
            logger.error(f"Error deleting message: {str(e)}")
        
        # Get style info
        style_info = STYLE_DEFINITIONS.get(style, STYLE_DEFINITIONS["realistic"])
        
        # Prepare media group with generated images
        media_group = []
        for i, url in enumerate(urls):
            caption = f"🖼️ **AI Generated Image**\n\nPrompt: `{prompt}`\nStyle: `{style_info['name']}`" if i == 0 else ""
            media_group.append(InputMediaPhoto(url, caption=caption))
        
        # Send generated images
        sent_message = await client.send_media_group(
            chat_id=message.chat.id,
            media=media_group
        )
        
        # Store the prompt for potential regeneration
        prompt_id = store_prompt(user_id, prompt)
        
        # Create feedback buttons
        feedback_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👍 Love it", callback_data=f"img_feedback_positive_{user_id}_{generation_id}"),
                InlineKeyboardButton("👎 Not good", callback_data=f"img_feedback_negative_{user_id}_{generation_id}")
            ],
            [InlineKeyboardButton("🔄 Regenerate", callback_data=f"img_regenerate_{user_id}_{prompt_id}")]
        ])
        
        # Send feedback message
        feedback_msg = await client.send_message(
            chat_id=message.chat.id,
            text="**How do you like these images?**\n\nYour feedback helps improve our AI.",
            reply_markup=feedback_markup,
            reply_to_message_id=sent_message[0].id if sent_message else None
        )
        
        # Store metadata in database
        try:
            user_images_collection.insert_one({
                "generation_id": generation_id,
                "user_id": user_id,
                "prompt": prompt,
                "style": style,
                "timestamp": generation_time,
                "image_count": len(urls)
            })
        except Exception as e:
            logger.error(f"Failed to store image metadata: {str(e)}")
        
        # Log to channel
        try:
            # Send images to log channel
            await client.send_media_group(LOG_CHANNEL, media_group)
            
            # Send metadata
            await client.send_message(
                LOG_CHANNEL,
                f"#ImgLog #Generated\n**Prompt**: `{prompt}`\n**Style**: `{style_info['name']}`\n"\
                f"**User ID**: {user_id}\n**Time**: {generation_time}\n"\
                f"**Images**: {len(urls)}\n**Generation ID**: `{generation_id}`"
            )
        except Exception as e:
            logger.error(f"Failed to log to channel: {str(e)}")
        
        # Clean up image files
        for url in urls:
            try:
                os.remove(url)
            except Exception as e:
                logger.error(f"Failed to clean up image file: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error in image generation: {str(e)}")
        await client.send_message(
            chat_id=message.chat.id,
            text=f"❌ **Error**\n\nFailed to generate images: {str(e)}"
        )
    finally:
        # Clear user state processing flag
        if user_id in user_states:
            user_states[user_id].set_processing(False)

# ====== CLEANUP ======

def start_cleanup_scheduler():
    """Start the background cleanup scheduler"""
    
    async def run_scheduled_cleanup():
        """Background task to regularly clean up old states"""
        logger.info("Started image generation cleanup scheduler")
        while True:
            await asyncio.sleep(3600)  # Run every hour
            
            # Clean up expired user states
            to_remove = []
            current_time = time.time()
            for user_id, state in user_states.items():
                if current_time - state.created_at > 600:  # 10 minute expiration
                    to_remove.append(user_id)
                    
            for user_id in to_remove:
                del user_states[user_id]
                
            logger.info(f"Cleaned up {len(to_remove)} expired user states")
            
    # Return the coroutine function so it can be scheduled by the bot
    return run_scheduled_cleanup



