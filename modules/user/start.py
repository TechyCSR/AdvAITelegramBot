from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from modules.lang import translate_text_async, get_user_language
import database.user_db as user_db
import logging
from typing import List, Dict
import asyncio

logger = logging.getLogger(__name__)

class ButtonManager:
    _buttons: Dict[str, List[str]] = {
        "main": ["Add to Group", "Commands", "Help", "Settings", "Support"],
        "navigation": ["❓ Help", "⚙️ Settings", "🔙 Back"]
    }
    
    @classmethod
    async def get_translated_buttons(cls, user_id: int, button_type: str) -> List[str]:
        user_lang = await get_user_language(user_id)
        return [await translate_text_async(btn, user_lang) for btn in cls._buttons[button_type]]

class MessageTemplates:
    WELCOME = """
**Welcome {user_mention}!** 👋

I'm an advanced AI-powered Telegram bot that can:
- Chat intelligently using GPT-4
- Convert voice messages to text and vice versa
- Generate images from text descriptions
- Extract text from images
- Support multiple languages

Use the buttons below to explore my features!

**@AdvChatGptBot**
"""
    TIP = "💡 Tip: You can use /help to see all available commands!"

class StartHandler:
    @staticmethod
    async def create_keyboard(user_id: int, client: Client) -> InlineKeyboardMarkup:
        buttons = await ButtonManager.get_translated_buttons(user_id, "main")
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(buttons[0], url=f"https://t.me/{client.me.username}?startgroup=true")],
            [InlineKeyboardButton(buttons[1], callback_data="commands"),
             InlineKeyboardButton(buttons[2], callback_data="help")],
            [InlineKeyboardButton(buttons[3], callback_data="settings"),
             InlineKeyboardButton(buttons[4], callback_data="support")]
        ])

    @staticmethod
    async def handle_start(client: Client, message: Message):
        try:
            await user_db.check_and_add_user(message.from_user.id)
            if message.from_user.username:
                await user_db.check_and_add_username(message.from_user.id, message.from_user.username)

            user_id = message.from_user.id
            user_lang = await get_user_language(user_id)
            
            welcome_text = MessageTemplates.WELCOME.format(
                user_mention=message.from_user.mention
            )
            
            translated_welcome = await translate_text_async(welcome_text, user_lang)
            translated_tip = await translate_text_async(MessageTemplates.TIP, user_lang)
            keyboard = await StartHandler.create_keyboard(user_id, client)

            await message.reply_text(
                translated_welcome,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
            
            await message.reply_text(translated_tip)
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await message.reply_text("An error occurred. Please try again.")

    @staticmethod
    async def handle_start_inline(client: Client, callback: CallbackQuery):
        try:
            user_id = callback.from_user.id
            user_lang = await get_user_language(user_id)
            
            welcome_text = MessageTemplates.WELCOME.format(
                user_mention=callback.from_user.mention
            )
            
            translated_welcome = await translate_text_async(welcome_text, user_lang)
            keyboard = await StartHandler.create_keyboard(user_id, client)

            await callback.message.edit_text(
                translated_welcome,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Error in start_inline: {e}")
            await callback.answer("An error occurred. Please try again.", show_alert=True)

async def start(client: Client, message: Message):
    await StartHandler.handle_start(client, message)

async def start_inline(client: Client, callback: CallbackQuery):
    await StartHandler.handle_start_inline(client, callback)

