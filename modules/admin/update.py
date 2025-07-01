import os
import sys
import logging
import asyncio
import time
import subprocess
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMINS

logger = logging.getLogger(__name__)

async def update_command(client: Client, message: Message):
    """
    Handle the update command - only for admin users
    Updates bot from GitHub and restarts it
    """
    # Check if user is admin
    if message.from_user.id not in ADMINS:
        await message.reply(
            "⛔ **Access Denied**\n\n"
            "Only bot administrators can use this command."
        )
        logger.warning(f"Non-admin user {message.from_user.id} attempted to use update command")
        return
    
    # Get username or first name for personalized message
    user_name = message.from_user.username or message.from_user.first_name
    
    # Create update keyboard with confirmation
    update_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Update Now", callback_data="confirm_update"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_update")
        ]
    ])
    
    # Send confirmation message
    await message.reply(
        f"🔄 **Update Confirmation**\n\n"
        f"Are you sure you want to update the bot from GitHub, {user_name}?\n\n"
        "This will:\n"
        "• Update g4f library to latest version\n"
        "• Pull the latest code from GitHub\n"
        "• Restart the bot with new changes\n"
        "• Bot will be unavailable for 15-45 seconds\n\n"
        "⚠️ **Warning**: Any uncommitted local changes may be lost!",
        reply_markup=update_keyboard
    )
    
    logger.info(f"Admin {message.from_user.id} requested update confirmation")

async def handle_update_callback(client: Client, callback_query):
    """Handle update confirmation or cancellation"""
    # Verify user is admin
    if callback_query.from_user.id not in ADMINS:
        await callback_query.answer("You don't have permission to perform this action", show_alert=True)
        return
    
    if callback_query.data == "confirm_update":
        # Update the message to show update is in progress
        await callback_query.message.edit_text(
            "🔄 **Updating Bot**\n\n"
            "Step 1/4: Updating g4f library to latest version...\n\n"
            "Please wait, this may take a moment."
        )
        
        # Log the update event
        logger.warning(f"Admin {callback_query.from_user.id} initiated bot update")
        
        # Perform the update
        await perform_update(client, callback_query)
        
    elif callback_query.data == "cancel_update":
        # Update the message to show cancellation
        await callback_query.message.edit_text(
            "✅ **Update Cancelled**\n\n"
            "Bot update has been cancelled. The bot will continue to run with the current version."
        )
        logger.info(f"Admin {callback_query.from_user.id} cancelled update")

async def perform_update(client: Client, callback_query):
    """Actually perform the update operation"""
    try:
        # Step 1: Update g4f to latest version
        await callback_query.message.edit_text(
            "🔄 **Updating Bot**\n\n"
            "Step 1/4: Updating g4f library to latest version...\n\n"
            "📦 Installing latest dependencies..."
        )
        
        # Update g4f to latest version
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'g4f'], 
                                  capture_output=True, text=True, cwd='.')
            
            if result.returncode != 0:
                logger.warning(f"g4f update warning: {result.stderr}")
                # Don't fail the entire update if g4f update fails, just log it
                g4f_status = "⚠️ g4f update had warnings (check logs)"
            else:
                logger.info("g4f updated successfully")
                g4f_status = "✅ g4f updated to latest version"
                
        except Exception as e:
            logger.error(f"Error updating g4f: {str(e)}")
            g4f_status = "⚠️ g4f update failed (check logs)"
        
        # Step 2: Check git status
        await callback_query.message.edit_text(
            "🔄 **Updating Bot**\n\n"
            "Step 2/4: Checking repository status...\n\n"
            "⏳ Please wait..."
        )
        
        # Check if we're in a git repository
        result = subprocess.run(['git', 'rev-parse', '--git-dir'], 
                              capture_output=True, text=True, cwd='.')
        
        if result.returncode != 0:
            await callback_query.message.edit_text(
                "❌ **Update Failed**\n\n"
                "Error: This is not a Git repository.\n"
                "Please ensure the bot is cloned from GitHub using `git clone`."
            )
            logger.error("Update failed: Not a git repository")
            return
        
        # Step 3: Fetch latest changes
        await callback_query.message.edit_text(
            "🔄 **Updating Bot**\n\n"
            "Step 3/4: Fetching latest changes from GitHub...\n\n"
            "📡 Downloading updates..."
        )
        
        # Fetch from origin
        result = subprocess.run(['git', 'fetch', 'origin'], 
                              capture_output=True, text=True, cwd='.')
        
        if result.returncode != 0:
            await callback_query.message.edit_text(
                f"❌ **Update Failed**\n\n"
                f"Error fetching from GitHub:\n"
                f"```\n{result.stderr}\n```\n\n"
                f"Please check your internet connection and repository access."
            )
            logger.error(f"Git fetch failed: {result.stderr}")
            return
        
        # Check if there are updates available
        result = subprocess.run(['git', 'rev-list', '--count', 'HEAD..origin/main'], 
                              capture_output=True, text=True, cwd='.')
        
        commits_behind = result.stdout.strip()
        
        if commits_behind == "0":
            await callback_query.message.edit_text(
                "✅ **Already Up to Date**\n\n"
                "The bot is already running the latest version from GitHub.\n"
                "No updates are available."
            )
            logger.info("No updates available")
            return
        
        # Step 4: Pull changes
        await callback_query.message.edit_text(
            "🔄 **Updating Bot**\n\n"
            f"Step 4/4: Applying {commits_behind} new update(s)...\n\n"
            "🔄 Pulling changes from GitHub..."
        )
        
        # Pull the latest changes
        result = subprocess.run(['git', 'pull', 'origin', 'main'], 
                              capture_output=True, text=True, cwd='.')
        
        if result.returncode != 0:
            await callback_query.message.edit_text(
                f"❌ **Update Failed**\n\n"
                f"Error pulling changes:\n"
                f"```\n{result.stderr}\n```\n\n"
                f"You may need to resolve conflicts manually."
            )
            logger.error(f"Git pull failed: {result.stderr}")
            return
        
        # Success message before restart
        await callback_query.message.edit_text(
            "✅ **Update Successful**\n\n"
            f"✅ Downloaded {commits_behind} new update(s) from GitHub\n"
            f"{g4f_status}\n\n"
            "🔄 **Restarting bot now...**\n"
            "The bot will be back online in 10-15 seconds."
        )
        
        logger.info(f"Update successful: {commits_behind} commits pulled")
        
        # Give a moment for the message to be sent
        await asyncio.sleep(2)
        
        # Create restart marker for post-restart notification
        with open("update_marker.txt", "w") as f:
            restart_data = f"{time.time()},{callback_query.from_user.id},{callback_query.message.chat.id},{callback_query.message.id},{commits_behind},{g4f_status}"
            f.write(restart_data)
            os.fsync(f.fileno())
        
        # Log final message before restart
        logger.warning("🔄 BOT UPDATING AND RESTARTING NOW...")
        
        # Restart the bot
        await perform_restart_after_update()
        
    except Exception as e:
        error_msg = f"Error during update: {str(e)}"
        logger.error(error_msg)
        
        try:
            await callback_query.message.edit_text(
                f"❌ **Update Failed**\n\n"
                f"An unexpected error occurred:\n"
                f"```\n{str(e)}\n```\n\n"
                f"The bot will continue running with the current version."
            )
        except:
            pass

