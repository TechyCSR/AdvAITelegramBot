from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
import logging
from pymongo import MongoClient
from config import DATABASE_URL

global maintenance_text

maintenance_text = """
🚧 This section is under development.
Please check back later.
~@AdvChatGptBot
"""
    

# Function to handle settings_others callback
async def settings_others_callback(client, callback: CallbackQuery):
    global maintenance_text
    await callback.answer(maintenance_text, show_alert=True)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize MongoDB client
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
maintenance_collection = db['maintenance']

async def is_maintenance_mode() -> bool:
    """Check if maintenance mode is enabled."""
    try:
        result = maintenance_collection.find_one({"setting": "maintenance_mode"})
        return result.get("enabled", False) if result else False
    except Exception as e:
        logger.error(f"Error checking maintenance mode: {e}")
        return False

async def set_maintenance_mode(enabled: bool) -> bool:
    """Set maintenance mode status."""
    try:
        maintenance_collection.update_one(
            {"setting": "maintenance_mode"},
            {"$set": {"enabled": enabled}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error setting maintenance mode: {e}")
        return False

async def toggle_maintenance_mode() -> bool:
    """Toggle maintenance mode status."""
    try:
        current_status = await is_maintenance_mode()
        return await set_maintenance_mode(not current_status)
    except Exception as e:
        logger.error(f"Error toggling maintenance mode: {e}")
        return False

