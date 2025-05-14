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


mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
user_images_collection = db['user_images']

# Store active generations to track them
active_generations = {}

# Function to generate images with improved error handling and performance
async def generate_images(prompt, max_images=4, style="realistic"):
    """Optimized image generation function with parallel processing"""
    generated_images = 0
    total_attempts = 0
    max_attempts = 2  # Reduced retry attempts for faster response
    image_urls = []
    
    # Try PollinationsAI first (faster) and fall back to default if needed
    providers = ["PollinationsAI", None]  # None = default provider
    
    for provider in providers:
        if generated_images >= max_images:
            break
            
        client = ImageClient()
        try:
            # Set provider if specified
            provider_obj = None
            if provider == "PollinationsAI":
                try:
                    provider_obj = PollinationsAI
                except Exception:
                    continue
            
            # Create a complete prompt with style
            styled_prompt = f"{prompt} in {style} style"
            
            # Faster resolution for faster generation
            width = 1024
            height = 1024
            
            # Use async generation with timeout
            response = await asyncio.wait_for(
                client.images.async_generate(
                    model="dall-e-3" if not provider else "stable-diffusion",
                    prompt=styled_prompt,
                    n=max_images - generated_images,
                    provider=provider_obj,
                    width=width,
                    height=height,
                    quality="standard"  # Use standard quality for faster generation
                ),
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
                break
                
        except asyncio.TimeoutError:
            print(f"Image generation timed out with provider {provider}")
            continue
        except Exception as e:
            print(f"Error generating image with provider {provider}: {str(e)}")
            continue
    
    if not image_urls:
        return None, "Failed to generate images. Please try a different prompt or try again later."
    
    # Process URLs to local paths
    image_urls = [u.replace("/images/", "./generated_images/") for u in image_urls]
    return image_urls, None


# Telegram bot command handler for generating images with modern UI
async def generate_command(client, message, prompt, reply_to_message_id=None, regenerate=False, feedback_msg=None):
    user_id = message.from_user.id
    # Store this generation for tracking
    generation_id = f"{user_id}_{int(time.time())}"
    active_generations[generation_id] = {
        "prompt": prompt,
        "status": "processing"
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
        except Exception as e:
            print(f"Error deleting feedback message: {e}")
    
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
        try:
            await client.send_message(
                LOG_CHANNEL, 
                f"#ImgLog #Rejected\nPrompt: {prompt}\nStyle: {style}\n**User**: {message.from_user.mention}\n**User ID**: {message.from_user.id}\n**Time**: {datetime.now()}\n**Chat ID**: {message.chat.id}\n"
            )
        except Exception:
            pass  # Don't fail if logging fails
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
            InlineKeyboardButton("👍 Love it", callback_data=f"img_feedback_positive_{user_id}"),
            InlineKeyboardButton("👎 Not good", callback_data=f"img_feedback_negative_{user_id}")
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
    
    # Log images to log channel
    try:
        await client.send_media_group(LOG_CHANNEL, media_group)
        await client.send_message(
            LOG_CHANNEL, 
            f"#ImgLog\nPrompt: {prompt}\nStyle: {style}\n**User**: {message.from_user.mention}\n**User ID**: {message.from_user.id}\n**Time**: {datetime.now()}\n**Chat ID**: {message.chat.id}\n"
        )
    except Exception:
        pass  # Don't fail if logging fails
    
    # Clean up image files
    for url in urls:
        try:
            os.remove(url)
        except:
            pass
    
    return feedback_msg

# Handle image feedback callback
async def handle_image_feedback(client, callback_query):
    data = callback_query.data
    
    if data.startswith("img_feedback_positive"):
        await callback_query.answer("Thanks for your positive feedback!")
        await callback_query.message.edit_text(
            callback_query.message.text + "\n\n✅ *Feedback received: You liked the images!*",
            reply_markup=None
        )
        
    elif data.startswith("img_feedback_negative"):
        await callback_query.answer("Thanks for your feedback. We'll improve!")
        await callback_query.message.edit_text(
            callback_query.message.text + "\n\n📝 *Feedback received: We'll work to improve our image generation.*",
            reply_markup=None
        )
        
    elif data.startswith("img_regenerate"):
        # Get the feedback message for deletion later
        feedback_msg = callback_query.message
        await callback_query.answer("Regenerating images...")
        
        # Extract prompt from callback data
        parts = data.split("_")
        user_id = parts[2]
        prompt = "_".join(parts[3:])
        
        # Get the original message that this feedback is replying to
        reply_to_message_id = None
        if hasattr(feedback_msg, 'reply_to_message_id') and feedback_msg.reply_to_message_id:
            reply_to_message_id = feedback_msg.reply_to_message_id
        
        # Generate new images, passing feedback message for deletion
        await generate_command(
            client, 
            callback_query.message, 
            prompt, 
            reply_to_message_id=reply_to_message_id,
            regenerate=True,
            feedback_msg=feedback_msg
        )



