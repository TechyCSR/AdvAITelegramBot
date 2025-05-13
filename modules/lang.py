from googletrans import Translator
from pymongo import MongoClient
from config import DATABASE_URL
import functools
import time

# Initialize MongoDB client
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
user_lang_collection = db['user_lang']
translation_cache = db['translation_cache']

# Initialize translator
translator = Translator()

# Simple in-memory cache for translations to avoid repeated API calls
_translation_cache = {}

def get_user_language(user_id):
    """Get user's preferred language from database"""
    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
    if user_lang_doc:
        return user_lang_doc['language']
    return 'en'  # Default to English if not set

def translate_to_lang(text, user_id=None, lang=None):
    """Translate text to user's preferred language or specified language with caching"""
    try:
        if lang is None and user_id is not None:
            lang = get_user_language(user_id)
        
        if lang == 'en':  # No need to translate if target is English
            return text
        
        # Create a unique key for the cache
        cache_key = f"{text}_{lang}"
        
        # Check in-memory cache first for fastest retrieval
        if cache_key in _translation_cache:
            return _translation_cache[cache_key]
            
        # Then check MongoDB cache
        cached = translation_cache.find_one({"key": cache_key})
        if cached:
            # Update in-memory cache and return
            _translation_cache[cache_key] = cached["translation"]
            return cached["translation"]
        
        # If not in cache, perform translation
        translation = translator.translate(text, src='en', dest=lang)
        translated_text = translation.text
        
        # Store in both caches
        _translation_cache[cache_key] = translated_text
        translation_cache.update_one(
            {"key": cache_key},
            {"$set": {"translation": translated_text, "timestamp": time.time()}},
            upsert=True
        )
        
        return translated_text
    except Exception as e:
        print(f"Translation error: {e}")
        return text  # Return original text if translation fails

# Create an async version for use in async functions
async def async_translate(text, user_id=None, lang=None):
    """Async wrapper for translate_to_lang function"""
    return translate_to_lang(text, user_id, lang)

# while True:
#     print(translate_to_lang("Hello, How are you?"))
#     break