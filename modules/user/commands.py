from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from modules.lang import translate_text_async, get_user_language
import logging
from typing import Dict, List
import asyncio

# Configure logging
logger = logging.getLogger(__name__)

class CommandTemplates:
    COMMANDS = """
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

    DESCRIPTIONS = {
        "start_desc": "Start the bot",
        "help_desc": "Show help menu",
        "commands_desc": "Show this commands list",
        "newchat_desc": "Start a new conversation",
        "settings_desc": "Open settings menu",
        "generate_desc": "Generate images from text",
        "img_desc": "Alternative for generate",
        "image_ai_desc": "Send an image with caption 'ai' to analyze it",
        "voice_to_text_desc": "Send a voice message to convert to text",
        "text_to_voice_desc": "Use /tts [text] to convert text to voice",
        "language_desc": "Change language",
        "voice_desc": "Change voice settings",
        "mode_desc": "Change AI mode",
        "help_tip": "Use the buttons below to navigate or type /help for more information."
    }

class CommandHandler:
    @staticmethod
    async def create_navigation_keyboard(user_id: int) -> InlineKeyboardMarkup:
        user_lang = await get_user_language(user_id)
        buttons = [
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
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    async def get_translated_descriptions(user_lang: str) -> Dict[str, str]:
        tasks = [
            translate_text_async(desc, user_lang)
            for desc in CommandTemplates.DESCRIPTIONS.values()
        ]
        translated_descriptions = await asyncio.gather(*tasks)
        return dict(zip(CommandTemplates.DESCRIPTIONS.keys(), translated_descriptions))

    @staticmethod
    async def handle_command_inline(client: Client, callback: CallbackQuery):
        try:
            user_id = callback.from_user.id
            user_lang = await get_user_language(user_id)
            
            translated_descriptions = await CommandHandler.get_translated_descriptions(user_lang)
            message_text = CommandTemplates.COMMANDS.format(**translated_descriptions)
            keyboard = await CommandHandler.create_navigation_keyboard(user_id)
            
            await callback.message.edit_text(
                message_text,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Error in command_inline: {e}")
            await callback.answer("An error occurred. Please try again.", show_alert=True)

async def command_inline(client: Client, callback: CallbackQuery):
    await CommandHandler.handle_command_inline(client, callback)
    


