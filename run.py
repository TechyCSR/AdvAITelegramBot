import os
import config
import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from pyrogram.enums import ChatAction
from modules.user.start import start, start_inline
from modules.user.help import help, help_inline
from modules.user.commands import command_inline
from modules.user.settings import settings_inline, settings_language_callback, change_voice_setting 
from modules.user.settings import settings_voice_inlines
from modules.user.assistant import settings_assistant_callback, change_mode_setting
from modules.user.lang_settings import settings_langs_callback, change_language_setting
from modules.user.user_support import settings_support_callback, support_admins_callback
from modules.user.dev_support import support_developers_callback
from modules.speech import text_to_voice, voice_to_text
from modules.image.img_to_text import extract_text_res, handle_show_text_callback, handle_followup_callback
from modules.maintenance import settings_others_callback
from modules.group.group_settings import leave_group, invite_command
from modules.feedback_nd_rating import rate_command, handle_rate_callback
from modules.group.group_info import info_command
from modules.models.ai_res import aires, new_chat
from modules.image.image_generation import generate_command, handle_image_feedback, start_cleanup_scheduler, handle_generate_command
from modules.image.inline_image_generation import handle_inline_query, cleanup_ongoing_generations
from modules.chatlogs import channel_log, user_log, error_log
from modules.user.global_setting import global_setting_command
from modules.speech.voice_to_text import handle_voice_toggle
import modules.models.user_db as user_db
import asyncio
import logging
import datetime
from logging.handlers import RotatingFileHandler
import json
import time
from modules.models.image_service import ImageService


# Create directories if they don't exist
if not os.path.exists("sessions"):
    os.makedirs("sessions")
if not os.path.exists("logs"):
    os.makedirs("logs")

