
import os
import random
from pyrogram.types import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import Client, filters
from pymongo import MongoClient
from g4f.client import Client as ImageClient
from g4f.Provider import BingCreateImages
from g4f.cookies import set_cookies
from config import BING_COOKIE, DATABASE_URL

# Initialize the MongoDB client
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
user_images_collection = db['user_images']


# Function to generate images
def generate_images(prompt, max_images=3):
    generated_images = 0
    total_attempts = 0
    max_attempts = 2  
    image_urls = []

    while generated_images < max_images and total_attempts < max_attempts:
        set_cookies(".bing.com", {
            "_U": BING_COOKIE
        })

        client = ImageClient(image_provider=BingCreateImages)

        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                n=max_images - generated_images 
            )

            for image_data in response.data:
                image_urls.append(image_data.url)
                generated_images += 1
                
                if generated_images >= max_images:
                    break

        except Exception as e:
            print(f"Error generating image: {str(e)}")
            return f"Error generating image: {str(e)}"

        total_attempts += 1

    if generated_images < max_images:
        print(f"Warning: Only generated {generated_images} out of {max_images} requested images.")

    return image_urls

# Function to update user's image history in MongoDB
def update_user_images(user_id, new_image_urls):
    user_images = user_images_collection.find_one({"user_id": user_id})
    
    if user_images:
        # Keep only the last 3 images
        updated_images = user_images["images"][-2:] + new_image_urls
        user_images_collection.update_one(
            {"user_id": user_id},
            {"$set": {"images": updated_images}}
        )
    else:
        # If user doesn't exist, create a new entry
        user_images_collection.insert_one({
            "user_id": user_id,
            "images": new_image_urls
        })

# Telegram bot command handler for generating images
async def generate_command(client, message, prompt):

    # prompt = message.text.split(" ", 1)[1]  
    # print(f"Generating images for prompt: {prompt}")
    user_id = message.from_user.id

    # Generate images
    urls = generate_images(prompt)

    if type(urls) == str:
        await message.reply_text(urls)
        return
    
    # Update the user's image history
    update_user_images(user_id, urls)
    
    # Prepare media group (album) to send images as a group
    media_group = [InputMediaPhoto(url,caption=f"Generated images for prompt: {prompt}") for url in urls]
    
    # Reply with the generated images in a single group
    await message.reply_media_group(media_group)

    await message.reply_text(f"Images generated : {prompt}\n User: {message.from_user.mention}\n**@AdChatGptBot**")



