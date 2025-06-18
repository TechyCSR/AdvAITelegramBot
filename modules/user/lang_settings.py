from pymongo import MongoClient
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import DATABASE_URL
from modules.lang import async_translate_to_lang

# Initialize the MongoDB client
mongo_client = MongoClient(DATABASE_URL)

# Access or create the database and collection
db = mongo_client['aibotdb']
user_lang_collection = db['user_lang']

# Dictionary of languages with flags
languages = {
    "en": "🇬🇧 English",
    "hi": "🇮🇳 Hindi",
    "zh": "🇨🇳 Chinese",
    "ar": "🇸🇦 Arabic",
    "fr": "🇫🇷 French",
    "ru": "🇷🇺 Russian"
}

# Function to handle settings language callback
async def settings_langs_callback(client, callback):
    user_id = callback.from_user.id
    
    # Fetch the user's current language from the database
    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
    if user_lang_doc:
        current_language = user_lang_doc['language']
    else:
        current_language = "en"
        user_lang_collection.insert_one({"user_id": user_id, "language": current_language})

    current_language_label = languages[current_language]
    
    # Translate current language text
    current_lang_text = await async_translate_to_lang("Current language:", user_id)
    message_text = f"{current_lang_text} {current_language_label}"

    # No need to translate language names as they're always displayed in their native form
    # But translate the Back button
    back_btn = await async_translate_to_lang("🔙 Back", user_id)

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🇮🇳 Hindi", callback_data="language_hi"),
                InlineKeyboardButton("🇬🇧 English", callback_data="language_en")
            ],
            [
                InlineKeyboardButton("🇨🇳 Chinese", callback_data="language_zh"),
                InlineKeyboardButton("🇸🇦 Arabic", callback_data="language_ar")
            ],
            [
                InlineKeyboardButton("🇫🇷 French", callback_data="language_fr"),
                InlineKeyboardButton("🇷🇺 Russian", callback_data="language_ru")
            ],
            [
                InlineKeyboardButton(back_btn, callback_data="settings_back")
            ]
        ]
    )

    await callback.message.edit(
        text=message_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

# Function to handle language setting change
async def change_language_setting(client, callback):
    user_id = callback.from_user.id
    new_language = callback.data.split("_")[1]

    # Update the user's language in the database
    user_lang_collection.update_one(
        {"user_id": user_id},
        {"$set": {"language": new_language}},
        upsert=True
    )

    current_language_label = languages[new_language]
    
    # Translate current language text 
    # Note: We translate using the NEW language setting
    current_lang_text = await async_translate_to_lang("Current language:", lang=new_language)
    message_text = f"{current_lang_text} {current_language_label}"

    # No need to translate language names as they're always displayed in their native form
    # But translate the Back button using the new language
    back_btn = await async_translate_to_lang("🔙 Back", lang=new_language)

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🇮🇳 Hindi", callback_data="language_hi"),
                InlineKeyboardButton("🇬🇧 English", callback_data="language_en")
            ],
            [
                InlineKeyboardButton("🇨🇳 Chinese", callback_data="language_zh"),
                InlineKeyboardButton("🇸🇦 Arabic", callback_data="language_ar")
            ],
            [
                InlineKeyboardButton("🇫🇷 French", callback_data="language_fr"),
                InlineKeyboardButton("🇷🇺 Russian", callback_data="language_ru")
            ],
            [
                InlineKeyboardButton(back_btn, callback_data="settings_back")
            ]
        ]
    )

    await callback.message.edit(
        text=message_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )


languages = {
    "en": "🇬🇧 English",
    "hi": "🇮🇳 Hindi",
    "zh": "🇨🇳 Chinese",
    "ar": "🇸🇦 Arabic",
    "fr": "🇫🇷 French",
    "ru": "🇷🇺 Russian"
}
