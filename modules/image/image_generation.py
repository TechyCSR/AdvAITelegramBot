import os
import random
import asyncio
from pyrogram.types import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import Client, filters
from pymongo import MongoClient
from ImgGenModel.g4f.client import Client as ImageClient
from ImgGenModel.g4f.Provider import BingCreateImages
from ImgGenModel.g4f.cookies import set_cookies
from config import BING_COOKIE, DATABASE_URL, LOG_CHANNEL
import requests
from datetime import datetime


mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
user_images_collection = db['user_images']


# Function to generate images with improved error handling and performance
async def generate_images(prompt, max_images=4):
    generated_images = 0
    total_attempts = 0
    max_attempts = 3  # Increased retry attempts
    image_urls = []

    while generated_images < max_images and total_attempts < max_attempts:
        client = ImageClient()
        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                n=max_images - generated_images,
                quality="hd"  # Request high quality images
            )
            for image_data in response.data:
                image_urls.append(image_data.url)
                generated_images += 1
                
                if generated_images >= max_images:
                    break

        except Exception as e:
            print(f"Error generating image: {str(e)}")
            total_attempts += 1
            await asyncio.sleep(1)  # Brief pause before retry
            continue

        total_attempts += 1
    
    if not image_urls:
        return None, "Failed to generate images. Please try a different prompt or try again later."
    
    image_urls = [u.replace("/images/", "./generated_images/") for u in image_urls]
    return image_urls, None


# Telegram bot command handler for generating images with modern UI
async def generate_command(client, message, prompt):
    user_id = message.from_user.id
    # Parse parameters from prompt if any
    style_options = ["realistic", "cartoon", "artistic", "3d", "sketch"]
    style = "realistic"  # Default style
    
    # Check if any style keywords are in the prompt
    for option in style_options:
        if f"style:{option}" in prompt.lower():
            style = option
            prompt = prompt.replace(f"style:{option}", "").strip()
    
    # Show processing status with modern UI
    processing_msg = await message.reply_text(
        "🎨 **Generating Images**\n\n"
        f"Creating visuals for: `{prompt}`\n"
        f"Style: `{style}`\n\n"
        "Please wait while the AI works its magic..."
    )
    
    # Generate images
    urls, error = await generate_images(f"{prompt} in {style} style")
    
    # Handle errors
    if error:
        await processing_msg.edit_text(
            f"❌ **Image Generation Failed**\n\n{error}"
        )
        client.send_message(
            LOG_CHANNEL, 
            f"#ImgLog #Rejected\nPrompt: {prompt}\nStyle: {style}\n**User**: {message.from_user.mention}\n**User ID**: {message.from_user.id}\n**Time**: {datetime.now()}\n**Chat ID**: {message.chat.id}\n"
        )
        return 
    
    # Prepare media group with generated images
    media_group = []
    for i, url in enumerate(urls):
        caption = f"🖼️ **AI Generated Image**\n\nPrompt: `{prompt}`\nStyle: `{style}`" if i == 0 else ""
        media_group.append(InputMediaPhoto(url, caption=caption))
    
    # Delete processing message
    await processing_msg.delete()
    
    # Send generated images
    sent_message = await message.reply_media_group(media_group)
    
    # Create feedback buttons for the generated images
    feedback_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👍 Love it", callback_data=f"img_feedback_positive_{user_id}"),
            InlineKeyboardButton("👎 Not good", callback_data=f"img_feedback_negative_{user_id}")
        ],
        [InlineKeyboardButton("🔄 Regenerate", callback_data=f"img_regenerate_{user_id}_{prompt}")]
    ])
    
    # Send a follow-up message with the feedback buttons
    await message.reply_text(
        "**How do you like these images?**\n\n"
        "Your feedback helps improve our AI.",
        reply_markup=feedback_markup
    )
    
    # Log images to log channel
    await client.send_media_group(LOG_CHANNEL, media_group)
    await client.send_message(
        LOG_CHANNEL, 
        f"#ImgLog\nPrompt: {prompt}\nStyle: {style}\n**User**: {message.from_user.mention}\n**User ID**: {message.from_user.id}\n**Time**: {datetime.now()}\n**Chat ID**: {message.chat.id}\n"
    )
    
    # Clean up image files
    for url in urls:
        try:
            os.remove(url)
        except:
            pass

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
        await callback_query.answer("Regenerating images...")
        parts = data.split("_")
        prompt = "_".join(parts[3:])
        await generate_command(client, callback_query.message, prompt)
        await callback_query.message.delete()



