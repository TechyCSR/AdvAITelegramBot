

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

👋 **Hey {first_name}!** 

Welcome to the **Telegram Advanced AI ChatBot**! 🌟

Explore the amazing features we have for you:
- **AI ChatBot (GPT-4)**
- **AI Speech to Text & Vice Versa**
- **AI Generative Images (DALL-E Model)**
- **AI Image to Text (Google Lens)**

Let's get started and experience the future of AI-powered conversations! 🚀


"""

LOGO ="https://graph.org/file/5d3d030e668795f769e20.mp4"




async def start(client, message):
    global welcome_text
    global LOGO

    fstname = message.from_user.first_name
    welcome_text = welcome_text.format(first_name=fstname)

    # Create the inline keyboard buttons
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Advance AI Chatbot", callback_data="alert"),],
        [InlineKeyboardButton("", callback_data="feature_1"),
         InlineKeyboardButton("Feature 2", callback_data="feature_2")],
        [InlineKeyboardButton("Feature 3", callback_data="feature_3"),
         InlineKeyboardButton("Feature 4", callback_data="feature_4")],
        [InlineKeyboardButton("More Info", url="https://example.com")]
    ])

    # Send the welcome message with the GIF and the keyboard
    await client.send_animation(
        chat_id=message.chat.id,
        animation=LOGO,
        caption=welcome_text,
        reply_markup=keyboard
    )
    await channel_log(client, message, "/start")


