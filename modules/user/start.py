import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from pyrogram.types import CallbackQuery
from modules.lang import get_ui_message, get_user_language
from modules.chatlogs import channel_log
import database.user_db as user_db

# Define button texts in English (will be translated at runtime)
button_list = [
    "add_to_group_button",
    "commands_button",
    "help_button",
    "settings_button",
    "support_button"
]

# Add these to the English language file via the message key system
welcome_text_key = "welcome_message"
tip_text_key = "welcome_tip"

LOGO = "https://telegra.ph/file/2c1010dc1030c8898448f.mp4"

async def start(client, message):
    await user_db.check_and_add_user(message.from_user.id)
    if message.from_user.username:
        await user_db.check_and_add_username(message.from_user.id, message.from_user.username)

    # Get user's language preference
    user_id = message.from_user.id
    
    # Get translated welcome message with user mention
    welcome_text = get_ui_message(welcome_text_key, user_id)
    welcome_text = welcome_text.replace("{user_mention}", message.from_user.mention)
    
    # Get translated button texts
    translated_buttons = [get_ui_message(btn, user_id) for btn in button_list]
    
    # Get translated tip text
    tip_text = get_ui_message(tip_text_key, user_id)

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
        caption=welcome_text,
        reply_markup=keyboard
    )
    await message.reply_text(tip_text)

async def start_inline(bot, callback):
    user_id = callback.from_user.id
    
    # Get translated welcome message with user mention
    welcome_text = get_ui_message(welcome_text_key, user_id)
    welcome_text = welcome_text.replace("{user_mention}", callback.from_user.mention)
    
    # Get translated button texts
    translated_buttons = [get_ui_message(btn, user_id) for btn in button_list]

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
        caption=welcome_text,
        reply_markup=keyboard
    )

