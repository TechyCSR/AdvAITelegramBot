import os
import random
import asyncio
import concurrent.futures
from pyrogram.types import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import Client, filters
from pymongo import MongoClient
from ImgGenModel.g4f.client import Client as ImageClient
from ImgGenModel.g4f.Provider import BingCreateImages, PollinationsAI
from ImgGenModel.g4f.cookies import set_cookies
from config import BING_COOKIE, DATABASE_URL, LOG_CHANNEL
import requests
from datetime import datetime
import time
import logging
import json

# Get the logger
logger = logging.getLogger(__name__)

mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
user_images_collection = db['user_images']
image_feedback_collection = db['image_feedback']  # New collection for tracking feedback

# Store active generations to track them
active_generations = {}

# Function to generate images with improved error handling and performance
async def generate_images(prompt, max_images=4, style="realistic"):
    """Optimized image generation function with parallel processing"""
    logger.info(f"Generating images with prompt: '{prompt}', style: '{style}'")
    generated_images = 0
    total_attempts = 0
    max_attempts = 2  # Reduced retry attempts for faster response
    image_urls = []
    
    # Try PollinationsAI first (faster) and fall back to default if needed
    providers = ["PollinationsAI", "Bing", None]
    
    for provider in providers:
        if generated_images >= max_images:
            break
            
        client = ImageClient()
        try:
            # Set provider if specified
            provider_obj = None
            model_name = "dall-e-3"  # Default model
            
            if provider == "PollinationsAI":
                try:
                    provider_obj = PollinationsAI
                    # PollinationsAI doesn't support stable-diffusion explicitly
                    # It uses its own internal model, so don't specify model name
                    model_name = None
                    logger.info(f"Using PollinationsAI provider with its default model")
                except Exception as e:
                    logger.error(f"Failed to use PollinationsAI provider: {str(e)}")
                    continue
            
            # Create a complete prompt with style
            styled_prompt = f"{prompt} in {style} style"
            
            # Faster resolution for faster generation
            width = 1024
            height = 1024
            
            # Use async generation with timeout
            logger.info(f"Starting image generation with provider: {provider or 'default'}, model: {model_name or 'provider default'}")
            
            # Prepare generation parameters based on provider
            generation_kwargs = {
                "prompt": styled_prompt,
                "n": max_images - generated_images,
                "provider": provider_obj,
                "width": width,
                "height": height,
                "quality": "standard"  # Use standard quality for faster generation
            }
            
            # Only add model parameter if it's specified (for providers that need it)
            if model_name:
                generation_kwargs["model"] = model_name
                
            # Call the API with the appropriate parameters
            response = await asyncio.wait_for(
                client.images.async_generate(**generation_kwargs),
                timeout=15  # Set timeout to prevent hanging
            )
            
            # Process the response
            for image_data in response.data:
                image_urls.append(image_data.url)
                generated_images += 1
                
                if generated_images >= max_images:
                    break
                    
            # If we got at least some images, consider it successful
            if generated_images > 0:
                logger.info(f"Successfully generated {generated_images} images")
                break
                
        except asyncio.TimeoutError:
            logger.warning(f"Image generation timed out with provider {provider}")
            print(f"Image generation timed out with provider {provider}")
            continue
        except Exception as e:
            logger.error(f"Error generating image with provider {provider}: {str(e)}")
            print(f"Error generating image with provider {provider}: {str(e)}")
            continue
    
    if not image_urls:
        logger.error("Failed to generate any images")
        return None, "Failed to generate images. Please try a different prompt or try again later."
    
    # Process URLs to local paths
    image_urls = [u.replace("/images/", "./generated_images/") for u in image_urls]
    return image_urls, None


