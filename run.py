import os
import config
import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup ,InputMediaPhoto
from modules.user.start import start , start_inline
from modules.user.help import help ,help_inline
from modules.user.commands import command_inline
from modules.user.settings import settings_inline
from modules.user.voice_settings import settings_voice_callback, change_voice_setting
from modules.user.ai_mode_settings import settings_assistant_callback, change_ai_mode
from modules.user.lang_settings import settings_langs_callback, change_language_setting
from modules.user.user_support import settings_support_callback,support_admins_callback
from modules.user.dev_support import support_developers_callback
from modules.speech import  text_to_voice,voice_to_text
from modules.image.img_to_text import extract_text_res
from modules.maintenance import settings_others_callback
from modules.group.group_settings import leave_group,invite_command
from modules.feedback_nd_rating import rate_command,handle_rate_callback
from modules.group.group_info import info_command
from modules.modles.ai_res import aires, new_chat
from modules.image.image_generation import generate_command
from modules.chatlogs import channel_log, user_log
from modules.user.global_setting import global_setting_command
import database.user_db as user_db
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

advAiBot = pyrogram.Client("AdvChatGptBotV2", bot_token=config.BOT_TOKEN, api_id=config.API_KEY, api_hash=config.API_HASH)

@advAiBot.on_message(filters.command("start"))
async def start_command(bot, update):
    await start(bot, update)
    await channel_log(bot, update, "/start")

@advAiBot.on_message(filters.command("help"))
async def help_command(bot, update):
    await help(bot, update)
    await channel_log(bot, update, "/help")

def is_chat_text_filter():
    async def funcc(_, __, update):
        if bool(update.text):
            return not update.text.startswith("/")
        return False
    return filters.create(funcc)

@advAiBot.on_message(is_chat_text_filter() & filters.text & filters.private)
async def handle_message(client, message):
    await aires(client, message)

@advAiBot.on_callback_query()
async def callback_query(client, callback_query):
    try:
        if callback_query.data == "help":
            await help_inline(client, callback_query)
        elif callback_query.data == "back":
            await start_inline(client, callback_query)
        elif callback_query.data == "commands":
            await command_inline(client, callback_query)
        elif callback_query.data == "settings":
            await settings_inline(client, callback_query)
        elif callback_query.data == "settings_v":
            await settings_voice_callback(client, callback_query)
        elif callback_query.data in ["settings_voice", "settings_text"]:
            await change_voice_setting(client, callback_query)
        elif callback_query.data == "settings_back":
            await settings_inline(client, callback_query)
        elif callback_query.data == "settings_lans":
            await settings_langs_callback(client, callback_query)
        elif callback_query.data in ["language_hi", "language_en", "language_zh", "language_ar", "language_fr", "language_ru"]:
            await change_language_setting(client, callback_query)
        elif callback_query.data == "settings_assistant":
            await settings_assistant_callback(client, callback_query)
        elif callback_query.data in ["mode_chatbot", "mode_coder", "mode_professional", "mode_teacher", "mode_therapist", "mode_assistant", "mode_gamer", "mode_translator"]:
            await change_ai_mode(client, callback_query)
        elif callback_query.data == "settings_others" or callback_query.data == "support_donate":
            await settings_others_callback(client, callback_query)
        elif callback_query.data == "support":
            await settings_support_callback(client, callback_query)
        elif callback_query.data == "support_admins":
            await support_admins_callback(client, callback_query)
        elif callback_query.data == "support_developers":
            await support_developers_callback(client, callback_query)
        elif callback_query.data in ["rate_1", "rate_2", "rate_3", "rate_4", "rate_5"]:
            await handle_rate_callback(client, callback_query)
    except Exception as e:
        logger.error(f"Error in callback_query: {e}")
        await callback_query.answer("An error occurred. Please try again.", show_alert=True)

@advAiBot.on_message(filters.voice)
async def voice(bot, message):
    await voice_to_text.handle_voice_message(bot, message)

@advAiBot.on_message(filters.command("gleave"))
async def leave_group_command(bot, update):
    if update.from_user.id in config.ADMINS:
        await leave_group(bot, update)
        await channel_log(bot, update, "/gleave")
    else:
        await update.reply_text("You are not allowed to use this command.")

@advAiBot.on_message(filters.command("rate") & filters.private)
async def rate_commands(bot, update):
    await rate_command(bot, update)

@advAiBot.on_message(filters.command("invite"))
async def invite_commands(bot, update):
    if update.from_user.id in config.ADMINS:
        await invite_command(bot, update)
        await channel_log(bot, update, "/invite")
    else:
        await update.reply_text("You are not allowed to use this command.")

@advAiBot.on_message(filters.command("uinfo"))
async def info_commands(bot, update):
    if update.from_user.id in config.ADMINS:
        await info_command(bot, update)
        await channel_log(bot, update, "/uinfo")
    else:
        await update.reply_text("You are not allowed to use this command.")

@advAiBot.on_message(filters.text & filters.command(["ai","ask","say"]) & filters.group)
async def handle_message(bot, update):
    if len(update.text) > 3:
        update.text = update.text[3:]
    else:
        await update.reply_text("Please provide valid text")
        return
    await user_log(bot, update, update.text)
    await aires(bot, update)

@advAiBot.on_message(filters.command(["newchat", "reset","new_conversation","clear_chat","new"]))
async def handle_new_chat(client, message):
    await new_chat(client, message)
    await channel_log(client, message, "/newchat")

@advAiBot.on_message(filters.command(["generate", "gen", "image","img"]))
async def handle_generate(client, message):
    try:
        # Get the command used
        command = message.command[0]
        
        # Extract prompt from message
        if len(message.command) < 2:
            await message.reply_text("Please provide a prompt to generate images.\nExample: /generate a beautiful sunset")
            return
            
        prompt = " ".join(message.command[1:])
        
        if not prompt.strip():
            await message.reply_text("Please provide a prompt to generate images.\nExample: /generate a beautiful sunset")
            return
        
        # Call generate_command with await
        await generate_command(client, message, prompt)
        
    except Exception as e:
        logger.error(f"Error in handle_generate: {e}")
        await message.reply_text("Sorry, there was an error processing your request. Please make sure to provide a valid prompt.")

@advAiBot.on_message(filters.photo)
async def handle_image(bot, update):
    if update.from_user.id == bot.me.id:
        return
    if update.chat.type == "private":
        await extract_text_res(bot, update)
    else:
        if update.caption:
            if "ai" in update.caption.lower() or "ask" in update.caption.lower():
                await extract_text_res(bot, update)
        else:
            return

@advAiBot.on_message(filters.command("settings"))
async def settings_command(bot, update):
    await global_setting_command(bot, update)
    await channel_log(bot, update, "/settings")

@advAiBot.on_message(filters.command(["announce","broadcast","acc"]))
async def announce_command(bot, update):
    if update.from_user.id in config.ADMINS:
        try:
            text = update.text.split(" ", 1)[1]
            await user_db.get_usernames_message(bot, update, text)
        except IndexError:
            await update.reply_text("Please provide a message to send.")
            return
    else:
        await update.reply_text("You are not allowed to use this command.")

if __name__ == "__main__":
    logger.info("Starting bot...")
    advAiBot.run()
