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
from modules.maintenance import maintenance_check, maintenance_message, is_feature_enabled
from modules.user.ai_model import get_user_ai_models, DEFAULT_TEXT_MODEL, RESTRICTED_TEXT_MODELS
from modules.user.premium_management import is_user_premium
from config import ADMINS

# --- Provider mapping ---
PROVIDER_MAP = {
    "gpt-4o": "PollinationsAI",
    "gpt-4.1": "PollinationsAI",
    "qwen3": "DeepInfraChat",
    "deepseek-r1": "DeepInfraChat"
}

# --- Model mapping for DeepInfraChat ---
DEEPINFRA_MODEL_MAP = {
    "qwen3": "Qwen/Qwen3-235B-A22B",
    "deepseek-r1": "deepseek-r1"
}

# Initialize the GPT client with a more efficient provider
gpt_client = GPTClient(provider="PollinationsAI")

def get_response(history: List[Dict[str, str]], model: str = "gpt-4o", provider: str = "PollinationsAI") -> str:
    """
    Get a non-streaming response from the AI model
    
    Args:
        history: Conversation history in the format expected by the AI model
        model: The model to use for generating the response
        provider: The provider to use for generating the response
        
    Returns:
        String response from the AI model
    """
    try:
        if not isinstance(history, list):
            history = [history]
        if not history:
            history = DEFAULT_SYSTEM_MESSAGE.copy()
        for i, msg in enumerate(history):
            if not isinstance(msg, dict):
                history[i] = {"role": "user", "content": str(msg)}
        gpt_client = GPTClient()
        if provider == "PollinationsAI":
            print(f"Using PollinationsAI model: {model}")
            response = gpt_client.chat.completions.create(
                model=model,
                messages=history,
                provider="PollinationsAI"
            )
            return response.choices[0].message.content
        elif provider == "DeepInfraChat":
            deep_model = DEEPINFRA_MODEL_MAP.get(model, model)
            print(f"Using DeepInfraChat model: {deep_model}")
            response = gpt_client.chat.completions.create(
                model=deep_model,
                messages=history,
                provider="DeepInfraChat"
            )
            return response.choices[0].message.content
        else:
            # fallback to default
            response = gpt_client.chat.completions.create(
                model="gpt-4o",
                messages=history,
                provider="PollinationsAI"
            )
            return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating response: {e}")
        raise

def get_streaming_response(history: List[Dict[str, str]]) -> Optional[Generator]:
    """
    Get a streaming response from the AI model
    
    Args:
        history: Conversation history in the format expected by the AI model
        
    Returns:
        Generator yielding response chunks or None if there's an error
    """
    try:
        # Ensure history is a list
        if not isinstance(history, list):
            history = [history]
            
        # If history is empty, use the default system message
        if not history:
            history = DEFAULT_SYSTEM_MESSAGE.copy()  # Create a copy to avoid modifying the original
            
        # Ensure each message in history is a dictionary
        for i, msg in enumerate(history):
            if not isinstance(msg, dict):
                history[i] = {"role": "user", "content": str(msg)}
                
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
DEFAULT_SYSTEM_MESSAGE: List[Dict[str, str]] = [
    {
        "role": "system",
        "content": (
            "I'm your advanced AI assistant (**@AdvChatGptBot**), Multi-Model AI Chatbot(Gpt4.1,Qwen3,DeepSeek R1,Img Gen : Dall-e3,Flux & Flux-Pro), designed to provide helpful, accurate, and thoughtful responses. "
            "I can assist with a wide range of tasks including answering questions, creating content, "
            "analyzing information, and engaging in meaningful conversations. I'm continuously learning "
            "and improving to better serve your needs. This bot was developed by Chandan Singh (@techycsr)."
        )
    },
    {
        "role": "assistant",
        "content": (
            "🎨 **Image Generation**\n"
            "I can help you generate images using the /img command. Here are some example conversations:\n\n"
            "Example 1:\n"
            "User: Can you create an image of a futuristic city?\n"
            "Assistant: I'll help you generate that image. Here's the command:\n"
            "```\n/img a futuristic city with flying cars, neon lights, and towering skyscrapers, cyberpunk style\n```\n"
            "Just copy and paste this command to generate your image.\n\n"
            "Example 2:\n"
            "User: I want a peaceful nature scene\n"
            "Assistant: Here's a command to create a peaceful nature scene:\n"
            "```\n/img a serene forest landscape with a crystal clear lake, morning mist, and golden sunlight filtering through trees\n```\n\n"
            "You can use these commands directly:\n"
            "• `/img [prompt]` - Generate images\n"
            "• `/generate [prompt]` - Alternative command\n\n"
            "💡 **Tips for Better Images**:\n"
            "• Be specific about details, lighting, and perspective\n"
            "• Include artistic style preferences\n"
            "• Mention colors and mood\n\n"
            "Just copy and paste the command in my chat to generate your image."
        )
    },
    {
        "role": "user",
        "content": "Can you create an image of a futuristic city?"
    },
    {
        "role": "assistant",
        "content": "I'll help you generate that image. Here's the command:\n```\n/img a futuristic city with flying cars, neon lights, and towering skyscrapers, cyberpunk style\n```\nJust copy and paste this command in chat to generate your image."
    },
    {
        "role": "user",
        "content": "I want a peaceful nature scene"
    },
    {
        "role": "assistant",
        "content": "Here's a command to create a peaceful nature scene:\n```\n/img a serene forest landscape with a crystal clear lake, morning mist, and golden sunlight filtering through trees\n```\nJust copy and paste this command in chat to generate your image."
    },
    {
        "role": "user",
        "content": "What commands are available?"
    },
    {
        "role": "assistant",
        "content": (
            "🤖 **Available Commands**\n\n"
            "• `/start` - Start the bot and get welcome message\n"
            "• `/help` - Show this help menu\n"
            "• `/img [prompt]` - Generate images from text descriptions\n"
            "• `/generate [prompt]` - Alternative image generation command\n"
            "• `/new` - Start a new conversation and update the bot to the latest version\n"
            "• `/settings` - Change your settings\n"
            "• `/benefits` - Show the benefits of the premium subscription\n"
            "💡 **Tips**:\n"
            "• You can chat with me naturally\n"
            "• Ask me to generate images by describing what you want\n"
            "• Use /new to clear our conversation history\n"
            "• For more options, use /settings, or contact @techycsr on Telegram"
        )
    },
    {
        "role": "user",
        "content": "How to change AI model for image generation or text responses?"
    },
    {
        "role": "assistant",
        "content":"/start --> settings --> AI Model Panel to change the  AI model for image generation or text responses."


    },
    {
        "role": "user",
        "content": "what's there in that image?"
    },
    {
        "role": "assistant",
        "content":"Looks like image context is not set. Please send the image again with your question."
    },
    {
        "role": "assistant",
        "content": (
            "👨‍💻 **About the Developer**\n\n"
            "This bot was created by Chandan Singh (@techycsr), a passionate tech enthusiast and student developer. "
            "He specializes in:\n"
            "• Python Development\n"
            "• AI/ML Applications\n"
            "• Telegram Bot Development\n"
            "• Open Source Projects\n\n"
            "🔗 **Connect with the Developer**:\n"
            "• Telegram: @techycsr\n"
            "• Website: techycsr.me\n"
            "• GitHub: github.com/techycsr\n\n"
            "• LinkedIn: linkedin.com/in/techycsr\n\n"
            "This bot is one of his many projects showcasing his expertise in AI and bot development."
        )
    },
    {
        "role": "system",
        "content": (
            "Remember: This bot was developed by Chandan Singh (@techycsr) as a demonstration of advanced AI "
            "capabilities in Telegram. For support or to learn more about the developer, visit techycsr.me "
            "or contact @techycsr on Telegram."
        )
    }
]