async def perform_restart_after_update():
    """Restart the bot after successful update"""
    try:
        # Get the path to the bot script
        script_path = sys.argv[0]
        python_executable = sys.executable
        
        logger.info(f"Restarting after update with script: {script_path}")
        
        # Give a moment for all operations to complete
        await asyncio.sleep(1)
        
        # Close standard file descriptors
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except:
            pass
            
        # Execute the restart
        os.execv(python_executable, [python_executable, script_path])
        
    except Exception as e:
        logger.error(f"Error during restart after update: {str(e)}")

async def check_update_marker(client: Client):
    """Check if bot was updated and notify admin who requested it"""
    try:
        marker_file = "update_marker.txt"
        if not os.path.exists(marker_file):
            return
            
        logger.info("Update marker found - processing")
        
        try:
            with open(marker_file, "r") as f:
                data = f.read().strip().split(",")
                
            if len(data) < 5:
                logger.warning(f"Update marker file has invalid format: {data}")
                return
                
            # Handle both old format (5 items) and new format (6 items with g4f status)
            if len(data) >= 6:
                timestamp, user_id, chat_id, message_id, commits_count, g4f_status = data[0], data[1], data[2], data[3], data[4], data[5]
            else:
                timestamp, user_id, chat_id, message_id, commits_count = data
                g4f_status = "✅ g4f update status unknown"
            update_time = time.strftime('%Y-%m-%d %H:%M:%S', 
                                     time.localtime(float(timestamp)))
            
            logger.info(f"Bot was updated by admin {user_id} at {update_time}")
            
            # Get current commit info
            try:
                result = subprocess.run(['git', 'log', '-1', '--format=%H %s'], 
                                      capture_output=True, text=True, cwd='.')
                commit_info = result.stdout.strip() if result.returncode == 0 else "Unknown"
            except:
                commit_info = "Unknown"
            
            # Send confirmation message
            try:
                await client.edit_message_text(
                    chat_id=int(chat_id),
                    message_id=int(message_id),
                    text="✅ **Bot Updated & Restarted Successfully!**\n\n"
                         f"📅 Update initiated: {update_time}\n"
                         f"📅 Completed: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                         f"📊 Changes applied: {commits_count} commit(s)\n"
                         f"📦 g4f library: {g4f_status.replace('✅ ', '').replace('⚠️ ', '')}\n\n"
                         f"🆕 **Latest commit:**\n"
                         f"`{commit_info[:50]}...`\n\n"
                         "🚀 The bot is now running the latest version!"
                )
                logger.info(f"Sent update confirmation to admin {user_id}")
            except Exception as e:
                logger.error(f"Failed to send update confirmation: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error processing update marker: {str(e)}")
        
        # Delete the marker file
        try:
            os.remove(marker_file)
            logger.info("Update marker file deleted")
        except Exception as e:
            logger.error(f"Failed to delete update marker file: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error checking update marker: {str(e)}") 