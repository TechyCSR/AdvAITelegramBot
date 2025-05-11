import logging
from pymongo import MongoClient
from config import DATABASE_URL

# Configure logging
logger = logging.getLogger(__name__)

# Initialize MongoDB client
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
auto_delete_collection = db['auto_delete']

async def is_auto_delete_enabled() -> bool:
    """Check if auto delete is enabled."""
    try:
        result = auto_delete_collection.find_one({"setting": "auto_delete"})
        return result.get("enabled", False) if result else False
    except Exception as e:
        logger.error(f"Error checking auto delete status: {e}")
        return False

async def set_auto_delete_enabled(enabled: bool) -> bool:
    """Set auto delete status."""
    try:
        auto_delete_collection.update_one(
            {"setting": "auto_delete"},
            {"$set": {"enabled": enabled}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error setting auto delete status: {e}")
        return False

async def toggle_auto_delete() -> bool:
    """Toggle auto delete status."""
    try:
        current_status = await is_auto_delete_enabled()
        return await set_auto_delete_enabled(not current_status)
    except Exception as e:
        logger.error(f"Error toggling auto delete: {e}")
        return False 