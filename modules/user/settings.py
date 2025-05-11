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
from pyrogram import Client
from modules.auto_delete import is_auto_delete_enabled
from modules.welcome import is_welcome_enabled
from modules.user.ai_mode_settings import get_user_ai_mode
from modules.user.voice_settings import get_user_voice

# Configure logging
logger = logging.getLogger(__name__)

# Initialize MongoDB client with optimized settings
client = MongoClient(DATABASE_URL, maxPoolSize=50, minPoolSize=10)

# Access database and collections
db = client["aibotdb"]
user_lang_collection = db['user_lang']
user_voice_collection = db["user_voice_setting"]
ai_mode_collection = db['ai_mode']

# Create indexes for faster queries
user_lang_collection.create_index("user_id", unique=True)
user_voice_collection.create_index("user_id", unique=True)
ai_mode_collection.create_index("user_id", unique=True)

# Define supported languages
languages = {
    "en": "English",
    "hi": "Hindi",
    "zh": "Chinese",
    "ar": "Arabic",
    "fr": "French",
    "ru": "Russian"
}

# Define AI modes
modes = {
    "chatbot": "🤖 Chatbot",
    "coder": "👨‍💻 Coder/Developer",
    "professional": "👔 Professional",
    "teacher": "👨‍🏫 Teacher",
    "therapist": "🧠 Therapist",
    "assistant": "👨‍💼 Personal Assistant",
    "gamer": "🎮 Gamer",
    "translator": "🌐 Translator"
}

async def get_user_settings(user_id: int):
    """Get all user settings in one database query"""
    settings = {
        'language': 'en',
        'voice': 'voice',
        'mode': 'chatbot'
    }
    
    try:
        # Get language
        lang_doc = user_lang_collection.find_one({"user_id": user_id})
        if lang_doc:
            settings['language'] = lang_doc['language']
        
        # Get voice setting
        voice_doc = user_voice_collection.find_one({"user_id": user_id})
        if voice_doc:
            settings['voice'] = voice_doc.get("voice", "voice")
        
        # Get AI mode
        mode_doc = ai_mode_collection.find_one({"user_id": user_id})
        if mode_doc:
            settings['mode'] = mode_doc['mode']
    except Exception as e:
        logger.error(f"Error getting user settings: {e}")
    
    return settings

