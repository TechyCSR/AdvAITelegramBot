

import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from pyrogram.types import CallbackQuery




from modules.lang import translate_to_lang, default_lang

from modules.chatlogs import channel_log



settings_text = """
**Settings Menu**

**User** = {message.from_user.mention}
**Language** = {default_lang}

**User_status** = {user_status}

"""


async def settings_inline(client, callback):
    global settings_text
    
    # settings_text = settings_text.format(message=callback, default_lang=default_lang, user_status=callback.from_user.status)
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🌐 Language", callback_data="settings_language"),
                InlineKeyboardButton("🎙️ Voice", callback_data="settings_voice")
            ],
            [
                InlineKeyboardButton("🤖 Assistant", callback_data="settings_assistant"),
                InlineKeyboardButton("🔧 Others", callback_data="settings_others")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="back")
            ]
        ]
    )
    await callback.message.edit(
        text=settings_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    await channel_log(client, callback, "/settings")

