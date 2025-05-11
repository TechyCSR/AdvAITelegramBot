from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from modules.lang import translate_text_async, get_user_language, get_language_display_name
import logging

# Configure logging
logger = logging.getLogger(__name__)

commands_text = """
**📝 Available Commands**

🤖 **Chat Commands**
• /start - {start_desc}
• /help - {help_desc}
• /commands - {commands_desc}
• /newchat - {newchat_desc}
• /settings - {settings_desc}

🎨 **Image Commands**
• /generate [prompt] - {generate_desc}
• /img [prompt] - {img_desc}
• {image_ai_desc}

🔊 **Voice Commands**
• {voice_to_text_desc}
• {text_to_voice_desc}

⚙️ **Settings Commands**
• /language - {language_desc}
• /voice - {voice_desc}
• /mode - {mode_desc}

{help_tip}
"""

async def command_inline(client, callback):
    try:
        user_id = callback.from_user.id
        user_lang = get_user_language(user_id)
        
        # Translate command descriptions
        translated_descriptions = {
            "start_desc": await translate_text_async("Start the bot", user_lang),
            "help_desc": await translate_text_async("Show help menu", user_lang),
            "commands_desc": await translate_text_async("Show this commands list", user_lang),
            "newchat_desc": await translate_text_async("Start a new conversation", user_lang),
            "settings_desc": await translate_text_async("Open settings menu", user_lang),
            "generate_desc": await translate_text_async("Generate images from text", user_lang),
            "img_desc": await translate_text_async("Alternative for generate", user_lang),
            "image_ai_desc": await translate_text_async("Send an image with caption 'ai' to analyze it", user_lang),
            "voice_to_text_desc": await translate_text_async("Send a voice message to convert to text", user_lang),
            "text_to_voice_desc": await translate_text_async("Use /tts [text] to convert text to voice", user_lang),
            "language_desc": await translate_text_async("Change language", user_lang),
            "voice_desc": await translate_text_async("Change voice settings", user_lang),
            "mode_desc": await translate_text_async("Change AI mode", user_lang),
            "help_tip": await translate_text_async("Use the buttons below to navigate or type /help for more information.", user_lang)
        }
        
        # Format commands text with translated descriptions
        message_text = commands_text.format(**translated_descriptions)
        
        # Create keyboard with translated buttons
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        await translate_text_async("❓ Help", user_lang),
                        callback_data="help"
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
            message_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Error in command_inline: {e}")
        await callback.answer("An error occurred. Please try again.", show_alert=True)
    


