

import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import CallbackQuery
from pyrogram.types import InlineQuery

from datetime import datetime

from config import logs # Import the logs channel ID



async def logging(client, message,command):
    client.send_message(
        chat_id=logs,
        text="**User:** `{}'\n**Mention**`{}`\n**Command:** `{}`\nTime: `{}`".format(message.from_user.id,message.from_user.mention,command,datetime.now())
    )