# Configure logging with a single main log file
MAIN_LOG_FILE = os.path.join("logs", "bot_main.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(MAIN_LOG_FILE, maxBytes=10*1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Initialize the Pyrogram client with improved session handling
advAiBot = pyrogram.Client(
    "AdvChatGptBotV2", 
    bot_token=config.BOT_TOKEN, 
    api_id=config.API_KEY, 
    api_hash=config.API_HASH,
    workdir="sessions"
)

# Track bot statistics
bot_stats = {
    "messages_processed": 0,
    "images_generated": 0,
    "voice_messages_processed": 0,
    "active_users": set()
}

# Get the cleanup scheduler function to run later
cleanup_scheduler = start_cleanup_scheduler()

@advAiBot.on_message(filters.command("start"))
async def start_command(bot, update):
    # Start the cleanup scheduler on first command
    global cleanup_scheduler_task, ongoing_generations_cleanup_task
    if not 'cleanup_scheduler_task' in globals() or cleanup_scheduler_task is None:
        cleanup_scheduler_task = asyncio.create_task(cleanup_scheduler())
        logger.info("Started image generation cleanup scheduler task")
        
    if not 'ongoing_generations_cleanup_task' in globals() or ongoing_generations_cleanup_task is None:
        ongoing_generations_cleanup_task = asyncio.create_task(cleanup_ongoing_generations())
        logger.info("Started inline generations cleanup scheduler task")
        
    bot_stats["active_users"].add(update.from_user.id)
    logger.info(f"User {update.from_user.id} started the bot")
    await start(bot, update)
    await channel_log(bot, update, "/start")

@advAiBot.on_message(filters.command("help"))
async def help_command(bot, update):
    logger.info(f"User {update.from_user.id} requested help")
    await help(bot, update)
    await channel_log(bot, update, "/help")


def is_chat_text_filter():
    async def funcc(_, __, update):
        if bool(update.text):
            return not update.text.startswith("/")
        return False
    return filters.create(funcc)

# Add a custom filter for non-command messages
def is_not_command_filter():
    async def func(_, __, message):
        if message.text:
            return not message.text.startswith('/')
        return True  # Non-text messages are not commands
    return filters.create(func)

# Add a custom filter for replies to bot messages
def is_reply_to_bot_filter():
    async def func(_, __, message):
        if message.reply_to_message and message.reply_to_message.from_user:
            # Check if the message is replying to the bot
            return message.reply_to_message.from_user.id == advAiBot.me.id
        return False
    return filters.create(func)

@advAiBot.on_message(is_chat_text_filter() & filters.text & filters.private)
async def handle_message(client, message):
    bot_stats["messages_processed"] += 1
    bot_stats["active_users"].add(message.from_user.id)
    logger.info(f"Processing message from user {message.from_user.id}")
    await aires(client, message)

@advAiBot.on_inline_query()
async def inline_query_handler(client, inline_query):
    """Handler for inline queries, primarily for image generation"""
    bot_stats["active_users"].add(inline_query.from_user.id)
    logger.info(f"Processing inline query from user {inline_query.from_user.id}: '{inline_query.query}'")
    
    # Handle image generation inline
    await handle_inline_query(client, inline_query)

@advAiBot.on_callback_query()
async def callback_query(client, callback_query):
    # Standard menu callbacks
    if callback_query.data == "help":
        await help_inline(client, callback_query)
    elif callback_query.data == "back":
        await start_inline(client, callback_query)
    elif callback_query.data == "commands":
        await command_inline(client, callback_query)
    elif callback_query.data == "settings":
        await settings_inline(client, callback_query)
    elif callback_query.data == "settings_v":
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
    
    # Onboarding tour handlers
    elif callback_query.data.startswith("onboarding_"):
        from modules.user.start import handle_onboarding
        await handle_onboarding(client, callback_query)
    
    # Image feedback and style selection handlers
    elif callback_query.data.startswith("img_feedback_"):
        await handle_image_feedback(client, callback_query)
    elif callback_query.data.startswith("img_regenerate_"):
        await handle_image_feedback(client, callback_query)
    elif callback_query.data.startswith("img_style_"):
        await handle_image_feedback(client, callback_query)
    
    # Voice setting handlers
    elif callback_query.data.startswith("toggle_voice_"):
        await handle_voice_toggle(client, callback_query)
    
    # Image text handlers
    elif callback_query.data.startswith("show_text_"):
        await handle_show_text_callback(client, callback_query)
    elif callback_query.data.startswith("followup_"):
        await handle_followup_callback(client, callback_query)
    elif callback_query.data.startswith("back_to_image_"):
        # Return to previous message with options
        user_id = int(callback_query.data.split("_")[3])
        await callback_query.message.edit_text(
            "**Need anything else with this image?**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Show Extracted Text", callback_data=f"show_text_{user_id}")],
                [InlineKeyboardButton("❓ Ask Follow-up", callback_data=f"followup_{user_id}")]
            ])
        )


@advAiBot.on_message(filters.voice)
async def voice(bot, message):
    bot_stats["voice_messages_processed"] += 1
    bot_stats["active_users"].add(message.from_user.id)
    await voice_to_text.handle_voice_message(bot, message)

# Add a new handler for replies to bot messages in groups
@advAiBot.on_message(is_reply_to_bot_filter() & filters.group & filters.text & is_not_command_filter())
async def handle_reply_to_bot(bot, message):
    bot_stats["messages_processed"] += 1
    bot_stats["active_users"].add(message.from_user.id)
    
    logger.info(f"Processing reply to bot in group {message.chat.id} from user {message.from_user.id}")
    
    # Show typing indicator
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    
    # Log the interaction
    await user_log(bot, message, message.text)
    
    # Process the query using the AI response function
    await aires(bot, message)

@advAiBot.on_message(filters.command("gleave"))
async def leave_group_command(bot, update):
    if update.from_user.id in config.ADMINS:
        logger.info(f"Admin {update.from_user.id} leaving group {update.chat.id}")
        await leave_group(bot, update)
        await channel_log(bot, update, "/gleave", f"Admin leaving group {update.chat.id if update.chat else 'unknown'}")
    else:
        logger.warning(f"Unauthorized user {update.from_user.id} attempted to use gleave command")
        await update.reply_text("⛔ You are not authorized to use this command.")
        await channel_log(bot, update, "/gleave", f"Unauthorized access attempt", level="WARNING")

