from deep_translator import GoogleTranslator
from pymongo import MongoClient
from config import DATABASE_URL
import time
import asyncio
import re
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, List, Tuple, Any, Set
from modules.lang_resources.translation_cache import (
    get_cached_translation,
    add_to_translation_cache,
    preload_all_caches,
    batch_cache_translations
)

# Initialize MongoDB client
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
user_lang_collection = db['user_lang']
translation_cache = db['translation_cache']  # Keep for backward compatibility

# Thread pool for parallel processing of translations
_translation_executor = ThreadPoolExecutor(max_workers=4)

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
_mention_cache: Dict[str, Dict[str, str]] = {}  # Special cache for user mentions

# Maximum retries for translation attempts
MAX_RETRIES = 3

# Special tokens that should not be translated
SPECIAL_TOKENS = ['@', 'http://', 'https://', '.com', '.org', '.net', '(', ')', '[', ']']

# Preload translation caches during module initialization
try:
    preload_all_caches()
except Exception as e:
    print(f"Error preloading translation caches: {e}")

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
    First checks the JSON cache, then falls back to online translation.
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
    
    # Check JSON cache for the text with placeholders removed
    cached_translation = get_cached_translation(working_text, lang)
    if cached_translation:
        # Restore placeholders
        result = cached_translation
        for token, placeholder in replacement_map.items():
            result = result.replace(token, placeholder)
        return result
    
    target_lang = get_target_language_code(lang)
    
    # Try translation with retries
    for attempt in range(MAX_RETRIES):
        try:
            translator = GoogleTranslator(source='en', target=target_lang)
            result = translator.translate(working_text)
            
            # If translation successful, add to JSON cache
            if result and result != working_text:
                add_to_translation_cache(working_text, result, lang)
            
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
    Uses the JSON cache first, then falls back to online translation.
    """
    try:
        # Get language if not provided
        if lang is None and user_id is not None:
            lang = get_user_language(user_id)
            
        # Skip translation for English or empty strings
        if lang == 'en' or not text.strip():
            return text
            
        # Special fast path for mentions
        if text.startswith('@') or '{mention}' in text:
            if lang in _mention_cache and text in _mention_cache[lang]:
                return _mention_cache[lang][text]
        
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
        
        # Check JSON file cache first (faster than MongoDB)
        json_cached = get_cached_translation(working_text, lang)
        if json_cached:
            # Restore placeholders
            result = json_cached
            for token, placeholder in replacement_map.items():
                result = result.replace(token, placeholder)
                
            # Add to mention cache if it's a mention or contains {mention}
            if text.startswith('@') or '{mention}' in text:
                if lang not in _mention_cache:
                    _mention_cache[lang] = {}
                _mention_cache[lang][text] = result
                
            return result
            
        # Create a cache key for the working text
        cache_key = f"{working_text}_{lang}"
        
        # Check in-memory cache 
        if cache_key in _translation_cache:
            result = _translation_cache[cache_key]
            # Restore placeholders
            for token, placeholder in replacement_map.items():
                result = result.replace(token, placeholder)
                
            # Add to mention cache if it's a mention
            if text.startswith('@') or '{mention}' in text:
                if lang not in _mention_cache:
                    _mention_cache[lang] = {}
                _mention_cache[lang][text] = result
                
            return result
            
        # Then check database cache (for backward compatibility)
        cached = translation_cache.find_one({"key": cache_key})
        if cached:
            _translation_cache[cache_key] = cached["translation"]
            result = cached["translation"]
            # Add to the JSON cache for future use
            add_to_translation_cache(working_text, result, lang)
            # Restore placeholders
            for token, placeholder in replacement_map.items():
                result = result.replace(token, placeholder)
                
            # Add to mention cache if it's a mention
            if text.startswith('@') or '{mention}' in text:
                if lang not in _mention_cache:
                    _mention_cache[lang] = {}
                _mention_cache[lang][text] = result
                
            return result
            
        # Use direct translation with placeholders removed
        target_lang = get_target_language_code(lang)
        
        # Run translation in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        translate_func = functools.partial(
            _translate_with_retries, working_text, target_lang
        )
        translated_text = await loop.run_in_executor(_translation_executor, translate_func)
            
        # Cache the translation of working text
        if translated_text and translated_text != working_text:
            # Add to in-memory cache
            _translation_cache[cache_key] = translated_text
            
            # Add to MongoDB cache (will be phased out)
            translation_cache.update_one(
                {"key": cache_key},
                {"$set": {"translation": translated_text, "timestamp": time.time()}},
                upsert=True
            )
            
            # Add to JSON file cache
            add_to_translation_cache(working_text, translated_text, lang)
        
        # Restore placeholders for the final result
        for token, placeholder in replacement_map.items():
            translated_text = translated_text.replace(token, placeholder)
            
        # Add to mention cache if it's a mention
        if text.startswith('@') or '{mention}' in text:
            if lang not in _mention_cache:
                _mention_cache[lang] = {}
            _mention_cache[lang][text] = translated_text
            
        return translated_text
            
    except Exception as e:
        print(f"Async translation error: {e}")
        import traceback
        traceback.print_exc()
        return text

def _translate_with_retries(text, target_lang):
    """Helper function for translating with retries in a thread"""
    for attempt in range(MAX_RETRIES):
        try:
            translator = GoogleTranslator(source='en', target=target_lang)
            result = translator.translate(text)
            if result:
                return result
        except Exception as e:
            print(f"Translation attempt {attempt + 1} failed: {e}")
            time.sleep(0.5)  # Small delay before retry
    
    return text  # Return original text if all attempts fail

# Legacy function for backward compatibility
def translate_to_lang(text, user_id=None, lang=None):
    """
    Synchronous translation with caching and placeholder preservation.
    Uses JSON cache first, then falls back to online translation.
    """
    try:
        # Get language if not provided
        if lang is None and user_id is not None:
            lang = get_user_language(user_id)
            
        # Skip translation for English or empty strings
        if lang == 'en' or not text.strip():
            return text
            
        # Special fast path for mentions
        if text.startswith('@') or '{mention}' in text:
            if lang in _mention_cache and text in _mention_cache[lang]:
                return _mention_cache[lang][text]
        
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
        
        # Check JSON file cache first (faster than MongoDB)
        json_cached = get_cached_translation(working_text, lang)
        if json_cached:
            # Restore placeholders
            result = json_cached
            for token, placeholder in replacement_map.items():
                result = result.replace(token, placeholder)
                
            # Add to mention cache if it's a mention
            if text.startswith('@') or '{mention}' in text:
                if lang not in _mention_cache:
                    _mention_cache[lang] = {}
                _mention_cache[lang][text] = result
                
            return result
            
        # Create a cache key for the working text
        cache_key = f"{working_text}_{lang}"
        
        # Check in-memory cache
        if cache_key in _translation_cache:
            result = _translation_cache[cache_key]
            # Restore placeholders
            for token, placeholder in replacement_map.items():
                result = result.replace(token, placeholder)
            return result
            
        # Then check database cache (for backward compatibility)
        cached = translation_cache.find_one({"key": cache_key})
        if cached:
            _translation_cache[cache_key] = cached["translation"]
            result = cached["translation"]
            # Add to JSON cache for future use
            add_to_translation_cache(working_text, result, lang)
            # Restore placeholders
            for token, placeholder in replacement_map.items():
                result = result.replace(token, placeholder)
                
            # Add to mention cache if it's a mention
            if text.startswith('@') or '{mention}' in text:
                if lang not in _mention_cache:
                    _mention_cache[lang] = {}
                _mention_cache[lang][text] = result
                
            return result
            
        # Perform the translation
        translated_text = translate_sync(working_text, lang)
        
        # Cache the translation of working text
        if translated_text != working_text:
            _translation_cache[cache_key] = translated_text
            
            # Add to MongoDB cache (will be phased out)
            translation_cache.update_one(
                {"key": cache_key},
                {"$set": {"translation": translated_text, "timestamp": time.time()}},
                upsert=True
            )
            
            # Add to JSON file cache
            add_to_translation_cache(working_text, translated_text, lang)
        
        # Restore placeholders for the final result
        for token, placeholder in replacement_map.items():
            translated_text = translated_text.replace(token, placeholder)
            
        # Add to mention cache if it's a mention
        if text.startswith('@') or '{mention}' in text:
            if lang not in _mention_cache:
                _mention_cache[lang] = {}
            _mention_cache[lang][text] = translated_text
            
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
    
    # First check cache for all texts
    cache_hits = batch_cache_translations(texts, lang)
    
    # If all texts were in cache, return immediately
    if len(cache_hits) == len(texts):
        return [cache_hits[text] for text in texts]
    
    # For texts not in cache, translate them in parallel
    missing_texts = [text for text in texts if text not in cache_hits]
    tasks = []
    
    # Create async tasks for all missing translations
    for text in missing_texts:
        tasks.append(asyncio.create_task(async_translate_to_lang(text, user_id, lang)))
    
    # Wait for all translations to complete
    missing_translations = await asyncio.gather(*tasks)
    
    # Combine cache hits with new translations in original order
    results = []
    missing_idx = 0
    
    for text in texts:
        if text in cache_hits:
            results.append(cache_hits[text])
        else:
            results.append(missing_translations[missing_idx])
            missing_idx += 1
            
    return results

# Optimized function for translating UI elements like buttons
async def translate_ui_element(text, user_id=None, lang=None):
    """
    Optimized translation for UI elements (buttons, labels)
    Uses multi-level caching with special handling for short texts
    """
    if not text or text.isspace():
        return text
        
    # Get language if not provided
    if lang is None and user_id is not None:
        lang = get_user_language(user_id)
        
    # Skip translation for English
    if lang == 'en':
        return text
        
    # Create cache key
    cache_key = f"ui_{text}_{lang}"
    
    # Check memory cache first (fastest)
    if cache_key in _translation_cache:
        return _translation_cache[cache_key]
        
    # Use standard translation
    translated = await async_translate_to_lang(text, user_id, lang)
    
    # Cache result
    _translation_cache[cache_key] = translated
    
    return translated

# Add this function to handle mentions properly

def preserve_mention(text, mention):
    """
    Special helper to preserve user mentions in any language
    Returns the text with the mention properly encoded for preservation
    """
    if not mention or not text:
        return text
        
    # Use a special token format that won't be translated
    mention_token = f"__MENTION_TOKEN_{hash(mention) & 0xFFFFFF}__"
    
    # Replace the mention in the text with the token
    tokenized_text = text.replace(mention, mention_token)
    
    return tokenized_text, mention_token, mention

async def format_with_mention(text, mention, user_id=None, lang=None):
    """
    Format text with mentions safely across all languages
    This ensures mentions are preserved during translation
    """
    if not mention or not text:
        return text
        
    # If English, just do normal formatting
    if lang == 'en' or (lang is None and user_id is not None and get_user_language(user_id) == 'en'):
        return text.replace("{mention}", mention)
    
    # First, preserve the mention by tokenizing it
    tokenized_text, mention_token, _ = preserve_mention(text, "{mention}")
    
    # Translate the tokenized text
    translated = await async_translate_to_lang(tokenized_text, user_id, lang)
    
    # Replace the token back with the actual mention
    result = translated.replace(mention_token, mention)
    
    return result

# Create a translation object for testing
if __name__ == "__main__":
    pass