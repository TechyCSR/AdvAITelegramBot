import os
import config
import pyrogram
import time
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from pyrogram.enums import ChatAction, ChatType, ParseMode
from modules.user.start import start, start_inline
from modules.user.help import help
from modules.user.commands import command_inline
from modules.user.settings import settings_inline, settings_language_callback, change_voice_setting 
from modules.user.settings import settings_voice_inlines
from modules.user.assistant import settings_assistant_callback, change_mode_setting
from modules.user.lang_settings import settings_langs_callback, change_language_setting
from modules.user.user_support import settings_support_callback, support_admins_callback, admin_panel_callback
from modules.user.dev_support import support_developers_callback
from modules.speech import text_to_voice, voice_to_text
from modules.image.img_to_text import extract_text_res, handle_show_text_callback, handle_followup_callback
from modules.maintenance import settings_others_callback, handle_feature_toggle, handle_feature_info, maintenance_check, maintenance_message, handle_donation
from modules.group.group_settings import leave_group, invite_command
from modules.feedback_nd_rating import rate_command, handle_rate_callback
from modules.group.group_info import info_command, uinfo_settings_callback, uinfo_history_callback
from modules.models.ai_res import aires, new_chat
from modules.image.image_generation import generate_command, handle_image_feedback, start_cleanup_scheduler, handle_generate_command
from modules.image.inline_image_generation import handle_inline_query, cleanup_ongoing_generations
from modules.models.inline_ai_response import cleanup_ongoing_generations as ai_cleanup_ongoing_generations
from modules.chatlogs import channel_log, user_log, error_log
from modules.user.user_settings_panel import user_settings_panel_command, handle_user_settings_callback
from modules.speech.voice_to_text import handle_voice_message, handle_voice_toggle
from modules.admin.restart import restart_command, handle_restart_callback, check_restart_marker
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

# Add a global in-memory dict to store pending group image contexts
pending_group_images = {}

@advAiBot.on_message(filters.command("start"))
async def start_command(bot, update):
    # Start the cleanup scheduler on first command
    global cleanup_scheduler_task, ongoing_generations_cleanup_task, ai_ongoing_generations_cleanup_task
    if not 'cleanup_scheduler_task' in globals() or cleanup_scheduler_task is None:
        cleanup_scheduler_task = asyncio.create_task(cleanup_scheduler())
        logger.info("Started image generation cleanup scheduler task")
        
    if not 'ongoing_generations_cleanup_task' in globals() or ongoing_generations_cleanup_task is None:
        ongoing_generations_cleanup_task = asyncio.create_task(cleanup_ongoing_generations())
        logger.info("Started inline generations cleanup scheduler task")
        
    if not 'ai_ongoing_generations_cleanup_task' in globals() or ai_ongoing_generations_cleanup_task is None:
        ai_ongoing_generations_cleanup_task = asyncio.create_task(ai_cleanup_ongoing_generations())
        logger.info("Started inline AI generations cleanup scheduler task")
    
    # Check for restart marker file on first command
    if not hasattr(advAiBot, "_restart_checked"):
        logger.info("Checking for restart marker on first command")
        await check_restart_marker(bot)
        setattr(advAiBot, "_restart_checked", True)
        
    bot_stats["active_users"].add(update.from_user.id)
    
    # Differentiate between private chats and group chats
    if update.chat.type == ChatType.PRIVATE:
        logger.info(f"User {update.from_user.id} started the bot in private chat")
        await start(bot, update)
    else:
        # This is a group chat
        logger.info(f"User {update.from_user.id} started the bot in group chat {update.chat.id} ({update.chat.title})")
        # Import the group_start function from the newly created file
        from modules.user.group_start import group_start
        await group_start(bot, update)
    
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
    # Check for maintenance mode
    if await maintenance_check(message.from_user.id):
        maint_msg = await maintenance_message(message.from_user.id)
        await message.reply(maint_msg)
        return
        
    bot_stats["messages_processed"] += 1
    bot_stats["active_users"].add(message.from_user.id)
    logger.info(f"Processing message from user {message.from_user.id}")
    await aires(client, message)

@advAiBot.on_inline_query()
async def inline_query_handler(client, inline_query):
    """Handler for inline queries, for both image generation and AI responses"""
    bot_stats["active_users"].add(inline_query.from_user.id)
    logger.info(f"Processing inline query from user {inline_query.from_user.id}: '{inline_query.query}'")
    
    # Route to appropriate handler based on query content
    await handle_inline_query(client, inline_query)

