from googletrans import Translator
from pymongo import MongoClient
from config import DATABASE_URL
import functools
import time
import json
import os

# Initialize MongoDB client
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
user_lang_collection = db['user_lang']
translation_cache = db['translation_cache']

# Initialize translator
translator = Translator()

# Simple in-memory cache for translations to avoid repeated API calls
_translation_cache = {}

# Language resource files path
LANG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lang_resources')
os.makedirs(LANG_DIR, exist_ok=True)

# Store translations for UI elements
_ui_translation_cache = {}

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

def load_ui_translations(lang_code):
    """Load UI translations from file or create if doesn't exist"""
    if lang_code in _ui_translation_cache:
        return _ui_translation_cache[lang_code]
    
    lang_file = os.path.join(LANG_DIR, f"{lang_code}.json")
    
    # If file exists, load it
    if os.path.exists(lang_file):
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                translations = json.load(f)
                _ui_translation_cache[lang_code] = translations
                return translations
        except Exception as e:
            print(f"Error loading language file {lang_file}: {e}")
    
    # If we don't have translations yet, return empty dict
    return {}

def get_ui_message(message_key, user_id=None, lang=None):
    """Get translated UI message based on user language preference"""
    try:
        if lang is None and user_id is not None:
            lang = get_user_language(user_id)
        
        # Default to English if no language specified
        if lang is None:
            lang = 'en'
        
        # Load the language translations
        translations = load_ui_translations(lang)
        
        # If message exists in translations, return it
        if message_key in translations:
            return translations[message_key]
        
        # If not translated yet and not English, translate it
        if lang != 'en':
            # Get English version
            en_translations = load_ui_translations('en')
            
            # If not in English either, this is a new key
            if message_key not in en_translations:
                # Store the new key in English file for future translations
                en_translations[message_key] = message_key
                _ui_translation_cache['en'] = en_translations
                
                # Save updated English file
                lang_file = os.path.join(LANG_DIR, "en.json")
                with open(lang_file, 'w', encoding='utf-8') as f:
                    json.dump(en_translations, f, ensure_ascii=False, indent=2)
            
            # Translate from English to target language
            en_text = en_translations[message_key]
            translated = translate_to_lang(en_text, lang=lang)
            
            # Add to translations and save
            translations[message_key] = translated
            _ui_translation_cache[lang] = translations
            
            # Save updated translations file
            lang_file = os.path.join(LANG_DIR, f"{lang}.json")
            with open(lang_file, 'w', encoding='utf-8') as f:
                json.dump(translations, f, ensure_ascii=False, indent=2)
            
            return translated
        
        # If English or translation failed, return the key itself
        return message_key
        
    except Exception as e:
        print(f"UI translation error: {e}")
        return message_key  # Return message key if translation fails

# Initialize English language file if it doesn't exist
def init_language_files():
    """Initialize language files if they don't exist"""
    en_file = os.path.join(LANG_DIR, "en.json")
    if not os.path.exists(en_file):
        default_translations = {
            "start_message": "Welcome to the Advanced AI Chatbot! Ask me anything or use the commands below:",
            "help_message": "Here's how you can use this bot:",
            "settings_message": "Configure your preferences:",
            "language_changed": "Language changed successfully!"
            # Add more default English messages here
        }
        with open(en_file, 'w', encoding='utf-8') as f:
            json.dump(default_translations, f, ensure_ascii=False, indent=2)

# Initialize language files on module load
init_language_files()

# Create an async version for UI messages
async def async_get_ui_message(message_key, user_id=None, lang=None):
    """Async wrapper for get_ui_message function"""
    return get_ui_message(message_key, user_id, lang)

# while True:
#     print(translate_to_lang("Hello, How are you?"))
#     break