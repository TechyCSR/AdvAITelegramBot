from deep_translator import GoogleTranslator
from pymongo import MongoClient
from config import DATABASE_URL
import time
import asyncio
import re
from typing import Dict, Optional, List, Tuple

# Initialize MongoDB client
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
user_lang_collection = db['user_lang']
translation_cache = db['translation_cache']

# Language code mapping (deep_translator uses some different codes than our system)
LANGUAGE_CODE_MAP = {
    'zh': 'zh-CN',  # Convert our 'zh' code to what deep_translator expects
    'ar': 'ar',
    'fr': 'fr',
    'ru': 'ru',
    'hi': 'hi',
    'en': 'en'
}

# Simple in-memory cache for translations to avoid repeated API calls
_translation_cache: Dict[str, str] = {}

# Maximum retries for translation attempts
MAX_RETRIES = 3

def get_user_language(user_id):
    """Get user's preferred language from database"""
    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
    if user_lang_doc:
        return user_lang_doc['language']
    return 'en'  # Default to English if not set

def get_target_language_code(lang):
    """Convert our language code to deep_translator format if needed"""
    return LANGUAGE_CODE_MAP.get(lang, lang)

def extract_placeholders(text: str) -> List[Tuple[str, str]]:
    """
    Extract placeholders from text like {user_id}, {mention}, etc.
    Returns a list of (placeholder, placeholder_text) tuples.
    """
    placeholder_pattern = r'\{([^{}]+)\}'
    placeholders = re.findall(placeholder_pattern, text)
    return [(p, '{' + p + '}') for p in placeholders]

def translate_sync(text, lang):
    """
    Synchronous translation function with direct execution and placeholder preservation.
    """
    if lang == 'en' or not text.strip():
        return text
        
    # Extract and preserve placeholders
    placeholders = extract_placeholders(text)
    replacement_map = {}
    
    # Replace placeholders with tokens that won't get translated or modified
    working_text = text
    for i, (name, placeholder) in enumerate(placeholders):
        # Use non-translatable token format
        token = f"__PLH_{i}__"
        replacement_map[token] = placeholder
        working_text = working_text.replace(placeholder, token)
    
    target_lang = get_target_language_code(lang)
    
    # Try translation with retries
    for attempt in range(MAX_RETRIES):
        try:
            translator = GoogleTranslator(source='en', target=target_lang)
            result = translator.translate(working_text)
            
            # Restore placeholders in the translated text
            if result:
                for token, placeholder in replacement_map.items():
                    result = result.replace(token, placeholder)
                return result
        except Exception as e:
            print(f"Translation attempt {attempt + 1} failed: {e}")
            if attempt == MAX_RETRIES - 1:
                print(f"All translation attempts failed for: {text} to {lang}")
                return text  # Return original text if all attempts fail
    
    return text

async def async_translate_to_lang(text, user_id=None, lang=None) -> str:
    """
    Asynchronous translation function with caching and placeholder preservation.
    """
    try:
        # Get language if not provided
        if lang is None and user_id is not None:
            lang = get_user_language(user_id)
            
        # Skip translation for English or empty strings
        if lang == 'en' or not text.strip():
            return text
        
        # Extract placeholders before creating cache key
        placeholders = extract_placeholders(text)
        replacement_map = {}
        
        # Replace placeholders with tokens
        working_text = text
        for i, (name, placeholder) in enumerate(placeholders):
            # Use non-translatable token format
            token = f"__PLH_{i}__"
            replacement_map[token] = placeholder
            working_text = working_text.replace(placeholder, token)
            
        # Create a cache key for the working text
        cache_key = f"{working_text}_{lang}"
        
        # Check in-memory cache first
        if cache_key in _translation_cache:
            result = _translation_cache[cache_key]
            # Restore placeholders
            for token, placeholder in replacement_map.items():
                result = result.replace(token, placeholder)
            return result
            
        # Then check database cache
        cached = translation_cache.find_one({"key": cache_key})
        if cached:
            _translation_cache[cache_key] = cached["translation"]
            result = cached["translation"]
            # Restore placeholders
            for token, placeholder in replacement_map.items():
                result = result.replace(token, placeholder)
            return result
        
        # For debugging
        print(f"DEBUG: Starting async translation of '{text}' to {lang}")    
        
        # Use direct translation function with placeholders removed
        target_lang = get_target_language_code(lang)
        try:
            translator = GoogleTranslator(source='en', target=target_lang)
            translated_text = translator.translate(working_text)
            print(f"DEBUG: Got translation result: '{translated_text}'")
            
            # Cache the translation of working text (without placeholders restored)
            if translated_text and translated_text != working_text:
                _translation_cache[cache_key] = translated_text
                translation_cache.update_one(
                    {"key": cache_key},
                    {"$set": {"translation": translated_text, "timestamp": time.time()}},
                    upsert=True
                )
            
            # Restore placeholders for the final result
            for token, placeholder in replacement_map.items():
                translated_text = translated_text.replace(token, placeholder)
                
            return translated_text
            
        except Exception as e:
            print(f"DEBUG: Direct translation error in async: {e}")
            return text
            
    except Exception as e:
        print(f"Async translation error: {e}")
        import traceback
        traceback.print_exc()
        return text