@advAiBot.on_callback_query(filters.create(lambda _, __, query: query.data in ["announce_confirm", "announce_cancel"]))
async def announce_callback_handler(bot, callback_query):
    user_id = callback_query.from_user.id
    if not hasattr(bot, "_announce_pending") or user_id not in bot._announce_pending:
        await callback_query.answer("No pending announcement.", show_alert=True)
        return
    if callback_query.data == "announce_cancel":
        del bot._announce_pending[user_id]
        await callback_query.edit_message_text("❌ Broadcast cancelled.")
        return
    # Confirm send
    text = bot._announce_pending[user_id]
    await callback_query.edit_message_text(
        f"📣 Sending broadcast to all users...\n\n{text}",
        parse_mode=ParseMode.MARKDOWN
    )
    # Send to users with Markdown
    from modules.models import user_db
    await user_db.get_usernames_message(bot, callback_query.message, text, parse_mode=ParseMode.MARKDOWN)
    await channel_log(bot, callback_query.message, "/announce", f"Admin broadcast message to users", level="WARNING")
    del bot._announce_pending[user_id]

@advAiBot.on_message(filters.voice)
async def voice(bot, message):
    # Check for maintenance mode and voice feature toggle
    from modules.maintenance import is_feature_enabled
    if await maintenance_check(message.from_user.id) or not await is_feature_enabled("voice_features"):
        maint_msg = await maintenance_message(message.from_user.id)
        await message.reply(maint_msg)
        return
    bot_stats["voice_messages_processed"] += 1
    bot_stats["active_users"].add(message.from_user.id)
    await handle_voice_message(bot, message)

# Register the toggle callback for voice/text mode
@advAiBot.on_callback_query(filters.create(lambda _, __, query: query.data.startswith("toggle_voice_")))
async def voice_toggle_callback(client, callback_query):
    await handle_voice_toggle(client, callback_query)

# Add a new handler for replies to bot messages in groups
@advAiBot.on_message(is_reply_to_bot_filter() & filters.group & filters.text & is_not_command_filter())
async def handle_reply_to_bot(bot, message):
    # Check for maintenance mode and AI response toggle
    from modules.maintenance import is_feature_enabled
    if await maintenance_check(message.from_user.id) or not await is_feature_enabled("ai_response"):
        maint_msg = await maintenance_message(message.from_user.id)
        await message.reply(maint_msg)
        return
        
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

# Register uinfo panel callbacks (move these above the generic callback_query handler)
@advAiBot.on_callback_query(filters.create(lambda _, __, q: q.data.startswith("uinfo_settings_")))
async def uinfo_settings_cb(client, callback_query):
    await uinfo_settings_callback(client, callback_query)

@advAiBot.on_callback_query(filters.create(lambda _, __, q: q.data.startswith("uinfo_history_")))
async def uinfo_history_cb(client, callback_query):
    await uinfo_history_callback(client, callback_query)

@advAiBot.on_message(filters.text & filters.command(["ai", "ask", "say"]) & filters.group)
async def handle_group_message(bot, update):
    # Check for maintenance mode and AI response feature
    from modules.maintenance import is_feature_enabled
    if await maintenance_check(update.from_user.id) or not await is_feature_enabled("ai_response"):
        maint_msg = await maintenance_message(update.from_user.id)
        await update.reply(maint_msg)
        return
        
    logger.info(f"Processing group command from user {update.from_user.id}")
    bot_stats["messages_processed"] += 1
    bot_stats["active_users"].add(update.from_user.id)
    
    # Show typing indicator while the AI generates a response
    await bot.send_chat_action(chat_id=update.chat.id, action=ChatAction.TYPING)
    
    # Log the interaction
    command = update.text.split()[0]
    await channel_log(bot, update, command)
    await user_log(bot, update, update.text)
    
    # Process the query using the AI response function
    await aires(bot, update)


@advAiBot.on_message(filters.command(["newchat", "reset", "new_conversation", "clear_chat", "new"]))
async def handle_new_chat(client, message):
    bot_stats["active_users"].add(message.from_user.id)
    await new_chat(client, message)
    await channel_log(client, message, "/newchat")


@advAiBot.on_message(filters.command(["generate", "gen", "image", "img"]))
async def handle_generate(client, message):
    # Check for maintenance mode and image generation toggle
    from modules.maintenance import is_feature_enabled
    if await maintenance_check(message.from_user.id) or not await is_feature_enabled("image_generation"):
        maint_msg = await maintenance_message(message.from_user.id)
        await message.reply(maint_msg)
        return
        
    logger.info(f"User {message.from_user.id} using image generation")
    await handle_generate_command(client, message)
    # Log the command usage
    await channel_log(client, message, f"/{message.command[0]}", "Image generation requested")

