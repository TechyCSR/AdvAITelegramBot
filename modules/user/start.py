

import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import CallbackQuery
from pyrogram.types import InlineQuery

from modules.lang import translate_to_lang, default_lang
from modules.chatlogs import channel_log

global welcome_text
global LOGO

welcome_text = """
**Hey {user_mention}!** 

Welcome to the **Telegram Advanced AI ChatBot**! 🌟

Explore the amazing features we have for you:
- **AI ChatBot (GPT-4)**
- **AI Speech to Text & Vice Versa**
- **AI Generative Images (DALL-E Model)**
- **AI Image to Text (Google Lens)**

Let's get started and experience the future of AI-powered conversations! 🚀


"""

LOGO ="https://graph.org/file/5d3d030e668795f769e20.mp4"


button_list = [
    "➕ Add Me To Your Group ➕",
    "💬 Commands",
    "❓ Help",
    "⚙️ Settings",
    "🛠️ Support",
    "ℹ️ More Info"
]






async def start(client, message):
    global welcome_text
    global LOGO
    mention = message.from_user.mention
    welcome_text = welcome_text.format(user_mention=mention)

    # for i in button_list:
    #     if default_lang !="en":
    #         button_list[button_list.index(i)] = translate_to_lang(i, default_lang )
    # Create the inline keyboard buttons

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(button_list[0], callback_data="alert")],
        [InlineKeyboardButton( button_list[1], callback_data="feature_1"),
         InlineKeyboardButton(button_list[2], callback_data="feature_2")],
        [InlineKeyboardButton(button_list[3], callback_data="feature_3"),
         InlineKeyboardButton(button_list[4], callback_data="feature_4")],
        [InlineKeyboardButton(button_list[5], url="https://example.com")]
    ])
    # Send the welcome message with the GIF and the keyboard
    await client.send_animation(
        chat_id=message.chat.id,
        animation=LOGO,
        caption=welcome_text,
        reply_markup=keyboard
        
    )
    await channel_log(client, message, "/start")