@advAiBot.on_message(filters.command("rate") & filters.private)
async def rate_commands(bot, update):
    await rate_command(bot, update)

@advAiBot.on_message(filters.command("invite"))
async def invite_commands(bot, update):
    if update.from_user.id in config.ADMINS:
        logger.info(f"Admin {update.from_user.id} used invite command")
        await invite_command(bot, update)
        await channel_log(bot, update, "/invite", "Admin used invite command")
    else:
        logger.warning(f"Unauthorized user {update.from_user.id} attempted to use invite command")
        await update.reply_text("⛔ You are not authorized to use this command.")
        await channel_log(bot, update, "/invite", f"Unauthorized access attempt", level="WARNING")

@advAiBot.on_message(filters.command("uinfo"))
async def info_commands(bot, update):
    if update.from_user.id in config.ADMINS:
        logger.info(f"Admin {update.from_user.id} requested user info")
        await info_command(bot, update)
        await channel_log(bot, update, "/uinfo", "Admin requested user info")
    else:
        logger.warning(f"Unauthorized user {update.from_user.id} attempted to use uinfo command")
        await update.reply_text("⛔ You are not authorized to use this command.")
        await channel_log(bot, update, "/uinfo", f"Unauthorized access attempt", level="WARNING")
        
@advAiBot.on_message(filters.text & filters.command(["ai", "ask", "say"]) & filters.group)
async def handle_group_message(bot, update):
    bot_stats["messages_processed"] += 1
    bot_stats["active_users"].add(update.from_user.id)
    
    # Check if the command has any text after it
    if len(update.text.split()) > 1:
        update.text = update.text.split(None, 1)[1]
    else:
        await update.reply_text("Please provide your query after the command.")
        return
    
    # Process the message with typing indicator
    await bot.send_chat_action(chat_id=update.chat.id, action=ChatAction.TYPING)
    await user_log(bot, update, update.text)
    await aires(bot, update)


@advAiBot.on_message(filters.command(["newchat", "reset", "new_conversation", "clear_chat", "new"]))
async def handle_new_chat(client, message):
    logger.info(f"User {message.from_user.id} started a new chat")
    await new_chat(client, message)
    await channel_log(client, message, "/newchat", "User started a new conversation")


@advAiBot.on_message(filters.command(["generate", "gen", "image", "img"]))
async def handle_generate(client, message):
    bot_stats["images_generated"] += 1
    bot_stats["active_users"].add(message.from_user.id)
    
    # Call the handler from image_generation.py
    await handle_generate_command(client, message)
    # Log the command usage
    await channel_log(client, message, f"/{message.command[0]}", "Image generation requested")

@advAiBot.on_message(filters.photo)
async def handle_image(bot, update):
    if update.from_user.id == bot.me.id:
        return
        
    bot_stats["active_users"].add(update.from_user.id)
    
    # Handle image in private chat
    if update.chat.type == "private":
        await extract_text_res(bot, update)
    else:
        # Check if caption contains AI command keywords
        if update.caption:
            if any(keyword in update.caption.lower() for keyword in ["ai", "ask"]):
                await extract_text_res(bot, update)

@advAiBot.on_message(filters.command("settings"))
async def settings_command(bot, update):
    logger.info(f"User {update.from_user.id} accessed settings")
    await global_setting_command(bot, update)
    await channel_log(bot, update, "/settings")

@advAiBot.on_message(filters.command("stats") & filters.user(config.ADMINS))
async def stats_command(bot, update):
    logger.info(f"Admin {update.from_user.id} requested stats")
    stats_text = (
        "📊 **Bot Statistics**\n\n"
        f"💬 Messages Processed: {bot_stats['messages_processed']}\n"
        f"🖼️ Images Generated: {bot_stats['images_generated']}\n"
        f"🎙️ Voice Messages: {bot_stats['voice_messages_processed']}\n"
        f"👥 Active Users: {len(bot_stats['active_users'])}\n"
    )
    await update.reply_text(stats_text)
    await channel_log(bot, update, "/stats", "Admin requested bot statistics")