# Telegram bot command handler for generating images with modern UI
async def generate_command(client, message, prompt, reply_to_message_id=None, regenerate=False, feedback_msg=None):
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username or f"user_{user_id}"
    
    logger.info(f"Image generation command from user {user_id} with prompt: '{prompt}'")
    
    # Record metadata about this generation
    generation_id = f"{user_id}_{int(time.time())}"
    generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    active_generations[generation_id] = {
        "prompt": prompt,
        "status": "processing",
        "user_id": user_id,
        "chat_id": chat_id,
        "timestamp": generation_time,
        "regenerated": regenerate
    }
    
    # Parse parameters from prompt if any
    style_options = ["realistic", "cartoon", "artistic", "3d", "sketch"]
    style = "realistic"  # Default style
    
    # Check if any style keywords are in the prompt
    for option in style_options:
        if f"style:{option}" in prompt.lower():
            style = option
            prompt = prompt.replace(f"style:{option}", "").strip()
    
    # If regenerating, delete the feedback message if it exists
    if regenerate and feedback_msg:
        try:
            await feedback_msg.delete()
            logger.info(f"Deleted previous feedback message for regeneration")
        except Exception as e:
            logger.error(f"Error deleting feedback message: {e}")
    
    # Show processing status with modern UI
    processing_msg = await message.reply_text(
        "🎨 **Generating Images**\n\n"
        f"Creating visuals for: `{prompt}`\n"
        f"Style: `{style}`\n\n"
        "Please wait while the AI works its magic...",
        reply_to_message_id=reply_to_message_id
    )
    
    # Generate images
    urls, error = await generate_images(prompt, style=style)
    
    # Handle errors
    if error:
        await processing_msg.edit_text(
            f"❌ **Image Generation Failed**\n\n{error}"
        )
        
        # Log the failure in a standardized format
        log_data = {
            "type": "image_generation_failed",
            "prompt": prompt,
            "style": style,
            "user_id": user_id,
            "username": username,
            "chat_id": chat_id,
            "error": error,
            "timestamp": generation_time
        }
        
        logger.error(f"Image generation failed: {json.dumps(log_data)}")
        
        try:
            await client.send_message(
                LOG_CHANNEL, 
                f"#ImgLog #Rejected\n**Prompt**: `{prompt}`\n**Style**: `{style}`\n**User**: {message.from_user.mention}\n**User ID**: {message.from_user.id}\n**Time**: {generation_time}\n**Chat ID**: {message.chat.id}\n**Error**: {error}"
            )
        except Exception as e:
            logger.error(f"Failed to send log to channel: {str(e)}")
            
        return 
    
    # Prepare media group with generated images
    media_group = []
    for i, url in enumerate(urls):
        caption = f"🖼️ **AI Generated Image**\n\nPrompt: `{prompt}`\nStyle: `{style}`" if i == 0 else ""
        media_group.append(InputMediaPhoto(url, caption=caption))
    
    # Delete processing message
    await processing_msg.delete()
    
    # Send generated images
    sent_message = await message.reply_media_group(
        media_group,
        reply_to_message_id=reply_to_message_id
    )
    
    # Create feedback buttons for the generated images
    feedback_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👍 Love it", callback_data=f"img_feedback_positive_{user_id}_{generation_id}"),
            InlineKeyboardButton("👎 Not good", callback_data=f"img_feedback_negative_{user_id}_{generation_id}")
        ],
        [InlineKeyboardButton("🔄 Regenerate", callback_data=f"img_regenerate_{user_id}_{prompt}")]
    ])
    
    # Send a follow-up message with the feedback buttons
    feedback_msg = await message.reply_text(
        "**How do you like these images?**\n\n"
        "Your feedback helps improve our AI.",
        reply_markup=feedback_markup,
        reply_to_message_id=sent_message[0].id if sent_message else None
    )
    
    # Store feedback message ID for potential regeneration
    active_generations[generation_id]["feedback_msg_id"] = feedback_msg.id
    active_generations[generation_id]["status"] = "completed"
    
    # Store image generation metadata in the database
    try:
        user_images_collection.insert_one({
            "generation_id": generation_id,
            "user_id": user_id,
            "prompt": prompt,
            "style": style,
            "timestamp": generation_time,
            "regenerated": regenerate,
            "image_count": len(urls)
        })
    except Exception as e:
        logger.error(f"Failed to store image metadata in database: {str(e)}")
    
    # Log images to log channel with a standardized format
    try:
        # First send the images
        sent_log_media = await client.send_media_group(LOG_CHANNEL, media_group)
        
        # Then send detailed metadata
        await client.send_message(
            LOG_CHANNEL, 
            f"#ImgLog #Generated\n**Prompt**: `{prompt}`\n**Style**: `{style}`\n**User**: {message.from_user.mention}\n**User ID**: {user_id}\n**Time**: {generation_time}\n**Chat ID**: {chat_id}\n**Images**: {len(urls)}\n**Regeneration**: {'Yes' if regenerate else 'No'}\n**Generation ID**: `{generation_id}`"
        )
        
        logger.info(f"Successfully logged image generation to channel. Generation ID: {generation_id}")
    except Exception as e:
        logger.error(f"Failed to send log to channel: {str(e)}")
    
    # Clean up image files
    for url in urls:
        try:
            os.remove(url)
        except Exception as e:
            logger.error(f"Failed to clean up image file {url}: {str(e)}")
    
    return feedback_msg

