

import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from pyrogram.types import CallbackQuery
from modules.lang import translate_to_lang, default_lang
from modules.chatlogs import channel_log
from config import DATABASE_URL

from pymongo import MongoClient


# Replace with your MongoDB connection string
client = MongoClient(DATABASE_URL)

# Access your database and collection
db = client["aibotdb"]
user_voice_collection = db["user_voice_setting"]


# Global dictionary for storing voice settings per user
voice_settings = {}



# Access or create the database and collection
user_lang_collection = db['user_lang']
user_voice_collection = db["user_voice_setting"]
ai_mode_collection = db['ai_mode']

modes = {
    "chatbot": "Chatbot",
    "coder": "Coder/Developer",
    "professional": "Professional",
    "teacher": "Teacher",
    "therapist": "Therapist",
    "assistant": "Personal Assistant",
    "gamer": "Gamer",
    "translator": "Translator"
}

languages = {
    "en": "🇬🇧 English",
    "hi": "🇮🇳 Hindi",
    "zh": "🇨🇳 Chinese",
    "ar": "🇸🇦 Arabic",
    "fr": "🇫🇷 French",
    "ru": "🇷🇺 Russian"
}

settings_text = """
**Setting Menu for User {mention}**

**User ID**: {user_id}
**User Language:** {default_lang}
**User Voice**: {voice_setting}
**User Mode**: {mode}

You can change your settings from below options.
"""



async def settings_inline(client, callback):
    settings_text = """
**Setting Menu for User {mention}**

**User ID**: {user_id}
**User Language:** {default_lang}
**User Voice**: {voice_setting}
**User Mode**: {mode}

You can change your settings from below options.
"""

    user_id = callback.from_user.id
    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
    if user_lang_doc:
        current_language = user_lang_doc['language']
    else:
        current_language = "en"
        user_lang_collection.insert_one({"user_id": user_id, "language": current_language})
    user_settings = user_voice_collection.find_one({"user_id": user_id})
    
    if user_settings:
        voice_setting = user_settings.get("voice", "voice")
    else:
        voice_setting = "voice"
        # If user doesn't exist, add them with default setting "voice"
        user_voice_collection.insert_one({"user_id": user_id, "voice": "voice"})
    
    user_mode_doc = ai_mode_collection.find_one({"user_id": user_id})

    if user_mode_doc:
        current_mode = user_mode_doc['mode']
    else:
        current_mode = "chatbot"
        ai_mode_collection.insert_one({"user_id": user_id, "mode": current_mode})
    
    current_mode_label = modes[current_mode]

    current_language=languages[current_language]
    settings_text = settings_text.format(
        mention=callback.from_user.mention,
        user_id=callback.from_user.id,
        default_lang=current_language,
        voice_setting=voice_setting,
        mode=current_mode_label,
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🌐 Language", callback_data="settings_lans"),
                InlineKeyboardButton("🎙️ Voice", callback_data="settings_v")
            ],
            [
                InlineKeyboardButton("🤖 Assistant", callback_data="settings_assistant"),
                InlineKeyboardButton("🔧 Others", callback_data="settings_others")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="back")
            ]
        ]
    )

    await callback.message.edit(
        text=settings_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )



async def settings_language_callback(client, callback):
    user_id = callback.from_user.id
    
    # Fetch user voice settings from MongoDB
    user_settings = user_voice_collection.find_one({"user_id": user_id})
    
    if user_settings:
        voice_setting = user_settings.get("voice", "voice")
    else:
        voice_setting = "voice"
        # If user doesn't exist, add them with default setting "voice"
        user_voice_collection.insert_one({"user_id": user_id, "voice": "voice"})

    print(f"Voice setting for {user_id}: {voice_setting}")
    # Update the button texts based on the user's current setting
    voice_button_text = "🎙️ Voice ✅" if voice_setting == "voice" else "🎙️ Voice"
    text_button_text = "💬 Text ✅" if voice_setting == "text" else "💬 Text"

    message_text = f"Current setting: Answering in {'Voice' if voice_setting == 'voice' else 'Text'} queries only."

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(voice_button_text, callback_data="settings_voice"),
                InlineKeyboardButton(text_button_text, callback_data="settings_text")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="settings_back")
            ]
        ]
    )

    await callback.message.edit(
        text=message_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )



async def change_voice_setting(client, callback):
    user_id = callback.from_user.id
    
    # Determine the new voice setting based on the callback data
    new_voice_setting = "voice" if callback.data == "settings_voice" else "text"

    # Update the voice setting in MongoDB
    user_voice_collection.update_one(
        {"user_id": user_id},
        {"$set": {"voice": new_voice_setting}},
        upsert=True
    )

    # Determine the current setting to display
    message_text = f"Current setting: Answering in {'Voice' if new_voice_setting == 'voice' else 'Text'} queries only."

    # Update the button texts with checkmarks
    voice_button_text = "🎙️ Voice ✅" if new_voice_setting == "voice" else "🎙️ Voice"
    text_button_text = "💬 Text ✅" if new_voice_setting == "text" else "💬 Text"

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(voice_button_text, callback_data="settings_voice"),
                InlineKeyboardButton(text_button_text, callback_data="settings_text")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="settings_back")
            ]
        ]
    )

    # Edit the message to reflect the new settings
    await callback.message.edit(
        text=message_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

# Function to handle settings inline
async def settings_voice_inlines(client, callback):
    settings_text = """
**Setting Menu for User {mention}**

**User ID**: {user_id}
**User Language:** {default_lang}
**User Voice**: {voice_setting}
**User Mode**: {mode}

You can change your settings from below options.
"""

    user_id = callback.from_user.id
    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
    if user_lang_doc:
        current_language = user_lang_doc['language']
    else:
        current_language = "en"
        user_lang_collection.insert_one({"user_id": user_id, "language": current_language})
    user_settings = user_voice_collection.find_one({"user_id": user_id})
    
    if user_settings:
        voice_setting = user_settings.get("voice", "voice")
    else:
        voice_setting = "voice"
        # If user doesn't exist, add them with default setting "voice"
        user_voice_collection.insert_one({"user_id": user_id, "voice": "voice"})
    
    user_mode_doc = ai_mode_collection.find_one({"user_id": user_id})

    if user_mode_doc:
        current_mode = user_mode_doc['mode']
    else:
        current_mode = "chatbot"
        ai_mode_collection.insert_one({"user_id": user_id, "mode": current_mode})
    
    current_mode_label = modes[current_mode]
    current_language=languages[current_language]


    settings_text = settings_text.format(
        mention=callback.from_user.mention,
        user_id=callback.from_user.id,
        default_lang=current_language,
        voice_setting=voice_setting,
        mode=current_mode_label,
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🌐 Language", callback_data="settings_lans"),
                InlineKeyboardButton("🎙️ Voice", callback_data="settings_v")
            ],
            [
                InlineKeyboardButton("🤖 Assistant", callback_data="settings_assistant"),
                InlineKeyboardButton("🔧 Others", callback_data="settings_others")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="back")
            ]
        ]
    )
    await callback.message.edit(
        text=settings_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )



