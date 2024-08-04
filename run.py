

import pyrogram 
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from modules.user.start import start

from config import config

advAiBot = pyrogram.Client("my_account", api_id=config.API_ID, api_hash=config.API_HASH, bot_token=config.BOT_TOKEN)

@advAiBot.on_message(filters.command("start"),filters.private())
async def start_command(client, message):
    await start(client, message)

advAiBot.run()

