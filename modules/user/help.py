from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from modules.lang import translate_text_async, get_user_language, get_language_display_name
import logging

# Configure logging
logger = logging.getLogger(__name__)

help_text = """
**❓ Help Menu**

Here are the main features I can help you with:

🤖 **Chat Features**
• Natural conversations
• Context-aware responses
• Multiple AI personalities
• Code assistance
• Translation support

🎨 **Image Generation**
• Create images from text
• Multiple style options
• High-quality outputs

🔤 **Text-to-Speech**
• Convert text to voice
• Multiple voice options
• Natural-sounding speech

🎤 **Speech-to-Text**
• Convert voice to text
• Support for multiple languages
• Accurate transcription

⚙️ **Settings**
• Language preferences
• Voice settings
• AI mode selection
• Other preferences

Use the buttons below to navigate or type /commands for a list of available commands.
"""

async def help(client, message):
    try:
        user_id = message.from_user.id
        user_lang = get_user_language(user_id)
        
        # Translate help message
        translated_text = await translate_text_async(help_text, user_lang)
        
        # Create keyboard with translated buttons
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        await translate_text_async("📝 Commands", user_lang),
                        callback_data="commands"
                    ),
                    InlineKeyboardButton(
                        await translate_text_async("⚙️ Settings", user_lang),
                        callback_data="settings"
                    )
                ],
                [
                    InlineKeyboardButton(
                        await translate_text_async("🔙 Back", user_lang),
                        callback_data="back"
                    )
                ]
            ]
        )
        
        await message.reply_text(
            translated_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await message.reply_text("An error occurred. Please try again.")

async def help_inline(client, callback):
    try:
        user_id = callback.from_user.id
        user_lang = get_user_language(user_id)
        
        # Translate help message
        translated_text = await translate_text_async(help_text, user_lang)
        
        # Create keyboard with translated buttons
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        await translate_text_async("📝 Commands", user_lang),
                        callback_data="commands"
                    ),
                    InlineKeyboardButton(
                        await translate_text_async("⚙️ Settings", user_lang),
                        callback_data="settings"
                    )
                ],
                [
                    InlineKeyboardButton(
                        await translate_text_async("🔙 Back", user_lang),
                        callback_data="back"
                    )
                ]
            ]
        )
        
        await callback.message.edit_text(
            translated_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Error in help_inline: {e}")
        await callback.answer("An error occurred. Please try again.", show_alert=True)
    
