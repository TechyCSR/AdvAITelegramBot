from typing import Dict, Optional
import logging
from functools import lru_cache
import asyncio
from concurrent.futures import ThreadPoolExecutor
from modules.database_config import db_config, DatabaseConfig
from googletrans import Translator

logger = logging.getLogger(__name__)

class LanguageManager:
    _instance = None
    _executor = ThreadPoolExecutor(max_workers=10)
    _cache: Dict[str, str] = {}
    _max_cache_size = 1000
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.translator = Translator()
    
    @lru_cache(maxsize=1000)
    def get_language_display_name(self, lang_code: str) -> str:
        languages = {
            "en": "🇬🇧 English",
            "hi": "🇮🇳 हिंदी",
            "zh": "🇨🇳 中文",
            "ar": "🇸🇦 العربية",
            "fr": "🇫🇷 Français",
            "ru": "🇷🇺 Русский"
        }
        return languages.get(lang_code, "🇬🇧 English")
    
    @DatabaseConfig.retry_on_failure
    async def get_user_language(self, user_id: int) -> str:
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: db_config.db.user_lang.find_one({"user_id": user_id})
            )
            return result["language"] if result else "en"
        except Exception as e:
            logger.error(f"Error getting user language: {e}")
            return "en"
    
    @DatabaseConfig.retry_on_failure
    async def update_user_language(self, user_id: int, language: str) -> bool:
        try:
            await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: db_config.db.user_lang.update_one(
                    {"user_id": user_id},
                    {"$set": {"language": language}},
                    upsert=True
                )
            )
            return True
        except Exception as e:
            logger.error(f"Error updating user language: {e}")
            return False
    
    def _get_cache_key(self, text: str, target_lang: str) -> str:
        return f"{text}:{target_lang}"
    
    def _update_cache(self, key: str, value: str):
        if len(self._cache) >= self._max_cache_size:
            self._cache.clear()
        self._cache[key] = value
    
    async def translate_text_async(self, text: str, target_lang: str) -> str:
        if target_lang == "en":
            return text
        
        cache_key = self._get_cache_key(text, target_lang)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: self.translator.translate(text, dest=target_lang)
            )
            translated_text = result.text
            self._update_cache(cache_key, translated_text)
            return translated_text
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text

lang_manager = LanguageManager.get_instance()

async def get_user_language(user_id: int) -> str:
    return await lang_manager.get_user_language(user_id)

async def update_user_language(user_id: int, language: str) -> bool:
    return await lang_manager.update_user_language(user_id, language)

async def translate_text_async(text: str, target_lang: str) -> str:
    return await lang_manager.translate_text_async(text, target_lang)

def get_language_display_name(lang_code: str) -> str:
    return lang_manager.get_language_display_name(lang_code)

async def translate_to_lang(text: str, user_id: int) -> str:
    """Translate text to user's preferred language."""
    try:
        user_lang = await get_user_language(user_id)
        return await translate_text_async(text, user_lang)
    except Exception as e:
        logger.error(f"Error in translate_to_lang: {e}")
        return text

# while True:
#     print(translate_to_lang("Hello, How are you?"))
#     break