import logging
from pymongo import MongoClient
from config import DATABASE_URL

# Configure logging
logger = logging.getLogger(__name__)

# Initialize MongoDB client
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
welcome_collection = db['welcome']

async def is_welcome_enabled() -> bool:
    """Check if welcome message is enabled."""
    try:
        result = welcome_collection.find_one({"setting": "welcome_message"})
        return result.get("enabled", True) if result else True  # Default to True if not set
    except Exception as e:
        logger.error(f"Error checking welcome message status: {e}")
        return True

async def set_welcome_enabled(enabled: bool) -> bool:
    """Set welcome message status."""
    try:
        welcome_collection.update_one(
            {"setting": "welcome_message"},
            {"$set": {"enabled": enabled}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error setting welcome message status: {e}")
        return False

async def toggle_welcome() -> bool:
    """Toggle welcome message status."""
    try:
        current_status = await is_welcome_enabled()
        return await set_welcome_enabled(not current_status)
    except Exception as e:
        logger.error(f"Error toggling welcome message: {e}")
        return False 