async def aires(client: Client, message: Message) -> None:
    """
    Handle user messages and generate AI responses
    
    Args:
        client: Pyrogram client instance
        message: Message from the user
    """
    if await maintenance_check(message.from_user.id) or not await is_feature_enabled("ai_response"):
        maint_msg = await maintenance_message(message.from_user.id)
        await message.reply(maint_msg)
        return

    try:
        await client.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)
        temp = await message.reply_text("⏳")
        user_id = message.from_user.id
        ask = message.text
        
        # Access MongoDB collection through the DatabaseService
        history_collection = get_history_collection()
        
        # Fetch user history from MongoDB
        user_history = history_collection.find_one({"user_id": user_id})
        if user_history and 'history' in user_history:
            # Ensure history is a list
            history = user_history['history']
            if not isinstance(history, list):
                history = [history]
        else: 
            # Use a copy of the default system message
            history = DEFAULT_SYSTEM_MESSAGE.copy()

        # Add the new user query to the history
        history.append({"role": "user", "content": ask})

        # Use non-streaming approach for all chats to avoid flood control
        await client.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)
        
        # --- Get user model ---
        user_model, _ = await get_user_ai_models(user_id)
        is_premium, _, _ = await is_user_premium(user_id)
        is_admin = user_id in ADMINS
        if not is_premium and not is_admin and user_model in RESTRICTED_TEXT_MODELS:
            user_model = DEFAULT_TEXT_MODEL
        provider = PROVIDER_MAP.get(user_model, "PollinationsAI")
        model_to_use = user_model
        fallback_used = False
        try:
            ai_response = get_response(history, model=model_to_use, provider=provider)
        except Exception as e:
            # fallback to gpt-4o
            fallback_used = True
            ai_response = get_response(history, model="gpt-4o", provider="PollinationsAI")
        
        # Add the AI response to the history
        history.append({"role": "assistant", "content": ai_response})
        
        # Update the user's history in MongoDB
        history_collection.update_one(
            {"user_id": user_id},
            {"$set": {"history": history}},
            upsert=True
        )
        
        if fallback_used:
            fallback_msg = f"⚠️ The selected model <b>{user_model}</b> is currently unavailable. Using <b>gpt-4o</b> as fallback."
            await temp.edit_text(fallback_msg + "\n\n" + ai_response, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
        else:
            await temp.edit_text(ai_response, disable_web_page_preview=True)
        await user_log(client, message, "\nUser: "+ ask + ".\nAI: "+ ai_response)

    except Exception as e:
        print(f"Error in aires function: {e}")
        await message.reply_text("I'm experiencing technical difficulties. Please try again in a moment.")

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
        
        # Create a new history entry with the default system message list
        history_collection.insert_one({
            "user_id": user_id,
            "history": DEFAULT_SYSTEM_MESSAGE
        })

        # Send confirmation message with modern UI
        await message.reply_text("🔄 **Conversation Reset**\n\nYour chat history has been cleared. Ready for a fresh conversation!")

    except Exception as e:
        await message.reply_text(f"Error clearing chat history: {e}")
        print(f"Error in new_chat function: {e}") 