from googletrans import Translator
from pymongo import MongoClient
from config import DATABASE_URL
from functools import lru_cache
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MongoDB client with optimized settings
client = MongoClient(DATABASE_URL, maxPoolSize=50, minPoolSize=10)
db = client["aibotdb"]
user_lang_collection = db['user_lang']

# Create index for faster queries
user_lang_collection.create_index("user_id", unique=True)

# Initialize translator with optimized settings
translator = Translator()

# Thread pool for translations
thread_pool = ThreadPoolExecutor(max_workers=10)

# Language code mapping with proper names
LANGUAGE_CODES = {
    "en": {"code": "en", "name": "English", "flag": "🇬🇧"},
    "hi": {"code": "hi", "name": "Hindi", "flag": "🇮🇳"},
    "zh": {"code": "zh-cn", "name": "Chinese", "flag": "🇨🇳"},
    "ar": {"code": "ar", "name": "Arabic", "flag": "🇸🇦"},
    "fr": {"code": "fr", "name": "French", "flag": "🇫🇷"},
    "ru": {"code": "ru", "name": "Russian", "flag": "🇷🇺"}
}

# Cache for translations with increased size
@lru_cache(maxsize=2000)
def get_cached_translation(text: str, target_lang: str) -> str:
    """Get cached translation or perform new translation"""
    try:
        # Get the correct language code
        lang_info = LANGUAGE_CODES.get(target_lang, {"code": target_lang})
        lang_code = lang_info["code"]
        
        # If target language is English, return original text
        if lang_code == "en":
            return text
            
        # Perform translation
        result = translator.translate(text, dest=lang_code)
        return result.text
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return text

def get_user_language(user_id: int) -> str:
    """Get user's language preference from database"""
    try:
        user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
        if user_lang_doc:
            return user_lang_doc['language']
        # Set default language to English if not found
        user_lang_collection.insert_one({"user_id": user_id, "language": "en"})
        return "en"
    except Exception as e:
        logger.error(f"Error getting user language: {e}")
        return "en"

def set_user_language(user_id: int, language: str) -> bool:
    """Set user's language preference in database"""
    try:
        if language not in LANGUAGE_CODES:
            return False
        user_lang_collection.update_one(
            {"user_id": user_id},
            {"$set": {"language": language}},
            upsert=True
        )
        # Clear translation cache
        get_cached_translation.cache_clear()
        return True
    except Exception as e:
        logger.error(f"Error setting user language: {e}")
        return False

async def translate_text_async(text: str, target_lang: str) -> str:
    """Asynchronous translation function"""
    try:
        # Run translation in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            thread_pool,
            get_cached_translation,
            text,
            target_lang
        )
        return result
    except Exception as e:
        logger.error(f"Error in translate_text_async: {e}")
        return text

def translate_to_lang(text: str, user_id: int = None, target_lang: str = None, **kwargs) -> str:
    """Translate text to target language with optimized caching"""
    try:
        # Format text with kwargs first
        if kwargs:
            text = text.format(**kwargs)
            
        # Determine target language
        if target_lang:
            lang = target_lang
        elif user_id:
            lang = get_user_language(user_id)
        else:
            return text
            
        # Get cached translation
        return get_cached_translation(text, lang)
    except Exception as e:
        logger.error(f"Error in translate_to_lang: {e}")
        return text

def get_language_display_name(lang_code: str) -> str:
    """Get language display name with flag"""
    lang_info = LANGUAGE_CODES.get(lang_code, {"name": lang_code, "flag": "🌐"})
    return f"{lang_info['flag']} {lang_info['name']}"

# while True:
#     print(translate_to_lang("Hello, How are you?"))
#     break