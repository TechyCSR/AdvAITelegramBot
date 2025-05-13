import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from pyrogram.types import CallbackQuery
from modules.lang import async_translate_to_lang
from modules.chatlogs import channel_log
from config import DATABASE_URL

from pymongo import MongoClient

# Replace with your MongoDB connection string
client = MongoClient(DATABASE_URL)

# Access your database and collection
db = client["aibotdb"]
user_voice_collection = db["user_voice_setting"]

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
**User Language:** {language}
**User Voice**: {voice_setting}
**User Mode**: {mode}

You can change your settings from below options.

**@AdvChatGptBot**
"""

async def settings_inline(client, callback):
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
        user_voice_collection.insert_one({"user_id": user_id, "voice": "voice"})
    
    user_mode_doc = ai_mode_collection.find_one({"user_id": user_id})
    if user_mode_doc:
        current_mode = user_mode_doc['mode']
    else:
        current_mode = "chatbot"
        ai_mode_collection.insert_one({"user_id": user_id, "mode": current_mode})
    
    current_mode_label = modes[current_mode]
    current_language_label = languages[current_language]

    translated_text = await async_translate_to_lang(settings_text, user_id)
    formatted_text = translated_text.format(
        mention=callback.from_user.mention,
        user_id=callback.from_user.id,
        language=current_language_label,
        voice_setting=voice_setting,
        mode=current_mode_label,
    )

    # Translate button labels
    language_btn = await async_translate_to_lang("🌐 Language", user_id)
    voice_btn = await async_translate_to_lang("🎙️ Voice", user_id)
    assistant_btn = await async_translate_to_lang("🤖 Assistant", user_id)
    others_btn = await async_translate_to_lang("🔧 Others", user_id)
    back_btn = await async_translate_to_lang("🔙 Back", user_id)

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(language_btn, callback_data="settings_lans"),
                InlineKeyboardButton(voice_btn, callback_data="settings_v")
            ],
            [
                InlineKeyboardButton(assistant_btn, callback_data="settings_assistant"),
                InlineKeyboardButton(others_btn, callback_data="settings_others")
            ],
            [
                InlineKeyboardButton(back_btn, callback_data="back")
            ]
        ]
    )

    await callback.message.edit(
        text=formatted_text,
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
    
    # Translate base text and options
    voice_text = await async_translate_to_lang("Voice", user_id)
    text_option = await async_translate_to_lang("Text", user_id)
    current_setting = await async_translate_to_lang("Current setting: Answering in", user_id)
    queries_only = await async_translate_to_lang("queries only.", user_id)
    back_btn = await async_translate_to_lang("🔙 Back", user_id)
    
    # Update the button texts based on the user's current setting
    voice_button_text = f"🎙️ {voice_text} ✅" if voice_setting == "voice" else f"🎙️ {voice_text}"
    text_button_text = f"💬 {text_option} ✅" if voice_setting == "text" else f"💬 {text_option}"

    # Create the message text with translated components
    message_text = f"{current_setting} {voice_text if voice_setting == 'voice' else text_option} {queries_only}"

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(voice_button_text, callback_data="settings_voice"),
                InlineKeyboardButton(text_button_text, callback_data="settings_text")
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

    # Translate base text and options
    voice_text = await async_translate_to_lang("Voice", user_id)
    text_option = await async_translate_to_lang("Text", user_id)
    current_setting = await async_translate_to_lang("Current setting: Answering in", user_id)
    queries_only = await async_translate_to_lang("queries only.", user_id)
    back_btn = await async_translate_to_lang("🔙 Back", user_id)

    # Create the message text with translated components
    message_text = f"{current_setting} {voice_text if new_voice_setting == 'voice' else text_option} {queries_only}"

    # Update the button texts with checkmarks
    voice_button_text = f"🎙️ {voice_text} ✅" if new_voice_setting == "voice" else f"🎙️ {voice_text}"
    text_button_text = f"💬 {text_option} ✅" if new_voice_setting == "text" else f"💬 {text_option}"

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(voice_button_text, callback_data="settings_voice"),
                InlineKeyboardButton(text_button_text, callback_data="settings_text")
            ],
            [
                InlineKeyboardButton(back_btn, callback_data="settings_back")
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
**User Language:** {language}
**User Voice**: {voice_setting}
**User Mode**: {mode}

You can change your settings from below options.

**@AdvChatGptBot**
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
    current_language_label = languages[current_language]

    translated_text = await async_translate_to_lang(settings_text, user_id)
    formatted_text = translated_text.format(
        mention=callback.from_user.mention,
        user_id=callback.from_user.id,
        language=current_language_label,
        voice_setting=voice_setting,
        mode=current_mode_label,
    )
    
    # Translate button labels
    language_btn = await async_translate_to_lang("🌐 Language", user_id)
    voice_btn = await async_translate_to_lang("🎙️ Voice", user_id)
    assistant_btn = await async_translate_to_lang("🤖 Assistant", user_id)
    others_btn = await async_translate_to_lang("🔧 Others", user_id)
    back_btn = await async_translate_to_lang("🔙 Back", user_id)
    
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(language_btn, callback_data="settings_lans"),
                InlineKeyboardButton(voice_btn, callback_data="settings_v")
            ],
            [
                InlineKeyboardButton(assistant_btn, callback_data="settings_assistant"),
                InlineKeyboardButton(others_btn, callback_data="settings_others")
            ],
            [
                InlineKeyboardButton(back_btn, callback_data="back")
            ]
        ]
    )
    await callback.message.edit(
        text=formatted_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )



