

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

# Initialize the MongoDB client
mongo_client = MongoClient(DATABASE_URL)

# Access or create the database and collection
db = mongo_client['aibotdb']
user_voice_collection = db['user_voice']


# Global dictionary for storing voice settings per user
voice_settings = {}

settings_text = """
**Settings Menu**

**User** = {mention}
**Language** = {default_lang}

"""


async def settings_inline(client, callback):
    global settings_text
    settings_text = settings_text.format(
        mention=callback.from_user.mention,
        default_lang=default_lang
    )
    
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🌐 Language", callback_data="settings_lans"),
                InlineKeyboardButton("🎙️ Voice", callback_data="settings_voice")
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
    voice_enabled = user_settings.get("voice", True) if user_settings else True

    # Update the button texts based on the user's current setting
    if voice_enabled:
        voice_button_text = "🎙️ Voice ✅"
        text_button_text = "💬 Text"
    else:
        voice_button_text = "🎙️ Voice"
        text_button_text = "💬 Text ✅"

    message_text = f"Current setting: Answering in {'Voice' if voice_enabled else 'Text'} queries only."

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


# Function to handle voice setting change
async def change_voice_setting(client, callback):
    user_id = callback.from_user.id
    
    # Determine the new voice setting based on the callback data
    if callback.data == "settings_voice":
        new_voice_setting = True
    else:  # "settings_text"
        new_voice_setting = False

    # Update the voice setting in MongoDB
    user_voice_collection.update_one(
        {"user_id": user_id},
        {"$set": {"voice": new_voice_setting}},
        upsert=True
    )

    # Determine the current setting to display
    current_setting = "Voice" if new_voice_setting else "Text"
    message_text = f"Current setting: Answering in {current_setting} queries only."

    # Update the button texts with checkmarks
    voice_button_text = "🎙️ Voice ✅" if new_voice_setting else "🎙️ Voice"
    text_button_text = "💬 Text" if new_voice_setting else "💬 Text ✅"

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
    global settings_text
    settings_text = settings_text.format(
        mention=callback.from_user.mention,
        default_lang=default_lang
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🌐 Language", callback_data="settings_lans"),
                InlineKeyboardButton("🎙️ Voice", callback_data="settings_voice")
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



