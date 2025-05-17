"""
Test script for the chat history command
"""
import os
import sys
import logging
import asyncio
from datetime import datetime

# Add the project root to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.admin.user_history import get_user_chat_history
from modules.core.database import get_history_collection, get_user_collection

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("history_cmd_test")

# Mock Pyrogram objects for testing
class MockClient:
    async def send_chat_action(self, chat_id, action):
        logger.info(f"Sending chat action {action} to {chat_id}")
    
    async def send_document(self, chat_id, document, caption, reply_markup=None):
        logger.info(f"Sending document {document} to {chat_id}")
        logger.info(f"Caption: {caption}")
        if reply_markup:
            logger.info("With reply markup")
        return True

class MockMessage:
    def __init__(self, chat_id):
        self.chat = type('obj', (object,), {'id': chat_id})

class MockStatusMessage:
    def __init__(self):
        self.text = ""
    
    async def edit_text(self, text):
        self.text = text
        logger.info(f"Status message updated: {text}")
        return self
    
    async def delete(self):
        logger.info("Status message deleted")
        return True

async def test_history_command():
    """Test the history command with a real user ID"""
    user_id = 5293138954  # User ID to test
    
    # Create mock objects
    mock_client = MockClient()
    mock_message = MockMessage(chat_id=123456)
    mock_status = MockStatusMessage()
    
    logger.info(f"Testing get_user_chat_history for user ID: {user_id}")
    
    # Run the function
    await get_user_chat_history(mock_client, mock_message, user_id, mock_status)
    
    logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(test_history_command()) 