# Handle image feedback callback
async def handle_image_feedback(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username or f"user_{user_id}"
    feedback_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Extract user_id and generation_id from the callback data
    parts = data.split("_")
    feedback_type = None
    target_user_id = None
    generation_id = None
    
    if data.startswith("img_feedback_positive"):
        feedback_type = "positive"
        target_user_id = parts[3] if len(parts) > 3 else "unknown"
        generation_id = parts[4] if len(parts) > 4 else f"{target_user_id}_{int(time.time())}"
        
        logger.info(f"Positive image feedback received from user {user_id} for generation {generation_id}")
        await callback_query.answer("Thanks for your positive feedback!")
        await callback_query.message.edit_text(
            callback_query.message.text + "\n\n✅ *Feedback received: You liked the images!*",
            reply_markup=None
        )
        
        # Log positive feedback to channel
        try:
            await client.send_message(
                LOG_CHANNEL,
                f"#ImgLog #Feedback #Positive\n**User**: {callback_query.from_user.mention}\n**User ID**: {user_id}\n**Time**: {feedback_time}\n**Generation ID**: `{generation_id}`"
            )
        except Exception as e:
            logger.error(f"Failed to log positive feedback to channel: {str(e)}")
        
    elif data.startswith("img_feedback_negative"):
        feedback_type = "negative"
        target_user_id = parts[3] if len(parts) > 3 else "unknown"
        generation_id = parts[4] if len(parts) > 4 else f"{target_user_id}_{int(time.time())}"
        
        logger.info(f"Negative image feedback received from user {user_id} for generation {generation_id}")
        await callback_query.answer("Thanks for your feedback. We'll improve!")
        await callback_query.message.edit_text(
            callback_query.message.text + "\n\n📝 *Feedback received: We'll work to improve our image generation.*",
            reply_markup=None
        )
        
        # Log negative feedback to channel
        try:
            await client.send_message(
                LOG_CHANNEL,
                f"#ImgLog #Feedback #Negative\n**User**: {callback_query.from_user.mention}\n**User ID**: {user_id}\n**Time**: {feedback_time}\n**Generation ID**: `{generation_id}`"
            )
        except Exception as e:
            logger.error(f"Failed to log negative feedback to channel: {str(e)}")
        
    elif data.startswith("img_regenerate"):
        # Get the feedback message for deletion later
        feedback_msg = callback_query.message
        logger.info(f"Image regeneration requested by user {user_id}")
        await callback_query.answer("Regenerating images...")
        
        # Extract prompt from callback data
        parts = data.split("_")
        target_user_id = parts[2]
        prompt = "_".join(parts[3:])
        
        # Get the original message that this feedback is replying to
        reply_to_message_id = None
        if hasattr(feedback_msg, 'reply_to_message_id') and feedback_msg.reply_to_message_id:
            reply_to_message_id = feedback_msg.reply_to_message_id
        
        # Log regeneration to channel
        try:
            await client.send_message(
                LOG_CHANNEL,
                f"#ImgLog #Regenerate\n**User**: {callback_query.from_user.mention}\n**User ID**: {user_id}\n**Time**: {feedback_time}\n**Prompt**: `{prompt}`"
            )
        except Exception as e:
            logger.error(f"Failed to log regeneration to channel: {str(e)}")
        
        # Generate new images, passing feedback message for deletion
        await generate_command(
            client, 
            callback_query.message, 
            prompt, 
            reply_to_message_id=reply_to_message_id,
            regenerate=True,
            feedback_msg=feedback_msg
        )
    
    # Store feedback in database if we have valid feedback
    if feedback_type and target_user_id and generation_id:
        try:
            image_feedback_collection.insert_one({
                "generation_id": generation_id,
                "user_id": user_id,
                "feedback_type": feedback_type,
                "timestamp": feedback_time
            })
            logger.info(f"Stored {feedback_type} feedback in database for generation {generation_id}")
        except Exception as e:
            logger.error(f"Failed to store feedback in database: {str(e)}")



