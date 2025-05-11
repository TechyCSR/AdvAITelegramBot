import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from pyrogram.types import CallbackQuery
from modules.lang import translate_to_lang, translate_text_async, get_user_language, get_language_display_name
from modules.chatlogs import channel_log
import database.user_db as user_db
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Define button texts
button_list = [
    "Add to Group",
    "Commands",
    "Help",
    "Settings",
    "Support"
]

welcome_text = """
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

tip_text = "💡 Tip: You can use /help to see all available commands!"

# Use a more reliable animation URL
WELCOME_ANIMATION = "https://telegra.ph/file/8c1c3a4f4c8d4f5d5e5e5.mp4"

async def start(client, message):
    try:
        await user_db.check_and_add_user(message.from_user.id)
        if message.from_user.username:
            await user_db.check_and_add_username(message.from_user.id, message.from_user.username)

        user_id = message.from_user.id
        user_lang = get_user_language(user_id)
        
        # Format welcome text with user mention
        formatted_welcome = welcome_text.format(
            user_mention=message.from_user.mention
        )
        
        # Translate welcome text and button texts
        translated_welcome = await translate_text_async(formatted_welcome, user_lang)
        translated_buttons = [translate_to_lang(btn, user_id) for btn in button_list]
        translated_tip = translate_to_lang(tip_text, user_id)

        # Create the inline keyboard buttons with translated text
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(translated_buttons[0], url=f"https://t.me/{client.me.username}?startgroup=true")],
            [InlineKeyboardButton(translated_buttons[1], callback_data="commands"),
             InlineKeyboardButton(translated_buttons[2], callback_data="help")],
            [InlineKeyboardButton(translated_buttons[3], callback_data="settings"),
             InlineKeyboardButton(translated_buttons[4], callback_data="support")]
        ])

        await message.reply_text(
            translated_welcome,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
        await message.reply_text(translated_tip)
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.reply_text("An error occurred. Please try again.")

async def start_inline(client, callback):
    try:
        user_id = callback.from_user.id
        user_lang = get_user_language(user_id)
        
        # Format welcome text with user mention
        formatted_welcome = welcome_text.format(
            user_mention=callback.from_user.mention
        )
        
        # Translate welcome text and button texts
        translated_welcome = await translate_text_async(formatted_welcome, user_lang)
        translated_buttons = [translate_to_lang(btn, user_id) for btn in button_list]

        # Create the inline keyboard buttons with translated text
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(translated_buttons[0], url=f"https://t.me/{client.me.username}?startgroup=true")],
            [InlineKeyboardButton(translated_buttons[1], callback_data="commands"),
             InlineKeyboardButton(translated_buttons[2], callback_data="help")],
            [InlineKeyboardButton(translated_buttons[3], callback_data="settings"),
             InlineKeyboardButton(translated_buttons[4], callback_data="support")]
        ])

        await callback.message.edit_text(
            translated_welcome,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Error in start_inline: {e}")
        await callback.answer("An error occurred. Please try again.", show_alert=True)

