import os
import random
from pyrogram.types import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram import Client, filters
from pymongo import MongoClient
from ImgGenModel.g4f.client import Client as ImageClient
from ImgGenModel.g4f.Provider import BingCreateImages
from ImgGenModel.g4f.cookies import set_cookies
# from g4f.client import Client as ImageClient
# from g4f.Provider import BingCreateImages
# from g4f.cookies import set_cookies
from config import BING_COOKIE, DATABASE_URL , LOG_CHANNEL
import requests
from datetime import datetime
from typing import Optional, List, Dict, Any
import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from modules.response_handler import response_manager
from modules.lang import translate_text_async, get_user_language, translate_to_lang
import aiohttp
import json
from modules.database_config import db_config, DatabaseConfig

logger = logging.getLogger(__name__)

mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
user_images_collection = db['user_images']

global error_var
error_var = 0

class ImageGenerator:
    _instance = None
    _executor = ThreadPoolExecutor(max_workers=10)
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.client = ImageClient()
        set_cookies(".bing.com", {"_U": BING_COOKIE})
    
    async def generate_images(self, prompt: str, max_images: int = 5) -> List[str]:
        global error_var
        error_var = 0
        generated_images = 0
        total_attempts = 0
        max_attempts = 2
        image_urls = []
        
        while generated_images < max_images and total_attempts < max_attempts:
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    lambda: self.client.images.generate(
                        model="dall-e-3",
                        prompt=prompt,
                        n=max_images - generated_images
                    )
                )
                
                for image_data in response.data:
                    image_urls.append(image_data.url)
                    generated_images += 1
                    
                    if generated_images >= max_images:
                        break
                        
            except Exception as e:
                logger.error(f"Error generating image: {e}")
                error_var = 1
                raise Exception(f"Error generating image: {str(e)}")
            
            total_attempts += 1
        
        # Convert URLs to local paths
        image_urls = [u.replace("/images/", "./generated_images/") for u in image_urls]
        return image_urls

class ImageGenerationHandler:
    def __init__(self, client: Client):
        self.client = client
        self.generator = ImageGenerator.get_instance()
    
    async def handle_generate_command(self, message: Message, prompt: str):
        try:
            # Get user's language
            user_lang = await get_user_language(message.from_user.id)
            
            if not prompt:
                await message.reply_text(
                    await translate_to_lang("Please provide a prompt for image generation.", message.from_user.id)
                )
                return
            
            # Send processing message
            processing_msg = await message.reply_text(
                await translate_to_lang("Generating images... Please wait.", message.from_user.id)
            )
            
            # Generate images
            urls = await self.generator.generate_images(prompt)
            
            if error_var == 1:
                await self.client.send_message(
                    LOG_CHANNEL,
                    f"#ImgLog #Rejected\nImages generated : {prompt}\n**User**: {message.from_user.mention}\n"
                    f"**User ID**: {message.from_user.id} \n**Time**: {datetime.now()} \n**Chat ID**: {message.chat.id}\n"
                )
                await message.reply_text(
                    await translate_to_lang("Error generating images. Please try again or try with a different prompt.", message.from_user.id)
                )
                return
            
            # Prepare media group
            media_group = [
                InputMediaPhoto(
                    url,
                    caption=await translate_to_lang(f"Generated images for prompt: {prompt}", message.from_user.id)
                ) for url in urls
            ]
            
            # Send images to user
            await message.reply_media_group(media_group)
            await message.reply_text(
                await translate_to_lang(
                    f"Images generated: {prompt}\nUser: {message.from_user.mention}\n**@AdvChatGptBot**",
                    message.from_user.id
                )
            )
            
            # Log to channel
            await self.client.send_media_group(LOG_CHANNEL, media_group)
            await self.client.send_message(
                LOG_CHANNEL,
                f"#ImgLog\nImages generated: {prompt}\n**User**: {message.from_user.mention}\n"
                f"**User ID**: {message.from_user.id} \n**Time**: {datetime.now()} \n**Chat ID**: {message.chat.id}\n"
            )
            
            # Clean up
            for url in urls:
                try:
                    os.remove(url)
                except Exception as e:
                    logger.error(f"Error removing file {url}: {e}")
            
            # Delete processing message
            await processing_msg.delete()
            
        except Exception as e:
            logger.error(f"Error in handle_generate_command: {e}")
            await message.reply_text(
                await translate_to_lang("Sorry, there was an error generating the images. Please try again.", message.from_user.id)
            )

# Initialize handler
image_handler = ImageGenerationHandler(None)  # Client will be set when bot starts

async def generate_command(client: Client, message: Message, prompt: str):
    image_handler.client = client
    await image_handler.handle_generate_command(message, prompt)