@advAiBot.on_message(filters.command(["announce", "broadcast", "acc"]))
async def announce_command(bot, update):
    if update.from_user.id in config.ADMINS:
        try:
            text = update.text.split(" ", 1)[1]
            logger.info(f"Admin {update.from_user.id} broadcasting message: {text[:50]}...")
            processing_msg = await update.reply_text("📣 Preparing to broadcast message...")
            await user_db.get_usernames_message(bot, update, text)
            await channel_log(bot, update, "/announce", f"Admin broadcast message to users", level="WARNING")
        except IndexError:
            logger.warning(f"Admin {update.from_user.id} attempted announce without message")
            await update.reply_text(
                "⚠️ Please provide a message to broadcast.\n\n"
                "Example: `/announce Hello everyone! We've added new features.`"
            )
    else:
        logger.warning(f"Unauthorized user {update.from_user.id} attempted to use announce command")
        await update.reply_text("⛔ You are not authorized to use this command.")
        await channel_log(bot, update, "/announce", f"Unauthorized access attempt", level="WARNING")

@advAiBot.on_message(filters.command("logs") & filters.user(config.ADMINS))
async def logs_command(bot, update):
    logger.info(f"Admin {update.from_user.id} requested logs")
    
    try:
        # Send status message
        status_msg = await update.reply_text(
            "📊 **Retrieving Logs**\n\n"
            "Preparing the most recent logs... This will take just a moment."
        )
        
        # Get the latest 500 lines from the main log file
        if os.path.exists(MAIN_LOG_FILE):
            # Read the log file and get the last 500 lines
            with open(MAIN_LOG_FILE, 'r', encoding='utf-8') as f:
                # Read all lines and take the last 500
                lines = f.readlines()
                last_lines = lines[-500:] if len(lines) > 500 else lines
                log_content = ''.join(last_lines)
            
            # Create a temporary file with the latest logs
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_log_file = f"logs/latest_logs_{timestamp}.txt"
            
            with open(temp_log_file, 'w', encoding='utf-8') as f:
                f.write(log_content)
            
            # Send the file
            await bot.send_document(
                chat_id=update.chat.id,
                document=temp_log_file,
                caption=f"📋 **Latest Bot Logs**\n\nShowing the most recent 500 log entries as of {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # Delete the temporary file
            try:
                os.remove(temp_log_file)
            except Exception as e:
                logger.error(f"Error removing temporary log file: {str(e)}")
                
            # Update status message
            await status_msg.edit_text("✅ **Logs Retrieved Successfully**")
            
        else:
            await status_msg.edit_text("❌ No log file found. The bot may not have generated any logs yet.")
        
        # Log this action
        await channel_log(bot, update, "/logs", "Admin requested latest logs")
        
    except Exception as e:
        logger.error(f"Error in logs command: {str(e)}")
        await update.reply_text(f"❌ **Error**\n\nFailed to retrieve logs: {str(e)}")
        
        # Log the error
        await error_log(bot, "LOGS_COMMAND", str(e), context=update.text, user_id=update.from_user.id)

@advAiBot.on_message(filters.command(["clear_cache", "clearcache", "clear_images"]))
async def clear_user_cache(client, message):
    """Handle request to clear user's image cache"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested to clear their image cache")
    
    # Clear the user's image cache
    success = await ImageService.clear_user_image_cache(user_id)
    
    if success:
        await message.reply_text("✅ **Your image cache has been cleared**\n\nAll stored image data has been removed.")
    else:
        await message.reply_text("ℹ️ **No image cache found**\n\nYou don't have any cached images to clear.")
    
    await channel_log(client, message, "/clear_cache", f"User cleared their image cache")

if __name__ == "__main__":
    # Print startup message
    logger.info("🤖 Advanced AI Telegram Bot starting...")
    print("🤖 Advanced AI Telegram Bot starting...")
    print("✨ Optimized for performance and modern UI")
    
    # Create global variables for the cleanup tasks
    cleanup_scheduler_task = None
    ongoing_generations_cleanup_task = None
    
    # Run the bot
    advAiBot.run()
