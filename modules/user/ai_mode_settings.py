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

# Initialize MongoDB client with optimized settings
client = MongoClient(DATABASE_URL, maxPoolSize=50, minPoolSize=10)
db = client["aibotdb"]
ai_mode_collection = db['user_ai_mode']

# Create index for faster queries
ai_mode_collection.create_index("user_id", unique=True)

# Cache for user AI mode settings with increased size
@lru_cache(maxsize=2000)
def get_user_ai_mode(user_id: int):
    """Get user AI mode with caching"""
    try:
        doc = ai_mode_collection.find_one({"user_id": user_id})
        return doc.get("mode", "chatbot") if doc else "chatbot"
    except Exception as e:
        logger.error(f"Error getting user AI mode: {e}")
        return "chatbot"

def update_user_ai_mode(user_id: int, mode: str):
    """Update user AI mode with optimized database operation"""
    try:
        ai_mode_collection.update_one(
            {"user_id": user_id},
            {"$set": {"mode": mode}},
            upsert=True
        )
        # Clear cache for this user
        get_user_ai_mode.cache_clear()
        return True
    except Exception as e:
        logger.error(f"Error updating user AI mode: {e}")
        return False

# Define AI modes with descriptions
ai_modes = {
    "chatbot": "🤖 General Chat - Friendly and helpful conversations",
    "coder": "💻 Code Assistant - Programming and technical help",
    "professional": "👔 Professional - Business and formal communication",
    "teacher": "👨‍🏫 Teacher - Educational and explanatory responses",
    "therapist": "🧠 Therapist - Supportive and empathetic conversations",
    "assistant": "👨‍💼 Personal Assistant - Task and information management",
    "gamer": "🎮 Gaming - Gaming-related discussions and help",
    "translator": "🌐 Translator - Language translation and cultural context"
}

ai_mode_settings_text = """
**🤖 AI Mode Settings**

Current Mode: {current_mode}

Select your preferred AI mode:
{modes_list}

Each mode is optimized for different types of interactions.
"""

async def settings_assistant_callback(client, callback):
    try:
        user_id = callback.from_user.id
        user_lang = get_user_language(user_id)
        
        # Get user AI mode
        ai_mode = ai_mode_collection.find_one({"user_id": user_id}) or {
            "mode": "chatbot"
        }
        
        # Format modes list
        modes_list = "\n".join([
            f"• {await translate_text_async(desc, user_lang)}"
            for mode, desc in ai_modes.items()
        ])
        
        # Format and translate message
        message_text = await translate_text_async(
            ai_mode_settings_text.format(
                current_mode=await translate_text_async(ai_modes[ai_mode["mode"]], user_lang),
                modes_list=modes_list
            ),
            user_lang
        )
        
        # Create keyboard with translated buttons
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{await translate_text_async('🤖 Chatbot', user_lang)} {'✅' if ai_mode['mode'] == 'chatbot' else ''}",
                        callback_data="mode_chatbot"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{await translate_text_async('💻 Coder', user_lang)} {'✅' if ai_mode['mode'] == 'coder' else ''}",
                        callback_data="mode_coder"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{await translate_text_async('👔 Professional', user_lang)} {'✅' if ai_mode['mode'] == 'professional' else ''}",
                        callback_data="mode_professional"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{await translate_text_async('👨‍🏫 Teacher', user_lang)} {'✅' if ai_mode['mode'] == 'teacher' else ''}",
                        callback_data="mode_teacher"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{await translate_text_async('🧠 Therapist', user_lang)} {'✅' if ai_mode['mode'] == 'therapist' else ''}",
                        callback_data="mode_therapist"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{await translate_text_async('👨‍💼 Assistant', user_lang)} {'✅' if ai_mode['mode'] == 'assistant' else ''}",
                        callback_data="mode_assistant"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{await translate_text_async('🎮 Gamer', user_lang)} {'✅' if ai_mode['mode'] == 'gamer' else ''}",
                        callback_data="mode_gamer"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{await translate_text_async('🌐 Translator', user_lang)} {'✅' if ai_mode['mode'] == 'translator' else ''}",
                        callback_data="mode_translator"
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
        logger.error(f"Error in settings_assistant_callback: {e}")
        await callback.answer("An error occurred. Please try again.", show_alert=True)

async def change_ai_mode(client, callback):
    try:
        user_id = callback.from_user.id
        user_lang = get_user_language(user_id)
        new_mode = callback.data.split("_")[1]
        
        # Update user AI mode
        ai_mode_collection.update_one(
            {"user_id": user_id},
            {"$set": {"mode": new_mode}},
            upsert=True
        )
        
        # Format and translate confirmation message
        message_text = await translate_text_async(
            f"AI mode changed to {await translate_text_async(ai_modes[new_mode], user_lang)}",
            user_lang
        )
        
        # Create updated keyboard
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"{await translate_text_async('🤖 Chatbot', user_lang)} {'✅' if new_mode == 'chatbot' else ''}",
                        callback_data="mode_chatbot"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{await translate_text_async('💻 Coder', user_lang)} {'✅' if new_mode == 'coder' else ''}",
                        callback_data="mode_coder"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{await translate_text_async('👔 Professional', user_lang)} {'✅' if new_mode == 'professional' else ''}",
                        callback_data="mode_professional"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{await translate_text_async('👨‍🏫 Teacher', user_lang)} {'✅' if new_mode == 'teacher' else ''}",
                        callback_data="mode_teacher"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{await translate_text_async('🧠 Therapist', user_lang)} {'✅' if new_mode == 'therapist' else ''}",
                        callback_data="mode_therapist"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{await translate_text_async('👨‍💼 Assistant', user_lang)} {'✅' if new_mode == 'assistant' else ''}",
                        callback_data="mode_assistant"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{await translate_text_async('🎮 Gamer', user_lang)} {'✅' if new_mode == 'gamer' else ''}",
                        callback_data="mode_gamer"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{await translate_text_async('🌐 Translator', user_lang)} {'✅' if new_mode == 'translator' else ''}",
                        callback_data="mode_translator"
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
                f"AI mode changed to {await translate_text_async(ai_modes[new_mode], user_lang)}",
                user_lang
            ),
            show_alert=True
        )
    except Exception as e:
        logger.error(f"Error in change_ai_mode: {e}")
        await callback.answer("Failed to change AI mode. Please try again.", show_alert=True) 