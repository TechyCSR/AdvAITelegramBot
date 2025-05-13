import os
import random
from pyrogram.types import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import Client, filters
from pymongo import MongoClient
from ImgGenModel.g4f.client import Client as ImageClient
from ImgGenModel.g4f.Provider import BingCreateImages
from ImgGenModel.g4f.cookies import set_cookies
# from g4f.client import Client as ImageClient
# from g4f.Provider import BingCreateImages
# from g4f.cookies import set_cookies
from config import BING_COOKIE, DATABASE_URL , LOG_CHANNEL
from modules.lang import get_ui_message, get_user_language
import requests
from datetime import datetime


mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
user_images_collection = db['user_images']

global error_var
error_var=0


# Function to generate images
def generate_images(prompt, max_images=5):
    global error_var
    error_var=0
    generated_images = 0
    total_attempts = 0
    max_attempts = 2  
    image_urls = []


    while generated_images < max_images and total_attempts < max_attempts:
        # set_cookies(".bing.com", {
        #     "_U": BING_COOKIE
        # })

        client = ImageClient()
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
            error_var=1
            return f"Error generating image: {str(e)}"

        total_attempts += 1

    # if generated_images < max_images:
    #     print(f"Warning: Only generated {generated_images} out of {max_images} requested images.")
    
    image_urls  = [u.replace("/images/", "./generated_images/") for u in image_urls]
    print(image_urls)
    return image_urls


# Telegram bot command handler for generating images
def generate_command(client, message, prompt):
    global error_var
    user_id = message.from_user.id

    # Generate images
    urls = generate_images(prompt)

    if error_var==1:
        client.send_message(LOG_CHANNEL, f"#ImgLog #Rejected\nImages generated : {prompt}\n**User**: {message.from_user.mention}\n **User ID**: {message.from_user.id} \n **Time** : {datetime.now()} \n**Chat ID**: {message.chat.id}\n")
        message.reply_text(get_ui_message("image_generation_error", user_id))
        return 
    
    # Prepare media group (album) to send images as a group
    # Get the caption in user's language
    caption_template = get_ui_message("generated_image_caption", user_id, None)
    if not caption_template or caption_template == "generated_image_caption":
        caption_template = "Generated images for prompt: {prompt}"
    
    caption = caption_template.replace("{prompt}", prompt)
    
    media_group = [InputMediaPhoto(url, caption=caption) for url in urls]
    
    # Reply with the generated images in a single group
    message.reply_media_group(media_group)
    
    # Get the completion message in user's language
    completion_msg = get_ui_message("image_gen_complete", user_id, None)
    if not completion_msg or completion_msg == "image_gen_complete":
        completion_msg = "Images generated : {prompt}\nUser: {user_mention}\n**@AdvChatGptBot**"
    
    completion_msg = completion_msg.replace("{prompt}", prompt).replace("{user_mention}", message.from_user.mention)
    
    message.reply_text(completion_msg)

    #log images to log channel
    client.send_media_group(LOG_CHANNEL, media_group)
    client.send_message(LOG_CHANNEL, f"#ImgLog\nImages generated : {prompt}\n**User**: {message.from_user.mention}\n **User ID**: {message.from_user.id} \n **Time** : {datetime.now()} \n**Chat ID**: {message.chat.id}\n")
    # delete the image files after sending
    for url in urls:
        os.remove(url)



