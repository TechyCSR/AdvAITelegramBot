from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import DATABASE_URL
from modules.lang import translate_to_lang, translate_text_async, get_user_language, get_language_display_name
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Initialize the MongoDB client with optimized settings
mongo_client = MongoClient(DATABASE_URL, maxPoolSize=50, minPoolSize=10)

# Access or create the database and collection
db = mongo_client['aibotdb']
user_lang_collection = db['user_lang']

# Create index for faster queries
user_lang_collection.create_index("user_id", unique=True)

language_text = """
**🌐 Language Settings**

Current Language: {current_language}

Select your preferred language from the options below.
"""

# Function to handle settings language callback
async def settings_langs_callback(client, callback):
    try:
        user_id = callback.from_user.id
        current_language = get_user_language(user_id)
        
        # Format and translate message
        message_text = await translate_text_async(
            language_text.format(current_language=get_language_display_name(current_language)),
            current_language
        )

        # Create language selection keyboard
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{get_language_display_name('hi')} {'✅' if current_language == 'hi' else ''}",
                        callback_data="language_hi"
                    ),
                    InlineKeyboardButton(
                        f"{get_language_display_name('en')} {'✅' if current_language == 'en' else ''}",
                        callback_data="language_en"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{get_language_display_name('zh')} {'✅' if current_language == 'zh' else ''}",
                        callback_data="language_zh"
                    ),
                    InlineKeyboardButton(
                        f"{get_language_display_name('ar')} {'✅' if current_language == 'ar' else ''}",
                        callback_data="language_ar"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{get_language_display_name('fr')} {'✅' if current_language == 'fr' else ''}",
                        callback_data="language_fr"
                    ),
                    InlineKeyboardButton(
                        f"{get_language_display_name('ru')} {'✅' if current_language == 'ru' else ''}",
                        callback_data="language_ru"
                    )
                ],
                [
                    InlineKeyboardButton(
                        await translate_text_async("🔙 Back", current_language),
                        callback_data="settings_back"
                    )
                ]
            ]
        )

        await callback.message.edit(
            text=message_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Error in settings_langs_callback: {e}")
        await callback.answer("An error occurred. Please try again.", show_alert=True)

# Function to handle language setting change
async def change_language_setting(client, callback):
    try:
        user_id = callback.from_user.id
        new_language = callback.data.split("_")[1]

        # Update the user's language in the database
        user_lang_collection.update_one(
            {"user_id": user_id},
            {"$set": {"language": new_language}},
            upsert=True
        )

        # Format and translate confirmation message
        message_text = await translate_text_async(
            f"Language changed to {get_language_display_name(new_language)}",
            new_language
        )

        # Create updated keyboard
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{get_language_display_name('hi')} {'✅' if new_language == 'hi' else ''}",
                        callback_data="language_hi"
                    ),
                    InlineKeyboardButton(
                        f"{get_language_display_name('en')} {'✅' if new_language == 'en' else ''}",
                        callback_data="language_en"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{get_language_display_name('zh')} {'✅' if new_language == 'zh' else ''}",
                        callback_data="language_zh"
                    ),
                    InlineKeyboardButton(
                        f"{get_language_display_name('ar')} {'✅' if new_language == 'ar' else ''}",
                        callback_data="language_ar"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{get_language_display_name('fr')} {'✅' if new_language == 'fr' else ''}",
                        callback_data="language_fr"
                    ),
                    InlineKeyboardButton(
                        f"{get_language_display_name('ru')} {'✅' if new_language == 'ru' else ''}",
                        callback_data="language_ru"
                    )
                ],
                [
                    InlineKeyboardButton(
                        await translate_text_async("🔙 Back", new_language),
                        callback_data="settings_back"
                    )
                ]
            ]
        )

        await callback.message.edit(
            text=message_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

        # Show success message
        await callback.answer(
            await translate_text_async(
                f"Language changed to {get_language_display_name(new_language)}",
                new_language
            ),
            show_alert=True
        )
    except Exception as e:
        logger.error(f"Error in change_language_setting: {e}")
        await callback.answer("Failed to change language. Please try again.", show_alert=True)


