

import pyrogram 
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from modules.user.start import start
import config

advAiBot = pyrogram.Client("Adance AI ChatBot", bot_token=config.BOT_TOKEN, api_id=config.API_KEY, api_hash=config.API_HASH)

@advAiBot.on_message(filters.command("start"),filters.private)
async def start_command(client, message):
    await start(client, message)

advAiBot.run()

