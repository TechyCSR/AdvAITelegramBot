import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message, InlineQuery, CallbackQuery
from modules.lang import translate_to_lang, translate_text_async, get_user_language, get_language_display_name
from modules.chatlogs import channel_log
from config import DATABASE_URL
from functools import lru_cache
import logging
from pymongo import MongoClient

# Configure logging
logger = logging.getLogger(__name__)

# Initialize the MongoDB client with optimized settings
mongo_client = MongoClient(DATABASE_URL, maxPoolSize=50, minPoolSize=10)

# Access or create the database and collection
db = mongo_client['aibotdb']
user_voice_collection = db['user_voice']

# Create index for faster queries
user_voice_collection.create_index("user_id", unique=True)

# Cache for user voice settings with increased size
@lru_cache(maxsize=2000)
def get_user_voice_setting(user_id: int):
    """Get user voice setting with caching"""
    try:
        doc = user_voice_collection.find_one({"user_id": user_id})
        return doc.get("voice_mode", "text") if doc else "text"
    except Exception as e:
        logger.error(f"Error getting user voice setting: {e}")
        return "text"

def update_user_voice_setting(user_id: int, voice_setting: str):
    """Update user voice setting with optimized database operation"""
    try:
        user_voice_collection.update_one(
            {"user_id": user_id},
            {"$set": {"voice_mode": voice_setting}},
            upsert=True
        )
        # Clear cache for this user
        get_user_voice_setting.cache_clear()
        return True
    except Exception as e:
        logger.error(f"Error updating user voice setting: {e}")
        return False

voice_settings_text = """
**🔊 Voice Settings**

Current Mode: {voice_mode}

Select your preferred voice mode:
• Text Mode: Receive responses as text messages
• Voice Mode: Receive responses as voice messages

Note: Voice mode may take longer to respond but provides a more natural experience.
"""

async def settings_voice_callback(client, callback):
    try:
        user_id = callback.from_user.id
        user_lang = get_user_language(user_id)
        
        # Get user voice settings
        voice_settings = user_voice_collection.find_one({"user_id": user_id}) or {
            "voice_mode": "text"
        }
        
        # Format and translate message
        message_text = await translate_text_async(
            voice_settings_text.format(
                voice_mode=voice_settings["voice_mode"].capitalize()
            ),
            user_lang
        )
        
        # Create keyboard with translated buttons
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"💬 {await translate_text_async('Text Mode', user_lang)} {'✅' if voice_settings['voice_mode'] == 'text' else ''}",
                        callback_data="settings_text"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"🎙️ {await translate_text_async('Voice Mode', user_lang)} {'✅' if voice_settings['voice_mode'] == 'voice' else ''}",
                        callback_data="settings_voice"
                    )
                ],
                [
                    InlineKeyboardButton(
                        await translate_text_async("🔙 Back", user_lang),
                        callback_data="settings_back"
                    )
                ]
            ]
        )
        
        await callback.message.edit_text(
            message_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Error in settings_voice_callback: {e}")
        await callback.answer("An error occurred. Please try again.", show_alert=True)

async def change_voice_setting(client, callback):
    try:
        user_id = callback.from_user.id
        user_lang = get_user_language(user_id)
        new_mode = "voice" if callback.data == "settings_voice" else "text"
        
        # Update user voice settings
        user_voice_collection.update_one(
            {"user_id": user_id},
            {"$set": {"voice_mode": new_mode}},
            upsert=True
        )
        
        # Format and translate confirmation message
        message_text = await translate_text_async(
            f"Voice mode changed to {new_mode.capitalize()}",
            user_lang
        )
        
        # Create updated keyboard
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"💬 {await translate_text_async('Text Mode', user_lang)} {'✅' if new_mode == 'text' else ''}",
                        callback_data="settings_text"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"🎙️ {await translate_text_async('Voice Mode', user_lang)} {'✅' if new_mode == 'voice' else ''}",
                        callback_data="settings_voice"
                    )
                ],
                [
                    InlineKeyboardButton(
                        await translate_text_async("🔙 Back", user_lang),
                        callback_data="settings_back"
                    )
                ]
            ]
        )
        
        await callback.message.edit_text(
            message_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
        # Show success message
        await callback.answer(
            await translate_text_async(
                f"Voice mode changed to {new_mode.capitalize()}",
                user_lang
            ),
            show_alert=True
        )
    except Exception as e:
        logger.error(f"Error in change_voice_setting: {e}")
        await callback.answer("Failed to change voice mode. Please try again.", show_alert=True) 