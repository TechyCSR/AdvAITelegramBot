import logging
from pyrogram import Client, filters
from config import DATABASE_URL, LOG_CHANNEL
from pymongo import MongoClient
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from modules.lang import translate_to_lang, get_user_language
from modules.maintenance import is_maintenance_mode
from modules.welcome import is_welcome_enabled
from modules.auto_delete import is_auto_delete_enabled

# Configure logging
logger = logging.getLogger(__name__)

# Initialize the MongoDB client
mongo_client = MongoClient(DATABASE_URL)

# Access or create the database and collection
db = mongo_client['aibotdb']
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

async def global_setting_command(client: Client, message: Message):
    try:
        # Get user's language
        user_lang = await get_user_language(message.from_user.id)
        
        # Get translated text
        translated_text = await translate_to_lang(
            "**Global Settings**\n\n"
            "Here you can configure global settings for the bot.\n\n"
            "**Current Settings:**\n"
            "• Maintenance Mode: {maintenance_status}\n"
            "• Welcome Message: {welcome_status}\n"
            "• Auto Delete: {auto_delete_status}\n"
            "• Log Channel: {log_channel_status}\n\n"
            "Use the buttons below to modify these settings.",
            message.from_user.id
        )
        
        # Get current settings
        maintenance_status = "Enabled" if await is_maintenance_mode() else "Disabled"
        welcome_status = "Enabled" if await is_welcome_enabled() else "Disabled"
        auto_delete_status = "Enabled" if await is_auto_delete_enabled() else "Disabled"
        log_channel_status = "Configured" if LOG_CHANNEL else "Not Configured"
        
        # Format the text with current settings
        formatted_text = translated_text.format(
            maintenance_status=maintenance_status,
            welcome_status=welcome_status,
            auto_delete_status=auto_delete_status,
            log_channel_status=log_channel_status
        )
        
        # Create inline keyboard
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    await translate_to_lang("Maintenance Mode", message.from_user.id),
                    callback_data="toggle_maintenance"
                )
            ],
            [
                InlineKeyboardButton(
                    await translate_to_lang("Welcome Message", message.from_user.id),
                    callback_data="toggle_welcome"
                )
            ],
            [
                InlineKeyboardButton(
                    await translate_to_lang("Auto Delete", message.from_user.id),
                    callback_data="toggle_auto_delete"
                )
            ],
            [
                InlineKeyboardButton(
                    await translate_to_lang("Log Channel", message.from_user.id),
                    callback_data="set_log_channel"
                )
            ]
        ])
        
        # Send the message
        await message.reply_text(
            formatted_text,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in global_setting_command: {e}")
        await message.reply_text(
            await translate_to_lang("Sorry, there was an error processing your request. Please try again.", message.from_user.id)
        )