# Legacy function for backward compatibility
def translate_to_lang(text, user_id=None, lang=None):
    """
    Synchronous translation with caching and placeholder preservation (maintained for backward compatibility).
    """
    try:
        # Get language if not provided
        if lang is None and user_id is not None:
            lang = get_user_language(user_id)
            
        # Skip translation for English or empty strings
        if lang == 'en' or not text.strip():
            return text
        
        # Extract placeholders before creating cache key
        placeholders = extract_placeholders(text)
        replacement_map = {}
        
        # Replace placeholders with tokens
        working_text = text
        for i, (name, placeholder) in enumerate(placeholders):
            # Use non-translatable token format
            token = f"__PLH_{i}__"
            replacement_map[token] = placeholder
            working_text = working_text.replace(placeholder, token)
            
        # Create a cache key for the working text
        cache_key = f"{working_text}_{lang}"
        
        # Check in-memory cache first
        if cache_key in _translation_cache:
            result = _translation_cache[cache_key]
            # Restore placeholders
            for token, placeholder in replacement_map.items():
                result = result.replace(token, placeholder)
            return result
            
        # Then check database cache
        cached = translation_cache.find_one({"key": cache_key})
        if cached:
            _translation_cache[cache_key] = cached["translation"]
            result = cached["translation"]
            # Restore placeholders
            for token, placeholder in replacement_map.items():
                result = result.replace(token, placeholder)
            return result
            
        # Perform the translation
        translated_text = translate_sync(working_text, lang)
        
        # Cache the translation of working text (without placeholders restored)
        if translated_text != working_text:
            _translation_cache[cache_key] = translated_text
            translation_cache.update_one(
                {"key": cache_key},
                {"$set": {"translation": translated_text, "timestamp": time.time()}},
                upsert=True
            )
        
        # Restore placeholders for the final result
        for token, placeholder in replacement_map.items():
            translated_text = translated_text.replace(token, placeholder)
            
        return translated_text
        
    except Exception as e:
        print(f"Translation error: {e}")
        return text

# Deprecated - Use async_translate_to_lang instead
async def async_translate(text, user_id=None, lang=None):
    """
    Deprecated async wrapper - use async_translate_to_lang instead
    """
    return await async_translate_to_lang(text, user_id, lang)

# Batch translation function for efficiently translating multiple strings at once
async def batch_translate(texts, user_id=None, lang=None):
    """
    Translate multiple texts at once.
    Returns a list of translated texts in the same order.
    """
    if not texts:
        return []
        
    # Get language if not provided
    if lang is None and user_id is not None:
        lang = get_user_language(user_id)
    
    # No need to translate if target is English
    if lang == 'en':
        return texts.copy()  # Return copy of original texts
    
    results = []
    
    # Process each text
    for text in texts:
        try:
            translated = await async_translate_to_lang(text, user_id, lang)
            results.append(translated)
        except Exception as e:
            print(f"Error in batch translation: {e}")
            results.append(text)  # Use original text on error
            
    return results

# while True:
#     print(translate_to_lang("Hello, How are you?"))
#     break