@Client.on_message(filters.command("settings"))
async def settings_command(client, message):
    try:
        # Get user settings
        settings = await get_user_settings(message.from_user.id)
        
        # Get user details
        user = message.from_user
        user_id = user.id
        username = user.username or "Not set"
        first_name = user.first_name or "Not set"
        last_name = user.last_name or "Not set"
        
        # Get additional preferences
        auto_delete = await is_auto_delete_enabled()
        welcome = await is_welcome_enabled()
        
        # Format user details
        user_details = (
            f"👤 **User Details**\n"
            f"├ ID: `{user_id}`\n"
            f"├ Username: @{username}\n"
            f"├ First Name: {first_name}\n"
            f"└ Last Name: {last_name}\n\n"
            f"⚙️ **Preferences**\n"
            f"├ Language: {languages.get(settings['language'], settings['language'])}\n"
            f"├ AI Mode: {modes.get(settings['mode'], settings['mode'])}\n"
            f"├ Voice: {settings['voice'].capitalize()}\n"
            f"├ Auto Delete: {'Enabled' if auto_delete else 'Disabled'}\n"
            f"└ Welcome Message: {'Enabled' if welcome else 'Disabled'}"
        )
        
        # Create keyboard with single button
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Bot Link", url="https://t.me/your_bot_username")]
        ])
        
        # Send message
        await message.reply_text(
            user_details,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in settings command: {e}")
        await message.reply_text("An error occurred while fetching settings. Please try again later.")

@Client.on_callback_query(filters.regex("^settings_"))
async def settings_inline(client, callback_query):
    try:
        # Get user settings
        settings = await get_user_settings(callback_query.from_user.id)
        
        # Get user details
        user = callback_query.from_user
        user_id = user.id
        username = user.username or "Not set"
        first_name = user.first_name or "Not set"
        last_name = user.last_name or "Not set"
        
        # Get additional preferences
        auto_delete = await is_auto_delete_enabled()
        welcome = await is_welcome_enabled()
        
        # Format user details
        user_details = (
            f"👤 **User Details**\n"
            f"├ ID: `{user_id}`\n"
            f"├ Username: @{username}\n"
            f"├ First Name: {first_name}\n"
            f"└ Last Name: {last_name}\n\n"
            f"⚙️ **Preferences**\n"
            f"├ Language: {languages.get(settings['language'], settings['language'])}\n"
            f"├ AI Mode: {modes.get(settings['mode'], settings['mode'])}\n"
            f"├ Voice: {settings['voice'].capitalize()}\n"
            f"├ Auto Delete: {'Enabled' if auto_delete else 'Disabled'}\n"
            f"└ Welcome Message: {'Enabled' if welcome else 'Disabled'}"
        )
        
        # Create keyboard with single button
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Bot Link", url="https://t.me/your_bot_username")]
        ])
        
        # Edit message
        await callback_query.message.edit_text(
            user_details,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in settings inline: {e}")
        await callback_query.answer("An error occurred. Please try again.", show_alert=True)

async def settings_back_callback(client, callback):
    try:
        user_id = callback.from_user.id
        user_lang = get_user_language(user_id)
        
        # Format and translate message
        message_text = await translate_text_async(
            "Returning to main menu...",
            user_lang
        )
        
        # Create keyboard with translated buttons
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        await translate_text_async("❓ Help", user_lang),
                        callback_data="help"
                    ),
                    InlineKeyboardButton(
                        await translate_text_async("📝 Commands", user_lang),
                        callback_data="commands"
                    )
                ],
                [
                    InlineKeyboardButton(
                        await translate_text_async("⚙️ Settings", user_lang),
                        callback_data="settings"
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
        logger.error(f"Error in settings_back_callback: {e}")
        await callback.answer("An error occurred. Please try again.", show_alert=True)

async def settings_language_callback(client, callback):
    try:
        user_id = callback.from_user.id
        settings = await get_user_settings(user_id)
        current_language = settings['language']
        
        # Format and translate message
        message_text = await translate_text_async(
            "Select your preferred language:",
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
        logger.error(f"Error in settings_language_callback: {e}")
        await callback.answer("An error occurred. Please try again.", show_alert=True)

async def change_language(client, callback):
    try:
        user_id = callback.from_user.id
        new_language = callback.data.split('_')[1]
        
        # Update language setting
        if not update_user_settings(user_id, 'language', new_language):
            await callback.answer("Invalid language selection", show_alert=True)
            return
        
        # Get updated settings
        settings = await get_user_settings(user_id)
        
        # Format and translate confirmation message
        message_text = await translate_text_async(
            f"Language changed to {get_language_display_name(new_language)}",
            new_language
        )
        
        # Create language selection keyboard
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
        logger.error(f"Error in change_language: {e}")
        await callback.answer("Failed to change language. Please try again.", show_alert=True)

async def change_voice_setting(client, callback):
    try:
        user_id = callback.from_user.id
        
        # Determine the new voice setting
        new_voice_setting = "voice" if callback.data == "settings_voice" else "text"

        # Update voice setting using optimized function
        update_user_settings(user_id, 'voice', new_voice_setting)

        # Get current language
        settings = await get_user_settings(user_id)

        # Format and translate message
        message_text = await translate_text_async(
            f"Current setting: Answering in {'Voice' if new_voice_setting == 'voice' else 'Text'} queries only.",
            settings['language']
        )

        # Update button texts with translations
        voice_button_text = await translate_text_async("🎙️ Voice", settings['language'])
        text_button_text = await translate_text_async("💬 Text", settings['language'])
        
        if new_voice_setting == "voice":
            voice_button_text += " ✅"
        else:
            text_button_text += " ✅"

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(voice_button_text, callback_data="settings_voice"),
                    InlineKeyboardButton(text_button_text, callback_data="settings_text")
                ],
                [
                    InlineKeyboardButton(
                        await translate_text_async("🔙 Back", settings['language']),
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
        print(f"Error in change_voice_setting: {e}")
        await callback.answer("An error occurred. Please try again.", show_alert=True)

async def settings_voice_inlines(client, callback):
    try:
        user_id = callback.from_user.id
        
        # Get all user settings in one go
        settings = await get_user_settings(user_id)
        
        # Format settings for display
        current_language_label = languages[settings['language']]
        voice_setting = "Text" if settings['voice'] == "text" else "Voice"
        current_mode_label = modes[settings['mode']]

        # Format text first
        formatted_text = settings_text.format(
            mention=callback.from_user.mention,
            user_id_str=str(user_id),
            language=current_language_label,
            voice_setting=voice_setting,
            mode=current_mode_label
        )

        # Then translate
        translated_text = await translate_text_async(formatted_text, settings['language'])

        # Create keyboard with translated buttons
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        await translate_text_async("🌐 Language", settings['language']),
                        callback_data="settings_lans"
                    ),
                    InlineKeyboardButton(
                        await translate_text_async("🎙️ Voice", settings['language']),
                        callback_data="settings_v"
                    )
                ],
                [
                    InlineKeyboardButton(
                        await translate_text_async("🤖 AI Mode", settings['language']),
                        callback_data="settings_assistant"
                    ),
                    InlineKeyboardButton(
                        await translate_text_async("⚡ Others", settings['language']),
                        callback_data="settings_others"
                    )
                ],
                [
                    InlineKeyboardButton(
                        await translate_text_async("🔙 Back", settings['language']),
                        callback_data="back"
                    )
                ]
            ]
        )

        await callback.message.edit(
            text=translated_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"Error in settings_voice_inlines: {e}")
        await callback.answer("An error occurred. Please try again.", show_alert=True)



