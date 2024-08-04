

import pyrogram 
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from modules.user.start import start , start_inline
from modules.user.help import help ,help_inline
from modules.user.commands import command_inline
from modules.user.settings import settings_inline


import config
from datetime import datetime

advAiBot = pyrogram.Client("Adance AI ChatBot", bot_token=config.BOT_TOKEN, api_id=config.API_KEY, api_hash=config.API_HASH)

@advAiBot.on_message(filters.command("start"))
async def start_command(bot, update):
    await start(bot, update)



@advAiBot.on_message(filters.command("help"))
async def help_command(bot, update):
    await help(bot, update)

@advAiBot.on_callback_query()
async def callback_query(client, callback_query):
    if callback_query.data == "help":
        await help_inline(client, callback_query)
    elif callback_query.data == "back":
        await start_inline(client, callback_query)
    elif callback_query.data == "commands":
        await command_inline(client, callback_query)
    elif callback_query.data == "settings":
        await settings_inline(client, callback_query)
    else:
        pass

advAiBot.run()


