from googletrans import Translator
from pymongo import MongoClient
from config import DATABASE_URL

# Initialize MongoDB client
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
user_lang_collection = db['user_lang']

# Initialize translator
translator = Translator()

def get_user_language(user_id):
    """Get user's preferred language from database"""
    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
    if user_lang_doc:
        return user_lang_doc['language']
    return 'en'  # Default to English if not set

def translate_to_lang(text, user_id=None, lang=None):
    """Translate text to user's preferred language or specified language"""
    try:
        if lang is None and user_id is not None:
            lang = get_user_language(user_id)
        
        if lang == 'en':  # No need to translate if target is English
            return text
            
        translation = translator.translate(text, src='en', dest=lang)
        return translation.text
    except Exception as e:
        print(f"Translation error: {e}")
        return text  # Return original text if translation fails

# while True:
#     print(translate_to_lang("Hello, How are you?"))
#     break