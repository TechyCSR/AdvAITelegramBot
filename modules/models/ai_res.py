import os
import asyncio
import time
import re
from typing import List, Dict, Any, Optional, Generator, Union
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from g4f.client import Client as GPTClient
from modules.core.database import get_history_collection
from modules.chatlogs import user_log


# Initialize the GPT client with a more efficient provider
gpt_client = GPTClient(provider="PollinationsAI")

def get_response(history: List[Dict[str, str]]) -> str:  
    """
    Get a non-streaming response from the AI model
    
    Args:
        history: Conversation history in the format expected by the AI model
        
    Returns:
        String response from the AI model
    """
    try:
        response = gpt_client.chat.completions.create(
            model="gpt-4o",  # Using more capable model for higher quality responses
            messages=history
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating response: {e}")
        return "I'm experiencing technical difficulties. Please try again in a moment."

def get_streaming_response(history: List[Dict[str, str]]) -> Optional[Generator]:
    """
    Get a streaming response from the AI model
    
    Args:
        history: Conversation history in the format expected by the AI model
        
    Returns:
        Generator yielding response chunks or None if there's an error
    """
    try:
        # Stream parameter set to True to get response chunks
        response = gpt_client.chat.completions.create(
            model="gpt-4o",  # Using more capable model for higher quality responses
            messages=history,
            stream=True
        )
        return response
    except Exception as e:
        print(f"Error generating streaming response: {e}")
        return None

def sanitize_markdown(text: str) -> str:
    """
    Ensures proper markdown formatting in streaming responses
    
    Args:
        text: Raw text that may contain incomplete markdown
        
    Returns:
        Text with proper markdown formatting
    """
    # Count opening and closing backticks to handle code blocks
    backticks_opened = text.count('```')
    if backticks_opened % 2 != 0:
        text += '\n```'  # Close incomplete code block
    
    # Handle inline code (single backtick)
    single_backticks = text.count('`') - (backticks_opened * 3)
    if single_backticks % 2 != 0:
        text += '`'  # Close incomplete inline code
    
    # Handle markdown bold/italic
    asterisks_count = text.count('*')
    if asterisks_count % 2 != 0:
        text += '*'  # Close incomplete bold/italic
    
    # Handle incomplete links or formatting
    if text.count('[') > text.count(']'):
        text += ']'
    
    if text.count('(') > text.count(')'):
        text += ')'
    
    return text

# Default system message with modern, professional tone
DEFAULT_SYSTEM_MESSAGE: Dict[str, str] = {
    "role": "assistant",
    "content": (
        "I'm your advanced AI assistant, designed to provide helpful, accurate, and thoughtful responses. "
        "I can assist with a wide range of tasks including answering questions, creating content, "
        "analyzing information, and engaging in meaningful conversations. I'm continuously learning "
        "and improving to better serve your needs. How may I assist you today?"
    )
}

async def aires(client: Client, message: Message) -> None:
    """
    Handle user messages and generate AI responses
    
    Args:
        client: Pyrogram client instance
        message: Message from the user
    """
    try:
        await client.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)
        temp = await message.reply_text("⏳")
        user_id = message.from_user.id
        ask = message.text
        
        # Access MongoDB collection through the DatabaseService
        history_collection = get_history_collection()
        
        # Fetch user history from MongoDB
        user_history = history_collection.find_one({"user_id": user_id})
        if user_history:
            history = user_history['history']
        else: 
            history = [DEFAULT_SYSTEM_MESSAGE]

        # Add the new user query to the history
        history.append({"role": "user", "content": ask})

        # Use non-streaming approach for all chats to avoid flood control
        await client.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)
        
        # Use non-streaming approach
        ai_response = get_response(history)
        
        # Add the AI response to the history
        history.append({"role": "assistant", "content": ai_response})
        
        # Update the user's history in MongoDB
        history_collection.update_one(
            {"user_id": user_id},
            {"$set": {"history": history}},
            upsert=True
        )
        
        # Edit the temporary message with the AI response
        await temp.edit_text(ai_response)
        await user_log(client, message, "\nUser: "+ ask + ".\nAI: "+ ai_response)

    except Exception as e:
        await message.reply_text(f"An error occurred: {e}")
        print(f"Error in aires function: {e}")

async def new_chat(client: Client, message: Message) -> None:
    """
    Reset a user's chat history
    
    Args:
        client: Pyrogram client instance
        message: Message from the user
    """
    try:
        user_id = message.from_user.id
        
        # Access MongoDB collection through the DatabaseService
        history_collection = get_history_collection()
        
        # Delete user history from MongoDB
        history_collection.delete_one({"user_id": user_id})

        # Send confirmation message with modern UI
        await message.reply_text("🔄 **Conversation Reset**\n\nYour chat history has been cleared. Ready for a fresh conversation!")

    except Exception as e:
        await message.reply_text(f"Error clearing chat history: {e}")
        print(f"Error in new_chat function: {e}") 