from typing import Optional, Dict, Any, Union
from pyrogram import Client
from pyrogram.types import Message, CallbackQuery
import asyncio
import logging
from functools import lru_cache
import time
from concurrent.futures import ThreadPoolExecutor
from modules.lang import translate_text_async, get_user_language

logger = logging.getLogger(__name__)

class ResponseManager:
    _instance = None
    _executor = ThreadPoolExecutor(max_workers=20)
    _rate_limits: Dict[int, float] = {}
    _cache: Dict[str, Any] = {}
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self._max_cache_size = 1000
        self._rate_limit_window = 1.0  # seconds
        self._max_requests_per_window = 5
    
    @lru_cache(maxsize=1000)
    def _get_cache_key(self, user_id: int, content: str) -> str:
        return f"{user_id}:{content}"
    
    def _check_rate_limit(self, user_id: int) -> bool:
        current_time = time.time()
        if user_id in self._rate_limits:
            last_request = self._rate_limits[user_id]
            if current_time - last_request < self._rate_limit_window:
                return False
        self._rate_limits[user_id] = current_time
        return True
    
    def _update_cache(self, key: str, value: Any):
        if len(self._cache) >= self._max_cache_size:
            self._cache.clear()
        self._cache[key] = value
    
    async def handle_text_response(
        self,
        client: Client,
        message: Message,
        response_text: str,
        reply_markup: Optional[Any] = None
    ) -> Message:
        try:
            if not self._check_rate_limit(message.from_user.id):
                return await message.reply_text("Please wait a moment before sending another message.")
            
            cache_key = self._get_cache_key(message.from_user.id, response_text)
            if cache_key in self._cache:
                return await message.reply_text(
                    self._cache[cache_key],
                    reply_markup=reply_markup
                )
            
            user_lang = await get_user_language(message.from_user.id)
            translated_text = await translate_text_async(response_text, user_lang)
            
            self._update_cache(cache_key, translated_text)
            
            return await message.reply_text(
                translated_text,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error in handle_text_response: {e}")
            return await message.reply_text("An error occurred while processing your request.")
    
    async def handle_image_response(
        self,
        client: Client,
        message: Message,
        image_path: str,
        caption: Optional[str] = None
    ) -> Message:
        try:
            if not self._check_rate_limit(message.from_user.id):
                return await message.reply_text("Please wait a moment before sending another image.")
            
            if caption:
                user_lang = await get_user_language(message.from_user.id)
                translated_caption = await translate_text_async(caption, user_lang)
            else:
                translated_caption = None
            
            return await message.reply_photo(
                image_path,
                caption=translated_caption
            )
        except Exception as e:
            logger.error(f"Error in handle_image_response: {e}")
            return await message.reply_text("An error occurred while processing your image.")
    
    async def handle_voice_response(
        self,
        client: Client,
        message: Message,
        voice_path: str,
        duration: int,
        caption: Optional[str] = None
    ) -> Message:
        try:
            if not self._check_rate_limit(message.from_user.id):
                return await message.reply_text("Please wait a moment before sending another voice message.")
            
            if caption:
                user_lang = await get_user_language(message.from_user.id)
                translated_caption = await translate_text_async(caption, user_lang)
            else:
                translated_caption = None
            
            return await message.reply_voice(
                voice_path,
                duration=duration,
                caption=translated_caption
            )
        except Exception as e:
            logger.error(f"Error in handle_voice_response: {e}")
            return await message.reply_text("An error occurred while processing your voice message.")
    
    async def handle_callback_response(
        self,
        client: Client,
        callback: CallbackQuery,
        response_text: str,
        reply_markup: Optional[Any] = None
    ) -> None:
        try:
            if not self._check_rate_limit(callback.from_user.id):
                await callback.answer("Please wait a moment before trying again.", show_alert=True)
                return
            
            user_lang = await get_user_language(callback.from_user.id)
            translated_text = await translate_text_async(response_text, user_lang)
            
            await callback.message.edit_text(
                translated_text,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error in handle_callback_response: {e}")
            await callback.answer("An error occurred. Please try again.", show_alert=True)
    
    async def handle_error_response(
        self,
        client: Client,
        message: Union[Message, CallbackQuery],
        error_message: str
    ) -> None:
        try:
            if isinstance(message, CallbackQuery):
                await message.answer(error_message, show_alert=True)
            else:
                await message.reply_text(error_message)
        except Exception as e:
            logger.error(f"Error in handle_error_response: {e}")

response_manager = ResponseManager.get_instance() 