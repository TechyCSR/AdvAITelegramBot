import logging
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.enums import ChatMemberStatus, ChatType
from config import LOG_CHANNEL as STCLOG, DATABASE_URL
from pymongo import MongoClient
from datetime import datetime
import asyncio

# Set up logger
logger = logging.getLogger(__name__)

# Connect to MongoDB
client = MongoClient(DATABASE_URL)
db = client['aibotdb']
groups_collection = db.groups

# Required bot permissions in groups
REQUIRED_PERMISSIONS = {
    "can_delete_messages": "Delete Messages",
    "can_invite_users": "Invite Users via Link"
}

# Optional but recommended permissions
RECOMMENDED_PERMISSIONS = {
    "can_pin_messages": "Pin Messages",
    "can_change_info": "Change Group Info"
}

async def check_bot_permissions(client: Client, chat_id: int) -> dict:
    """
    Check what permissions the bot has in a given group
    
    Args:
        client: Telegram client
        chat_id: Chat ID to check
        
    Returns:
        Dictionary with permission status
    """
    try:
        # Get the bot's user ID
        bot_id = (await client.get_me()).id
        
        # Get bot's member info in the group
        bot_member = await client.get_chat_member(chat_id, bot_id)
        
        # Initialize permissions dictionary
        permissions = {}
        
        # Check if bot is admin
        is_admin = bot_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
        permissions["is_admin"] = is_admin
        
        if is_admin and hasattr(bot_member, 'privileges'):
            # Check specific permissions
            for perm_name, _ in {**REQUIRED_PERMISSIONS, **RECOMMENDED_PERMISSIONS}.items():
                permissions[perm_name] = getattr(bot_member.privileges, perm_name, False)
        else:
            # Not admin, so no permissions
            for perm_name in {**REQUIRED_PERMISSIONS, **RECOMMENDED_PERMISSIONS}.keys():
                permissions[perm_name] = False
                
        # Add chat info
        chat = await client.get_chat(chat_id)
        permissions["chat_title"] = chat.title
        permissions["chat_type"] = chat.type
        permissions["chat_members_count"] = await client.get_chat_members_count(chat_id)
        
        # Log permissions check
        logger.info(f"Checked permissions in group {chat_id}: {permissions}")
        
        return permissions
        
    except Exception as e:
        logger.error(f"Error checking bot permissions in group {chat_id}: {e}")
        return {
            "error": str(e),
            "is_admin": False,
            **{perm_name: False for perm_name in {**REQUIRED_PERMISSIONS, **RECOMMENDED_PERMISSIONS}.keys()}
        }

async def has_required_permissions(client: Client, chat_id: int) -> bool:
    """
    Check if the bot has all required permissions
    
    Args:
        client: Telegram client
        chat_id: Chat ID to check
        
    Returns:
        True if all required permissions are granted, False otherwise
    """
    perms = await check_bot_permissions(client, chat_id)
    
    if "error" in perms:
        # Error occurred during permission check
        return False
        
    # Check if all required permissions are granted
    for perm_name in REQUIRED_PERMISSIONS.keys():
        if not perms.get(perm_name, False):
            return False
            
    return True

async def update_group_stats(chat_id: int, permissions: dict, added_by_user_id: int = None) -> None:
    """
    Update group statistics in the database
    
    Args:
        chat_id: Group chat ID
        permissions: Permissions dictionary
        added_by_user_id: User ID who added the bot (optional)
    """
    try:
        # Prepare update data
        update_data = {
            "last_active": datetime.now(),
            "permissions": permissions,
            "members_count": permissions.get("chat_members_count", 0),
            "title": permissions.get("chat_title", "Unknown Group")
        }
        
        # Add first seen if this is a new group
        existing_group = groups_collection.find_one({"chat_id": chat_id})
        if not existing_group:
            update_data["first_seen"] = datetime.now()
            update_data["added_by"] = added_by_user_id
            
        # Update the database
        groups_collection.update_one(
            {"chat_id": chat_id},
            {"$set": update_data},
            upsert=True
        )
        
        logger.info(f"Updated group stats for {chat_id}")
    except Exception as e:
        logger.error(f"Error updating group stats for {chat_id}: {e}")