@advAiBot.on_message(filters.photo & filters.private)
async def handle_private_image(bot, update):
    """Handler for images in private chats"""
    # Check for maintenance mode
    if await maintenance_check(update.from_user.id):
        maint_msg = await maintenance_message(update.from_user.id)
        await update.reply(maint_msg)
        return
        
    bot_stats["active_users"].add(update.from_user.id)
    user_id = update.from_user.id
    
    logger.info(f"Processing private chat image for user {user_id}")
    
    # For private chats, process all images
    await extract_text_res(bot, update)
    
    # Log usage
    await channel_log(bot, update, "Private Image Analysis")
    logger.info(f"Image analysis for user {user_id} in private chat")

@advAiBot.on_message(filters.photo & filters.group)
async def handle_group_image(bot, update):
    """Handler for images in group chats"""
    if await maintenance_check(update.from_user.id):
        maint_msg = await maintenance_message(update.from_user.id)
        await update.reply(maint_msg)
        return
    bot_stats["active_users"].add(update.from_user.id)
    user_id = update.from_user.id
    logger.info(f"Group image received - Chat ID: {update.chat.id}, Title: {update.chat.title}, Caption: {update.caption}")
    if not update.caption:
        logger.info(f"Image in group {update.chat.id} ignored - no caption")
        return
    caption_lower = update.caption.lower()
    has_ai_trigger = "ai" in caption_lower or "/ai" in caption_lower
    if not has_ai_trigger:
        logger.info(f"Image in group {update.chat.id} ignored - caption doesn't contain AI trigger: {update.caption}")
        return
    # Save the image context in memory (keyed by chat_id and message_id)
    key = (update.chat.id, update.message_id)
    pending_group_images[key] = {
        "user_id": user_id,
        "photo": update.photo,
        "caption": update.caption
    }
    # Prompt user for AI response
    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, analyze with AI", callback_data=f"group_img_ai_yes_{update.chat.id}_{update.message_id}"),
            InlineKeyboardButton("❌ No", callback_data=f"group_img_ai_no_{update.chat.id}_{update.message_id}")
        ]
    ])
    await update.reply_text(
        "🤖 Do you want an AI response for this image and caption?",
        reply_markup=markup
    )
    # Log usage
    await channel_log(bot, update, "Group Image AI Prompt", "Prompted for AI response on group image")
    logger.info(f"Prompted for AI response on group image in {update.chat.id} by user {user_id}")

@advAiBot.on_callback_query(filters.create(lambda _, __, query: query.data.startswith("group_img_ai_yes_") or query.data.startswith("group_img_ai_no_")))
async def handle_group_img_ai_callback(bot, callback_query):
    data = callback_query.data
    parts = data.split("_")
    action = parts[3]  # 'yes' or 'no'
    chat_id = int(parts[4])
    message_id = int(parts[5])
    key = (chat_id, message_id)
    context = pending_group_images.get(key)
    if not context:
        await callback_query.answer("Image context expired or not found.", show_alert=True)
        return
    if action == "no":
        await callback_query.message.edit_text("❌ AI analysis cancelled for this image.")
        pending_group_images.pop(key, None)
        await callback_query.answer("Cancelled.")
        return
    # If 'yes', process the image and generate AI response
    await callback_query.message.edit_text("🔍 Processing image and generating AI response...")
    from modules.image.img_to_text import extract_text_from_image
    from modules.core.database import get_history_collection
    from modules.models.ai_res import get_response, DEFAULT_SYSTEM_MESSAGE
    user_id = context["user_id"]
    photo = context["photo"]
    caption = context["caption"]
    # Download the image
    try:
        if isinstance(photo, list):
            photo_obj = photo[-1]
        else:
            photo_obj = photo
        file_path = f"temp_{user_id}_{int(time.time())}.jpg"
        file = await bot.download_media(photo_obj.file_id, file_name=file_path)
        extracted_text, error = await extract_text_from_image(file)
        if error:
            await callback_query.message.edit_text(f"❌ Text Extraction Failed\n\n{error}")
            pending_group_images.pop(key, None)
            return
        if not extracted_text or extracted_text.strip() == "":
            await callback_query.message.edit_text("⚠️ No text detected in the image.")
            pending_group_images.pop(key, None)
            return
        # Combine extracted text and caption
        user_question = caption
        combined_text = f"{extracted_text}\n\n[User's question: {user_question}]"
        # Update user history (like in aires)
        history_collection = get_history_collection()
        user_history = history_collection.find_one({"user_id": user_id})
        if user_history and 'history' in user_history:
            history = user_history['history']
            if not isinstance(history, list):
                history = [history]
        else:
            history = DEFAULT_SYSTEM_MESSAGE.copy()
        # Add the new user query to the history
        prompt = f"The following text was extracted from an image:\n\n{combined_text}"
        history.append({"role": "user", "content": prompt})
        ai_response = get_response(history)
        history.append({"role": "assistant", "content": ai_response})
        history_collection.update_one(
            {"user_id": user_id},
            {"$set": {"history": history}},
            upsert=True
        )
        await callback_query.message.edit_text(
            f"📝 **Image Text Analysis**\n\n{ai_response}",
            disable_web_page_preview=True
        )
        pending_group_images.pop(key, None)
        # Clean up file
        try:
            if os.path.exists(file):
                os.remove(file)
        except Exception as e:
            logger.error(f"Error removing temporary file: {e}")
        await callback_query.answer("AI response generated.")
    except Exception as e:
        logger.error(f"Error processing group image AI: {e}")
        await callback_query.message.edit_text(f"Error processing the image: {str(e)}")
        pending_group_images.pop(key, None)
        await callback_query.answer("Error.")

