import datetime
from pymongo import MongoClient
from config import DATABASE_URL
from typing import Optional, Tuple



# Initialize MongoDB client and collection
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
user_bans_collection = db['user_bans']

async def ban_user(user_id: int, admin_id: int, reason: str = "No reason provided.") -> bool:
    """Bans a user, storing their ID, reason, and ban timestamp."""
    if not isinstance(user_id, int) or not isinstance(admin_id, int):
        return False
        
    ban_record = {
        "user_id": user_id,
        "is_banned": True,
        "reason": reason,
        "banned_at": datetime.datetime.utcnow(),
        "banned_by": admin_id
    }
    user_bans_collection.update_one({"user_id": user_id}, {"$set": ban_record}, upsert=True)
    return True

async def unban_user(user_id: int) -> bool:
    """Unbans a user by removing their record or marking as not banned."""
    if not isinstance(user_id, int):
        return False
        
    result = user_bans_collection.update_one({"user_id": user_id}, {"$set": {"is_banned": False, "unbanned_at": datetime.datetime.utcnow()}})
    return result.modified_count > 0

async def is_user_banned(user_id: int) -> Tuple[bool, Optional[str]]:
    """Checks if a user is banned. Returns (True, reason) if banned, else (False, None)."""
    if not isinstance(user_id, int):
        return False, None # Or raise an error
        
    ban_record = user_bans_collection.find_one({"user_id": user_id, "is_banned": True})
    if ban_record:
        return True, ban_record.get("reason", "No reason provided.")
    return False, None

async def get_banned_message(reason: str) -> str:
    """Returns the formatted message to show to a banned user."""
    return (
        f"🚫 **You have been banned from using this bot.** 🚫\n\n"
        f"<b>Reason:</b> {reason}\n\n"
        f"If you believe this is a mistake, please contact an administrator: @techycsr"
    )

async def get_user_by_id_or_username(client, identifier):
    """Helper to get user object by ID or username."""
    try:
        if isinstance(identifier, int):
            return await client.get_users(identifier)
        elif isinstance(identifier, str):
            return await client.get_users(identifier.strip('@'))
    except Exception:
        return None
    return None 