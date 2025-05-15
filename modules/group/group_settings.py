from pyrogram import Client, filters
import pyrogram.errors
import asyncio
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import LOG_CHANNEL as STCLOG, DATABASE_URL, ADMINS, OWNER_ID
import logging
from pymongo import MongoClient
from typing import List, Dict, Optional, Union
from datetime import datetime
from modules.maintenance import maintenance_check, maintenance_message, is_feature_enabled

# Set up logger
logger = logging.getLogger(__name__)

# Connect to MongoDB
client = MongoClient(DATABASE_URL)  
db = client['aibotdb']  
groups_collection = db.groups 

async def leave_group(client: Client, message):
    chat_id = message.chat.id
    bot_username = (await client.get_me()).username
    group_id = int(message.command[1])
    
    try:
        await client.leave_chat(group_id)
        await message.reply("Left the group successfully.")
        await client.send_message(STCLOG, f"#Leave\n Admin-SudoUsers {chat_id} \nReason- Admin Knows\nTask - @{bot_username} left the group {group_id}.")
    except pyrogram.errors.FloodWait as e:
        await message.reply(f"Failed to leave the group. Please try again later. Error: {e}")
    except pyrogram.errors.exceptions.ChatAdminRequired as e:
        await message.reply(f"I don't have the necessary permissions to leave the group. Please make sure I have the permission to leave. Error: {e}")
    except Exception as e:
        await message.reply(f"Failed to leave the group. Error: {e}")

async def invite_command(client, message):
    if len(message.command) != 2:
        await message.reply("Invalid command! Please provide a group ID.")
        return
    chat_id = message.text.split(" ")[1]

    try:
        chat_invite_link = await client.export_chat_invite_link(int(chat_id))
        await message.reply_text(f"Invite link for group {chat_id}:\n{chat_invite_link}")
    except Exception as e:
        await message.reply_text(f"Failed to get invite link for group {chat_id}.\nError: {e}")

async def leave_group(client: Client, message: Message) -> None:
    """
    Handle leaving a group through admin command
    
    Args:
        client: Telegram client
        message: Message with command
    """
    # Check maintenance mode and admin status
    if await maintenance_check(message.from_user.id) and message.from_user.id not in ADMINS:
        maint_msg = await maintenance_message(message.from_user.id)
        await message.reply(maint_msg)
        return
        
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Check if the message is in a group
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply_text("This command can only be used in groups.")
        return
    
    # Check if admin (custom check in case ADMINS list is outdated)
    if user_id in ADMINS or user_id == OWNER_ID or await is_group_admin(client, chat_id, user_id):
        # Confirm leaving
        await message.reply_text("Leaving this group, goodbye!")
        
        # Update the database
        try:
            groups_collection.update_one(
                {"chat_id": chat_id},
                {"$set": {
                    "left": True,
                    "left_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "left_by": user_id
                }},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error updating database when leaving group: {e}")
        
        # Leave the group
        try:
            await client.leave_chat(chat_id)
        except Exception as e:
            logger.error(f"Error leaving group: {e}")
    else:
        await message.reply_text("Only admins can use this command.")

async def invite_command(client: Client, message: Message) -> None:
    """
    Handle invite command to get group invite link
    
    Args:
        client: Telegram client
        message: Message with command
    """
    # Check maintenance mode and admin status
    if await maintenance_check(message.from_user.id) and message.from_user.id not in ADMINS:
        maint_msg = await maintenance_message(message.from_user.id)
        await message.reply(maint_msg)
        return
        
    user_id = message.from_user.id
    
    # Check if admin 
    if user_id in ADMINS or user_id == OWNER_ID:
        # Extract chat_id from command
        try:
            parts = message.text.split()
            if len(parts) > 1:
                target_chat = parts[1]
                
                # Try to get invite link
                try:
                    if target_chat.startswith("@"):
                        # It's a username
                        chat = await client.get_chat(target_chat)
                        chat_id = chat.id
                        chat_title = chat.title
                    else:
                        # Assume it's a chat ID
                        chat_id = int(target_chat)
                        chat = await client.get_chat(chat_id)
                        chat_title = chat.title
                    
                    invite_link = await client.create_chat_invite_link(chat_id)
                    
                    # Send the invite link
                    await message.reply_text(
                        f"🔗 **Invite Link for {chat_title}**\n\n"
                        f"{invite_link.invite_link}\n\n"
                        f"Expires: {'Never' if not invite_link.expire_date else invite_link.expire_date}\n"
                        f"Created by: [You](tg://user?id={user_id})"
                    )
                except Exception as e:
                    await message.reply_text(f"Error getting invite link: {str(e)}")
                    logger.error(f"Error getting invite link: {e}")
            else:
                await message.reply_text(
                    "Please specify a chat ID or username.\n\n"
                    "Usage: `/invite @chatusername` or `/invite -1001234567890`"
                )
        except Exception as e:
            await message.reply_text(f"Error processing command: {str(e)}")
            logger.error(f"Error in invite command: {e}")
    else:
        await message.reply_text("Only admins can use this command.")

async def is_group_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """
    Check if a user is an admin in a group
    
    Args:
        client: Telegram client
        chat_id: Chat ID to check
        user_id: User ID to check
        
    Returns:
        True if user is admin, False otherwise
    """
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in ["creator", "administrator"]
    except Exception:
        return False