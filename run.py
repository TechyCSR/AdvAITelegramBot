

import pyrogram 
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from


from modules.user.start import start , start_inline
from modules.user.help import help ,help_inline
from modules.user.commands import command_inline
from modules.user.settings import settings_inline,settings_language_callback,change_voice_setting 
from modules.user.settings import settings_voice_inlines
from modules.user.assistant import settings_assistant_callback,change_mode_setting
from modules.user.lang_settings import settings_langs_callback,change_language_setting
from modules.user.user_support import settings_support_callback,support_admins_callback
from modules.user.dev_support import support_developers_callback
from modules.speech import  text_to_voice,voice_to_text


from modules.maintenance import settings_others_callback
from modules.group.group_settings import leave_group,invite_command
from modules.feedback_nd_rating import rate_command,handle_rate_callback
from modules.group.group_info import info_command

import os
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
    elif callback_query.data == "settings_language":
        await settings_language_callback(client, callback_query)
    elif callback_query.data in ["settings_voice", "settings_text"]:
        await change_voice_setting(client, callback_query)
    elif callback_query.data == "settings_back":
        await settings_voice_inlines(client, callback_query)
    elif callback_query.data == "settings_lans":
        await settings_langs_callback(client, callback_query)
    elif callback_query.data in ["language_hi", "language_en", "language_zh", "language_ar", "language_fr", "language_ru"]:
        await change_language_setting(client, callback_query)
    elif callback_query.data=="settings_assistant":
        await settings_assistant_callback(client, callback_query)
    elif callback_query.data in ["mode_chatbot", "mode_coder", "mode_professional", "mode_teacher", "mode_therapist", "mode_assistant", "mode_gamer", "mode_translator"]:
        await change_mode_setting(client, callback_query)
    elif callback_query.data=="settings_others" or callback_query.data=="support_donate":
        await settings_others_callback(client, callback_query)
    elif callback_query.data=="support":
         await settings_support_callback(client, callback_query)
    elif callback_query.data=="support_admins":
        await support_admins_callback(client, callback_query)
    elif callback_query.data=="support_developers":
        await support_developers_callback(client, callback_query)

    elif callback_query.data in ["rate_1", "rate_2", "rate_3", "rate_4", "rate_5"]:
        await handle_rate_callback(client, callback_query)
        
    else:
        pass

@advAiBot.on_message(filters.voice)
async def voice(bot, message):
    await voice_to_text.handle_voice_message(bot, message)

# @advAiBot.on_message(filters.text & filters.private & filters.chat()
# async def handle_text_message(client, message):
#     await text_to_voice.handle_text_message(client, message)


@advAiBot.on_message(filters.command("gleave") & filters.private & filters.chat(config.ADMINS))
async def leave_group_command(bot, update):
    await leave_group(bot, update)

@advAiBot.on_message(filters.command("rate") & filters.private)
async def rate_commands(bot, update):
    await rate_command(bot, update)

@advAiBot.on_message(filters.command("invite") &  filters.private & filters.chat(config.ADMINS))
async def invite_commands(bot, update):
    await invite_command(bot, update)

@advAiBot.on_message(filters.command("uinfo") )
async def info_commands(bot, update):
    if update.from_
    await info_command(bot, update)






advAiBot.run()


