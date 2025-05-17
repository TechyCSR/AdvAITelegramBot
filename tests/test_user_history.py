"""
Test file for user chat history functionality
"""
import os
import sys
import logging
import asyncio
from datetime import datetime
from pymongo import MongoClient

# Add the project root to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATABASE_URL
from modules.admin.user_history import get_user_chat_history
from modules.core.database import get_history_collection, get_user_collection

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("history_test")

# Connect to MongoDB through the database service
history_collection = get_history_collection()
users_collection = get_user_collection()

async def check_user_history(user_id: int):
    """Check if chat history exists for a specific user ID"""
    # Check if user exists
    user_data = users_collection.find_one({"user_id": user_id})
    if not user_data:
        logger.error(f"USER NOT FOUND: No user data found for ID {user_id}")
        return False
        
    # Check user history
    user_history = history_collection.find_one({"user_id": user_id})
    if not user_history:
        # Try with int user_id
        user_history = history_collection.find_one({"user_id": int(user_id)})
    
    if not user_history or 'history' not in user_history:
        logger.error(f"No chat history found for user {user_id}")
        return False
    
    # Get messages from history
    chat_entries = [entry for entry in user_history['history'] if entry.get('role') in ['user', 'assistant']]
    
    logger.info(f"User {user_id} - {user_data.get('first_name', '')} {user_data.get('last_name', '')}")
    logger.info(f"Found {len(chat_entries)} chat entries for this user")
    
    # Print message details
    for i, entry in enumerate(chat_entries):
        role = entry.get('role', '')
        content = entry.get('content', '')
        if content:
            logger.info(f"Entry #{i+1} - {role}: {content[:50]}...")
    
    return len(chat_entries) > 0

async def create_test_history(user_id: int, message: str = "Test message"):
    """Create a test history entry for a user"""
    # First check if the user exists
    user = users_collection.find_one({"user_id": user_id})
    
    if not user:
        # Create user if doesn't exist
        logger.info(f"Creating test user with ID {user_id}")
        users_collection.insert_one({
            "user_id": user_id,
            "first_name": "Test",
            "last_name": "User",
            "username": "testuser",
            "first_seen": datetime.now(),
            "last_active": datetime.now()
        })
    
    # Check if the user already has history
    existing_history = history_collection.find_one({"user_id": user_id})
    
    if existing_history and 'history' in existing_history:
        # Add to existing history
        logger.info(f"Adding to existing history for user {user_id}")
        existing_entries = existing_history['history']
        existing_entries.append({"role": "user", "content": message})
        existing_entries.append({"role": "assistant", "content": "This is a test response"})
        
        history_collection.update_one(
            {"user_id": user_id},
            {"$set": {"history": existing_entries}}
        )
    else:
        # Create new history
        logger.info(f"Creating new history for user {user_id}")
        history_collection.insert_one({
            "user_id": user_id,
            "history": [
                {"role": "assistant", "content": "I'm your advanced AI assistant. How may I assist you today?"},
                {"role": "user", "content": message},
                {"role": "assistant", "content": "This is a test response"}
            ]
        })
    
    logger.info("Test history created successfully")
    return True

async def test_specific_user(user_id: int):
    """Test history functionality for specific user ID"""
    # Check if user has history
    has_history = await check_user_history(user_id)
    
    if not has_history:
        logger.warning(f"User {user_id} has no chat history, creating test history")
        await create_test_history(user_id)
        # Check again
        has_history = await check_user_history(user_id)
        
    if has_history:
        logger.info(f"User {user_id} has chat history, can be displayed in history")
    else:
        logger.error(f"User {user_id} still has no history after creating test entry")

# Main test function
async def main():
    user_id = 5293138954  # User ID to test
    
    logger.info(f"Running user history test for user ID: {user_id}")
    await test_specific_user(user_id)
    
    logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(main()) 