@advAiBot.on_message(filters.command("settings"))
async def settings_command(bot, update):
    logger.info(f"User {update.from_user.id} accessed settings")
    await user_settings_panel_command(bot, update)
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
            # Show preview and ask for confirmation
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirm Send", callback_data="announce_confirm"),
                    InlineKeyboardButton("❌ Cancel", callback_data="announce_cancel")
                ]
            ])
            await update.reply_text(
                f"**Broadcast Preview:**\n\n{text}",
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
            # Store the message in a temp dict for this admin (in-memory, simple)
            if not hasattr(bot, "_announce_pending"): bot._announce_pending = {}
            bot._announce_pending[update.from_user.id] = text
        except IndexError:
            logger.warning(f"Admin {update.from_user.id} attempted announce without message")
            await update.reply_text(
                "⚠️ Please provide a message to broadcast.\n\n"
                "Example: `/announce Hello everyone! We've added new features.`",
                parse_mode=ParseMode.MARKDOWN
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

async def stats_alert(client, callback_query):
    """Show bot statistics in an alert popup"""
    from modules.maintenance import is_admin_user
    
    if not await is_admin_user(callback_query.from_user.id):
        await callback_query.answer("You don't have permission to view stats.", show_alert=True)
        return
    
    stats_text = (
        f"Messages: {bot_stats['messages_processed']}\n"
        f"Images: {bot_stats['images_generated']}\n"
        f"Voice: {bot_stats['voice_messages_processed']}\n"
        f"Users: {len(bot_stats['active_users'])}"
    )
    
    try:
        await callback_query.answer(stats_text, show_alert=True)
    except Exception as e:
        # If too long, try a shorter version
        if "MESSAGE_TOO_LONG" in str(e):
            short_stats = f"Msgs: {bot_stats['messages_processed']}, Users: {len(bot_stats['active_users'])}"
            await callback_query.answer(short_stats, show_alert=True)
        else:
            # Just acknowledge the callback
            await callback_query.answer("Could not display stats")
    
    # Refresh the admin panel with error handling
    try:
        from modules.maintenance import show_admin_panel
        await show_admin_panel(client, callback_query)
    except Exception as e:
        logger.error(f"Error refreshing admin panel: {str(e)}")
        # Don't re-raise as this is a non-critical refresh

@advAiBot.on_message(filters.group & filters.command(["pin", "unpin", "promote", "demote", "ban", "warn"]))
async def handle_group_admin_commands(bot, message):
    """Handle admin commands in groups with maintenance mode check"""
    # Check maintenance mode - exempt admins
    if await maintenance_check(message.from_user.id):
        maint_msg = await maintenance_message(message.from_user.id)
        await message.reply(maint_msg)
        return
        
    # Let normal Telegram permission system handle the actual execution
    pass

@advAiBot.on_message(filters.command("restart") & filters.user(config.ADMINS))
async def handle_restart_command(bot, update):
    """Handler for the restart command"""
    logger.info(f"Admin {update.from_user.id} used restart command")
    await restart_command(bot, update)
    await channel_log(bot, update, "/restart", "Admin initiated restart command")

@advAiBot.on_message(filters.new_chat_members)
async def handle_new_chat_members(client, message):
    """Handle when new members are added to a group, including the bot itself"""
    # Import the new_chat_members function from the group module
    from modules.group.new_group import new_chat_members
    await new_chat_members(client, message)
    
    # Log the event
    try:
        await channel_log(client, message, "new_members")
    except Exception as e:
        logger.error(f"Error logging new chat members: {e}")

@advAiBot.on_message(filters.command("history") & filters.user(config.ADMINS))
async def history_command(bot, update):
    """Handler for the history command to view a user's chat history"""
    logger.info(f"Admin {update.from_user.id} requested chat history")
    
    # Check if user ID is provided
    if len(update.command) != 2:
        await update.reply_text(
            "⚠️ **Usage**: `/history USER_ID`\n\n"
            "Please provide the user ID to view chat history."
        )
        return
    
    try:
        # Get the target user ID
        target_user_id = int(update.command[1])
        
        # Send status message
        status_msg = await update.reply_text(
            f"🔍 **Retrieving Chat History**\n\n"
            f"Fetching chat logs for user {target_user_id}... Please wait."
        )
        
        # Call the function to get user chat history
        from modules.admin.user_history import get_user_chat_history
        await get_user_chat_history(bot, update, target_user_id, status_msg)
        
        # Log this admin action
        await channel_log(bot, update, "/history", f"Admin requested chat history for user {target_user_id}")
        
    except ValueError:
        await update.reply_text("❌ **Error**: User ID must be a valid integer.")
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        await update.reply_text(f"❌ **Error retrieving chat history**: {str(e)}")
        await error_log(bot, "HISTORY_COMMAND", str(e), context=update.text, user_id=update.from_user.id)

@advAiBot.on_message(filters.text & filters.private & filters.user(config.ADMINS))
async def handle_admin_text_input(bot, message):
    """Handler for admin text input, including user ID for history search"""
    # Check if the user is awaiting user ID input for history
    from modules.core.database import get_session_collection
    session_collection = get_session_collection()
    
    try:
        # Debug logging to help trace issues
        logger.debug(f"Admin text handler received message: {message.text[:20]}...")
        
        user_session = session_collection.find_one({"user_id": message.from_user.id})
        if user_session and user_session.get("awaiting_user_id_for_history"):
            logger.info(f"Admin {message.from_user.id} providing user ID for history search: {message.text}")
            
            # Clear the session flag
            session_collection.update_one(
                {"user_id": message.from_user.id},
                {"$unset": {
                    "awaiting_user_id_for_history": "",
                    "message_id": ""
                }}
            )
            
            # Try to parse the user ID
            try:
                target_user_id = int(message.text.strip())
                
                # Send status message
                status_msg = await message.reply_text(
                    f"🔍 **Retrieving Chat History**\n\n"
                    f"Fetching chat logs for user {target_user_id}... Please wait."
                )
                
                # Call the function to get user chat history
                from modules.admin.user_history import get_user_chat_history
                await get_user_chat_history(bot, message, target_user_id, status_msg)
                
                # Log this admin action
                await channel_log(bot, message, "history_search", f"Admin searched chat history for user {target_user_id}")
                
            except ValueError:
                await message.reply_text("❌ **Error**: User ID must be a valid integer.")
            except Exception as e:
                logger.error(f"Error retrieving chat history: {e}")
                await message.reply_text(f"❌ **Error retrieving chat history**: {str(e)}")
                
            # Try to delete the original message to clean up
            try:
                await message.delete()
            except Exception as e:
                logger.debug(f"Could not delete message: {e}")
                
            # Return True to indicate we've handled this message and prevent passing to regular message handler
            return
            
        # Debug message to confirm we're continuing to normal message handling
        logger.debug(f"Admin text not for history search, proceeding to normal handling")
    except Exception as e:
        logger.error(f"Error in admin text input handler: {e}")
    
    # If we reach here, it's not a special admin action, so proceed with normal message handling
    await handle_message(bot, message)

if __name__ == "__main__":
    # Print startup message
    logger.info("🤖 Advanced AI Telegram Bot starting...")
    print("🤖 Advanced AI Telegram Bot starting...")
    print("✨ Optimized for performance and modern UI")
    
    # Create global variables for the cleanup tasks
    cleanup_scheduler_task = None
    ongoing_generations_cleanup_task = None
    ai_ongoing_generations_cleanup_task = None
    
    # Run the bot
    advAiBot.run()
