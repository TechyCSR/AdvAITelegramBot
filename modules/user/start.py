

import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery

from modules.chatlogs import channel_log

from database import user_db


global welcome_text
global LOGO

welcome_text = """
**Hey {user_mention}!** 

Welcome to the **Advanced AI ChatBot**! 🌟

Explore the amazing features we have for you:

- **AI ChatBot (GPT-4o and GPT-4o-mini)**
- **AI Speech to Text & Vice Versa**
- **AI Generative Images (DALL-E 3 Model)**
- **AI Image to Text (Google Lens)**


*Get started by adding me to your group!**  🚀
"""

LOGO ="https://graph.org/file/5d3d030e668795f769e20.mp4"
# LOGO="./assets/logos/logo3.gif"


button_list = [
    "➕ Add Me To Your Group ➕",
    "💬 Commands",
    "❓ Help",
    "⚙️ Settings",
    "🛠️ Support",
    "ℹ️ More Info"
]




async def start(client, message):
    global LOGO
    welcome_tex = welcome_text.format(user_mention = message.from_user.mention)



    # for i in button_list:
    #     if default_lang !="en":
    #         button_list[button_list.index(i)] = translate_to_lang(i, default_lang )
    # Create the inline keyboard buttons

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(button_list[0], url=f"https://t.me/{client.me.username}?startgroup=true")],
        [InlineKeyboardButton( button_list[1], callback_data="commands"),
         InlineKeyboardButton(button_list[2], callback_data="help")],
        [InlineKeyboardButton(button_list[3], callback_data="settings"),
         InlineKeyboardButton(button_list[4], callback_data="support")],
        [InlineKeyboardButton(button_list[5], callback_data="info")]
    ])
    # Send the welcome message with the GIF and the keyboard
    await client.send_animation(
        chat_id=message.chat.id,
        animation=LOGO,
        caption=welcome_tex,
        reply_markup=keyboard
    
    )



async def start_inline(bot, callback):
    global LOGO
    mention = callback.from_user.mention
    welcome_tex = welcome_text.format(user_mention=mention)

    # for i in button_list:
    #     if default_lang !="en":
    #         button_list[button_list.index(i)] = translate_to_lang(i, default_lang )
    # Create the inline keyboard buttons

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(button_list[0], url=f"https://t.me/{bot.me.username}?startgroup=true")],
        [InlineKeyboardButton(button_list[1], callback_data="commands"),
         InlineKeyboardButton(button_list[2], callback_data="help")],
        [InlineKeyboardButton(button_list[3], callback_data="settings"),
         InlineKeyboardButton(button_list[4], callback_data="support")],
        [InlineKeyboardButton(button_list[5], callback_data="info")]
    ])
    # Send the welcome message with the GIF and the keyboard
    await bot.edit_message_caption(
        chat_id=callback.message.chat.id,
        message_id=callback.message.id,
        caption=welcome_tex,
        reply_markup=keyboard
    )

