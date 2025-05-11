import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from pyrogram.types import CallbackQuery
from modules.lang import translate_to_lang
from modules.chatlogs import channel_log
import database.user_db as user_db

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

LOGO = "https://telegra.ph/file/2c1010dc1030c8898448f.mp4"

async def start(client, message):
    await user_db.check_and_add_user(message.from_user.id)
    if message.from_user.username:
        await user_db.check_and_add_username(message.from_user.id, message.from_user.username)

    # Translate welcome text and button texts
    user_id = message.from_user.id
    translated_welcome = translate_to_lang(welcome_text, user_id)
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

    # Send the welcome message with the GIF and the keyboard
    await client.send_animation(
        chat_id=message.chat.id,
        animation=LOGO,
        caption=translated_welcome,
        reply_markup=keyboard
    )
    await message.reply_text(translated_tip)

async def start_inline(bot, callback):
    user_id = callback.from_user.id
    mention = callback.from_user.mention

    # Translate welcome text and button texts
    translated_welcome = translate_to_lang(welcome_text, user_id)
    translated_buttons = [translate_to_lang(btn, user_id) for btn in button_list]

    # Create the inline keyboard buttons with translated text
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(translated_buttons[0], url=f"https://t.me/{bot.me.username}?startgroup=true")],
        [InlineKeyboardButton(translated_buttons[1], callback_data="commands"),
         InlineKeyboardButton(translated_buttons[2], callback_data="help")],
        [InlineKeyboardButton(translated_buttons[3], callback_data="settings"),
         InlineKeyboardButton(translated_buttons[4], callback_data="support")]
    ])

    # Send the welcome message with the GIF and the keyboard
    await bot.edit_message_caption(
        chat_id=callback.message.chat.id,
        message_id=callback.message.id,
        caption=translated_welcome,
        reply_markup=keyboard
    )

