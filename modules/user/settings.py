

import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from pyrogram.types import CallbackQuery
from modules.lang import translate_to_lang, default_lang

from modules.chatlogs import channel_log


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





# Function to handle settings language callback
async def settings_language_callback(client, callback):
    user_id = callback.from_user.id
    # Set default value to True (Voice) if not set
    if user_id not in voice_settings:
        voice_settings[user_id] = True

    current_setting = "Voice" if voice_settings[user_id] else "Text"
    message_text = f"Current setting: Answering in {current_setting} queries only."

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎙️ Voice", callback_data="settings_voice"),
                InlineKeyboardButton("💬 Text", callback_data="settings_text")
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
    if callback.data == "settings_voice":
        voice_settings[user_id] = True
    else:
        voice_settings[user_id] = False
    current_setting = "Voice" if voice_settings[user_id] else "Text"
    message_text = f"Current setting: Answering in {current_setting} queries only."

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎙️ Voice", callback_data="settings_voice"),
                InlineKeyboardButton("💬 Text", callback_data="settings_text")
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



