import pyrogram
from pyrogram import Client, filters
from pyrogram.types import Message, InlineQuery, CallbackQuery
from config import API_ID, API_HASH, BOT_TOKEN
from modules.user.settings import settings_inline, settings_language_callback, change_language
from modules.user.voice_settings import settings_voice_callback, change_voice_setting
from modules.user.ai_mode_settings import settings_assistant_callback, change_ai_mode
from modules.user.help import help_inline
from modules.user.commands import command_inline
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot
app = Client(
    "AdvAITelegramBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Command handlers
@app.on_message(filters.command("start"))
async def start_command(client, message):
    try:
        from modules.user.start import start_command
        await start_command(client, message)
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.reply("An error occurred. Please try again.")

@app.on_message(filters.command("help"))
async def help_command(client, message):
    try:
        await help_inline(client, message)
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await message.reply("An error occurred. Please try again.")

@app.on_message(filters.command("settings"))
async def settings_command(client, message):
    try:
        await settings_inline(client, message)
    except Exception as e:
        logger.error(f"Error in settings command: {e}")
        await message.reply("An error occurred. Please try again.")

@app.on_message(filters.command("commands"))
async def commands_command(client, message):
    try:
        await command_inline(client, message)
    except Exception as e:
        logger.error(f"Error in commands command: {e}")
        await message.reply("An error occurred. Please try again.")

# Callback handlers
@app.on_callback_query(filters.regex("^settings_lans$"))
async def settings_language_handler(client, callback):
    try:
        await settings_language_callback(client, callback)
    except Exception as e:
        logger.error(f"Error in settings language callback: {e}")
        await callback.answer("An error occurred. Please try again.", show_alert=True)

@app.on_callback_query(filters.regex("^language_"))
async def language_change_handler(client, callback):
    try:
        await change_language(client, callback)
    except Exception as e:
        logger.error(f"Error in language change callback: {e}")
        await callback.answer("An error occurred. Please try again.", show_alert=True)

@app.on_callback_query(filters.regex("^settings_v$"))
async def settings_voice_handler(client, callback):
    try:
        await settings_voice_callback(client, callback)
    except Exception as e:
        logger.error(f"Error in settings voice callback: {e}")
        await callback.answer("An error occurred. Please try again.", show_alert=True)

@app.on_callback_query(filters.regex("^settings_voice$|^settings_text$"))
async def voice_change_handler(client, callback):
    try:
        await change_voice_setting(client, callback)
    except Exception as e:
        logger.error(f"Error in voice change callback: {e}")
        await callback.answer("An error occurred. Please try again.", show_alert=True)

@app.on_callback_query(filters.regex("^settings_assistant$"))
async def settings_assistant_handler(client, callback):
    try:
        await settings_assistant_callback(client, callback)
    except Exception as e:
        logger.error(f"Error in settings assistant callback: {e}")
        await callback.answer("An error occurred. Please try again.", show_alert=True)

@app.on_callback_query(filters.regex("^mode_"))
async def ai_mode_change_handler(client, callback):
    try:
        await change_ai_mode(client, callback)
    except Exception as e:
        logger.error(f"Error in AI mode change callback: {e}")
        await callback.answer("An error occurred. Please try again.", show_alert=True)

@app.on_callback_query(filters.regex("^settings_back$"))
async def settings_back_handler(client, callback):
    try:
        await settings_inline(client, callback)
    except Exception as e:
        logger.error(f"Error in settings back callback: {e}")
        await callback.answer("An error occurred. Please try again.", show_alert=True)

@app.on_callback_query(filters.regex("^back$"))
async def back_handler(client, callback):
    try:
        from modules.user.start import start_command
        await start_command(client, callback.message)
    except Exception as e:
        logger.error(f"Error in back callback: {e}")
        await callback.answer("An error occurred. Please try again.", show_alert=True)

# Error handler
@app.on_error()
async def error_handler(client, error):
    logger.error(f"Global error handler caught: {error}")
    return True

# Start the bot
if __name__ == "__main__":
    logger.info("Starting bot...")
    app.run() 