async def send_permissions_message(client: Client, chat_id: int, permissions: dict) -> None:
    """
    Send a message about missing permissions
    
    Args:
        client: Telegram client
        chat_id: Chat ID to send to
        permissions: Permissions dictionary
    """
    # Check which required permissions are missing
    missing_required = []
    for perm_name, perm_label in REQUIRED_PERMISSIONS.items():
        if not permissions.get(perm_name, False):
            missing_required.append(perm_label)
            
    # Only send a message if required permissions are missing
    if missing_required:
        message_text = "⚠️ **I'm missing some required permissions!**\n\n"
        message_text += "To work correctly in this group, I need these permissions:\n"
        for perm in missing_required:
            message_text += f"• {perm} ❌\n"
                
        message_text += "\nPlease ask a group admin to grant these permissions."
        
        # Add tutorial button
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("How to set permissions", callback_data="group_permissions_help")]
        ])
        
        await client.send_message(chat_id, message_text, reply_markup=keyboard)
    # No message is sent if only recommended permissions are missing

async def handle_permissions_help(client: Client, callback_query):
    """
    Handle the permissions help callback
    
    Args:
        client: Telegram client
        callback_query: Callback query
    """
    help_text = """
📖 **How to set bot permissions**

1️⃣ Open your group settings
2️⃣ Go to "Administrators"
3️⃣ Tap on my name (@AdvChatGptBot)
4️⃣ Enable these permissions:
   • Delete Messages
   • Invite Users via Link
   • Pin Messages (recommended)
   • Change Group Info (recommended)
5️⃣ Tap "Save" to apply changes

These permissions help me serve your group better!
"""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Got it!", callback_data="dismiss_permissions_help")]
    ])
    
    await callback_query.edit_message_text(help_text, reply_markup=keyboard)

async def leave_group_if_no_permissions(client: Client, chat_id: int, message_before_leave: bool = True) -> bool:
    """
    Check permissions and leave the group if required ones are missing
    
    Args:
        client: Telegram client
        chat_id: Chat ID to check
        message_before_leave: Whether to send message before leaving
        
    Returns:
        True if bot left the group, False otherwise
    """
    try:
        # Check permissions
        perms = await check_bot_permissions(client, chat_id)
        
        # Update group stats
        await update_group_stats(chat_id, perms)
        
        # Check if all required permissions are available
        has_perms = True
        for perm_name in REQUIRED_PERMISSIONS.keys():
            if not perms.get(perm_name, False):
                has_perms = False
                break
                
        if not has_perms:
            # Send message before leaving if requested
            if message_before_leave:
                message_text = """
⚠️ **I'm missing required permissions**

I need the following permissions to work correctly:
• Delete Messages
• Invite Users via Link

Since these permissions are needed for me to function properly, I'll leave this group.
You can add me back once these permissions are ready to be granted.

Goodbye! 👋
"""
                await client.send_message(chat_id, message_text)
                
                # Wait a moment for message to be seen
                await asyncio.sleep(3)
                
            # Log leaving due to missing permissions
            group_info = f"Chat ID: {chat_id}"
            if "chat_title" in perms:
                group_info += f", Title: {perms['chat_title']}"
                
            await client.send_message(
                STCLOG,
                f"#LeftGroup\nReason: Missing required permissions\n{group_info}"
            )
            
            # Leave the group
            await client.leave_chat(chat_id)
            
            # Mark as left in database
            groups_collection.update_one(
                {"chat_id": chat_id},
                {"$set": {
                    "left": True, 
                    "left_at": datetime.now(),
                    "left_reason": "Missing required permissions"
                }}
            )
            
            return True
            
        return False
        
    except Exception as e:
        logger.error(f"Error in leave_group_if_no_permissions for {chat_id}: {e}")
        return False 