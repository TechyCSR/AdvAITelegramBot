import asyncio
from typing import List, Optional, Dict, Any
from modules.core.database import get_user_collection, get_user_lang_collection

async def check_and_add_username(user_id: int, username: str) -> None:
    """
    Check if a username exists in the users collection, and add it if it doesn't.
    
    Args:
        user_id: Telegram user ID
        username: Telegram username
    """
    users_collection = get_user_collection()
    user = users_collection.find_one({"user_id": user_id})
    
    if user:
        if "username" in user:
            if user["username"] == username:
                return
    
    users_collection.update_one(
        {"user_id": user_id}, 
        {"$set": {"username": username}},
        upsert=True
    )
    print(f"Username {username} was added to user ID {user_id}.")
    

async def check_and_add_user(user_id: int) -> None:
    """
    Check if a user ID exists in the users collection, and add it if it doesn't.
    
    Args:
        user_id: Telegram user ID
    """
    users_collection = get_user_collection()
    user = users_collection.find_one({"user_id": user_id})
    
    if not user:
        users_collection.insert_one({"user_id": user_id})
        print(f"User ID {user_id} was added to the users collection.")

def drop_user_id(user_id: int) -> None:
    """
    Remove a specific user ID from the users collection.
    
    Args:
        user_id: Telegram user ID to remove
    """
    users_collection = get_user_collection()
    result = users_collection.delete_one({"user_id": user_id})
    
    if result.deleted_count == 1:
        print(f"User ID {user_id} was successfully deleted.")

def get_user_ids() -> List[int]:
    """
    Retrieve all user IDs from the users collection.
    
    Returns:
        List of user IDs
    """
    users_collection = get_user_collection()
    user_ids = users_collection.distinct("user_id")
    print(f"Retrieved {len(user_ids)} user IDs.")
    return user_ids

def get_user_language(user_id: int) -> str:
    """
    Get user's preferred language from database
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        Language code (defaults to 'en' if not set)
    """
    user_lang_collection = get_user_lang_collection()
    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
    
    if user_lang_doc:
        return user_lang_doc['language']
    
    return 'en'  # Default to English if not set

def check_and_add_blocked_user(user_id: int) -> None:
    """
    Add a user to the blocked users collection if not already there
    
    Args:
        user_id: Telegram user ID to block
    """
    from modules.core.database import db_service
    block_users_collection = db_service.get_collection('blocked_users')
    
    user = block_users_collection.find_one({"user_id": user_id})
    if not user:
        block_users_collection.insert_one({"user_id": user_id})
        print(f"User ID {user_id} was added to the blocked users collection.")

async def get_user_ids_message(bot, update, text: str) -> None:
    """
    Send a message to all users
    
    Args:
        bot: Telegram bot instance
        update: Message update
        text: Message text to send
    """
    users_collection = get_user_collection()
    user_ids = users_collection.distinct("user_id")
    total = 0
    
    await update.reply_text(f"Sending message to {len(user_ids)} users...")
    
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, text)
            await asyncio.sleep(0.05)
            total += 1
        except Exception as e:
            print(f"Error sending message to user ID {user_id}: {e}")
    
    await update.reply_text(f"Message sent to {total} users.")

async def get_usernames_message(bot, update, text: str, parse_mode=None) -> None:
    """
    Send a message to all users with usernames and pin the message with notification
    
    Args:
        bot: Telegram bot instance
        update: Message update
        text: Message text to send
        parse_mode: Telegram parse mode (e.g., 'markdown', 'html')
    """
    users_collection = get_user_collection()
    users = users_collection.find({"username": {"$exists": True}})
    total = 0
    await update.reply_text(f"Sending message to users with usernames...")
    for user in users:
        try:
            sent_msg = await bot.send_message(user["username"], text, parse_mode=parse_mode)
            await asyncio.sleep(0.05)
            try:
                await bot.pin_chat_message(sent_msg.chat.id, sent_msg.id, disable_notification=False)
            except Exception as e:
                print(f"Could not pin message for user {user['user_id']}: {e}")
            total += 1
        except Exception as e:
            print(f"Error sending message to user ID {user['user_id']}: {e}")
    await update.reply_text(f"Message sent to {total} users.") 