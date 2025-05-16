import os
import sys
import logging
import asyncio
import time
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMINS

logger = logging.getLogger(__name__)

async def restart_command(client: Client, message: Message):
    """
    Handle the restart command - only for admin users
    Safely stops and restarts the bot
    """
    # Check if user is admin
    if message.from_user.id not in ADMINS:
        await message.reply(
            "⛔ **Access Denied**\n\n"
            "Only bot administrators can use this command."
        )
        logger.warning(f"Non-admin user {message.from_user.id} attempted to use restart command")
        return
    
    # Get username or first name for personalized message
    user_name = message.from_user.username or message.from_user.first_name
    
    # Create restart keyboard with confirmation
    restart_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Restart Now", callback_data="confirm_restart"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_restart")
        ]
    ])
    
    # Send confirmation message
    await message.reply(
        f"🔄 **Restart Confirmation**\n\n"
        f"Are you sure you want to restart the bot, {user_name}?\n\n"
        "All current operations will be interrupted and the bot will be unavailable for a few seconds.",
        reply_markup=restart_keyboard
    )
    
    logger.info(f"Admin {message.from_user.id} requested restart confirmation")

async def handle_restart_callback(client: Client, callback_query):
    """Handle restart confirmation or cancellation"""
    # Verify user is admin
    if callback_query.from_user.id not in ADMINS:
        await callback_query.answer("You don't have permission to perform this action", show_alert=True)
        return
    
    if callback_query.data == "confirm_restart":
        # Update the message to show restart is in progress
        await callback_query.message.edit_text(
            "🔄 **Restarting Bot**\n\n"
            "The bot is shutting down and will restart momentarily...\n\n"
            "This typically takes 5-10 seconds. Thanks for your patience."
        )
        
        # Log the restart event
        logger.warning(f"Admin {callback_query.from_user.id} initiated bot restart")
        
        # Give a moment for the message to be sent
        await asyncio.sleep(1)
        
        # Perform the restart
        await perform_restart(client, callback_query)
        
    elif callback_query.data == "cancel_restart":
        # Update the message to show cancellation
        await callback_query.message.edit_text(
            "✅ **Restart Cancelled**\n\n"
            "Bot restart has been cancelled. The bot will continue to run normally."
        )
        logger.info(f"Admin {callback_query.from_user.id} cancelled restart")

async def perform_restart(client: Client, callback_query):
    """Actually perform the restart operation"""
    try:
        # Get the path to the bot script
        script_path = sys.argv[0]  # The main script that was run (should be run.py)
        logger.info(f"Preparing to restart with script: {script_path}")
        
        # Create a restart marker file to indicate intentional restart
        with open("restart_marker.txt", "w") as f:
            # Format: timestamp,user_id,chat_id,message_id
            restart_data = f"{time.time()},{callback_query.from_user.id},{callback_query.message.chat.id},{callback_query.message.id}"
            f.write(restart_data)
            logger.info(f"Restart marker created with data: {restart_data}")
            
            # Make sure restart marker is written to disk before closing
            os.fsync(f.fileno())
        
        # Log final message before restart
        logger.warning("🔄 BOT RESTARTING NOW...")
        
        # Give a moment for all operations to complete
        await asyncio.sleep(1)
        
        # We can't use await client.stop() here because it causes a deadlock
        # Instead, we just exit and restart directly

        # Use os.execv to replace the current process with a new one
        python_executable = sys.executable  # Path to Python interpreter
        
        # Close standard file descriptors to ensure clean restart
        # This helps prevent resource leaks
        try:
            # Close non-essential resources
            sys.stdout.flush()
            sys.stderr.flush()
        except:
            pass
            
        # Execute the restart using os.execv
        os.execv(python_executable, [python_executable, script_path])
        
    except Exception as e:
        error_msg = f"Error during restart: {str(e)}"
        logger.error(error_msg)
        
        # Try to notify the admin
        try:
            await callback_query.message.edit_text(
                f"❌ **Restart Failed**\n\n"
                f"An error occurred while trying to restart: {str(e)}\n\n"
                f"The bot will continue running, but you may need to restart it manually."
            )
        except:
            # If we can't edit the message, the client might already be closing
            pass

async def check_restart_marker(client: Client):
    """Check if bot was restarted and notify admin who requested it"""
    try:
        # Check if restart marker file exists
        marker_file = "restart_marker.txt"
        if not os.path.exists(marker_file):
            logger.debug("No restart marker found - normal startup")
            return
            
        logger.info(f"Restart marker found - processing")
        
        try:
            # Read the marker file
            with open(marker_file, "r") as f:
                data = f.read().strip().split(",")
                
            if len(data) < 4:
                logger.warning(f"Restart marker file has invalid format: {data}")
                return
                
            # Extract data
            timestamp, user_id, chat_id, message_id = data
            restart_time = time.strftime('%Y-%m-%d %H:%M:%S', 
                                       time.localtime(float(timestamp)))
            
            logger.info(f"Bot was restarted by admin {user_id} at {restart_time}")
            
            # Send confirmation message
            try:
                await client.edit_message_text(
                    chat_id=int(chat_id),
                    message_id=int(message_id),
                    text="✅ **Bot Restarted Successfully!**\n\n"
                         f"Restart initiated at: {restart_time}\n"
                         f"Restart completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                         "The bot is now fully operational."
                )
                logger.info(f"Sent restart confirmation to admin {user_id}")
            except Exception as e:
                logger.error(f"Failed to send restart confirmation: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error processing restart marker: {str(e)}")
        
        # Always delete the marker file, even if there was an error processing it
        try:
            os.remove(marker_file)
            logger.info("Restart marker file deleted")
        except Exception as e:
            logger.error(f"Failed to delete restart marker file: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error checking restart marker: {str(e)}") 