

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Global dictionary for storing language settings per user
language_settings = {}

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
    # Set default value to English if not set
    if user_id not in language_settings:
        language_settings[user_id] = "en"

    current_language = languages[language_settings[user_id]]
    message_text = f"Current language: {current_language}"

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
                InlineKeyboardButton("🔙 Back", callback_data="settings_back")
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
    language_settings[user_id] = callback.data.split("_")[1]

    current_language = languages[language_settings[user_id]]
    message_text = f"Current language: {current_language}"

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
                InlineKeyboardButton("🔙 Back", callback_data="settings_back")
            ]
        ]
    )

    await callback.message.edit(
        text=message_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )



# # Function to handle settings inline
# async def settings_inline(client, callback):
#     global settings_text
#     keyboard = InlineKeyboardMarkup(
#         [
#             [
#                 InlineKeyboardButton("🌐 Language", callback_data="settings_language"),
#                 InlineKeyboardButton("🎙️ Voice", callback_data="settings_voice")
#             ],
#             [
#                 InlineKeyboardButton("🤖 Assistant", callback_data="settings_assistant"),
#                 InlineKeyboardButton("🔧 Others", callback_data="settings_others")
#             ],
#             [
#                 InlineKeyboardButton("🔙 Back", callback_data="back")
#             ]
#         ]
#     )
#     await callback.message.edit(
#         text=settings_text,
#         reply_markup=keyboard,
#         disable_web_page_preview=True
#     )

