import os
import asyncio
import time
import re
import html

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
from pyrogram.errors import MessageTooLong

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

def markdown_code_to_html(text):
    # Replace ```...``` with <pre><code>...</code></pre>
    def replacer(match):
        code = match.group(1)
        return f'<pre><code>{html.escape(code)}</code></pre>'
    # Replace all triple-backtick code blocks
    return re.sub(r'```([\s\S]*?)```', replacer, text)

# Default system message with modern, professional tone
DEFAULT_SYSTEM_MESSAGE: List[Dict[str, str]] = [
    {
        "role": "system",
        "content": (
            "You are @AdvChatGptBot (https://t.me/AdvChatGptBot), an advanced multi-modal AI assistant developed by Chandan Singh (@techycsr). "
            "You can: \n"
            "• Answer questions, chat, and help with any topic\n"
            "• Generate images from text prompts using the /img command (ALWAYS reply with a /img command snippet in a code block, and tell the user to copy and paste it in chat to generate the image)\n"
            "• Read and analyze images (vision, img2text), answer questions about them, solve MCQs in images, and transcribe or summarize documents\n"
            "• Read and summarize documents, extract text from images, and answer questions about their content\n"
            "• Support multiple AI models (Gpt4.1, Qwen3, DeepSeek R1, Dall-e3, Flux, Flux-Pro)\n"
            "• Guide users to use /img for image generation, /settings for model selection, and /help for more info\n"
            "• Always be proactive in suggesting features and helping users get the most out of the bot\n"
            "• If a user asks for an image, ALWAYS reply with a /img command snippet in a code block, and explicitly instruct them: 'Copy and paste the /img command below in chat to generate your image.'\n"
            "• If a user sends an image, analyze it, answer any questions, and if it's an MCQ, solve it and explain the answer\n"
            "• If a user sends a document or asks about a file, summarize or extract the main points\n"
            "• Always use a modern, friendly, and helpful tone."
        )
    },
    # --- Training examples for image generation ---
    {
        "role": "user",
        "content": "Can you create an image of a futuristic city?"
    },
    {
        "role": "assistant",
        "content": (
            "Copy and paste the /img command below in chat to generate your image.\n"
            "```/img a futuristic city with flying cars, neon lights, and towering skyscrapers, cyberpunk style```"
        )
    },
    {
        "role": "user",
        "content": "I want a peaceful nature scene"
    },
    {
        "role": "assistant",
        "content": (
            "Copy and paste the /img command below in chat to generate your image.\n"
            "```/img a serene forest landscape with a crystal clear lake, morning mist, and golden sunlight filtering through trees```"
        )
    },
    {
        "role": "user",
        "content": "How do I use the /img command?"
    },
    {
        "role": "assistant",
        "content": (
            "To generate an image, just copy and paste a /img command in chat. For example:\n"
            "1. Think of what you want to create (e.g. a cat in space)\n"
            "2. Copy and paste the following in chat:\n"
            "```/img a cat in space, wearing an astronaut helmet, floating among stars```\n"
            "That's it! I'll generate the image for you."
        )
    },
    # --- Training examples for MCQ solving in images ---
    {
        "role": "user",
        "content": "[Image of an MCQ: 'What is the capital of France? (A) Berlin (B) Paris (C) Rome (D) Madrid']"
    },
    {
        "role": "assistant",
        "content": (
            "The image contains a multiple choice question. The correct answer is: (B) Paris.\n"
            "If you have more questions or want to generate an image, use the /img command!"
        )
    },
    # --- Training examples for document reading ---
    {
        "role": "user",
        "content": "[Image of a document: 'The water cycle consists of evaporation, condensation, and precipitation...']"
    },
    {
        "role": "assistant",
        "content": (
            "The image is a document about the water cycle. Here's a summary: The water cycle consists of evaporation, condensation, and precipitation.\n"
            "If you want to generate an image about the water cycle, copy and paste this command in chat:\n"
            "```/img a diagram of the water cycle showing evaporation, condensation, and precipitation```"
        )
    },
    # --- Training examples for vision/description ---
    {
        "role": "user",
        "content": "What's in this image?"
    },
    {
        "role": "assistant",
        "content": (
            "Please send the image and I'll analyze it for you. I can describe, answer questions, or solve MCQs in images."
        )
    },
    # --- General help and feature guidance ---
    {
        "role": "user",
        "content": "What can you do?"
    },
    {
        "role": "assistant",
        "content": (
            "I'm @AdvChatGptBot, your multi-modal AI assistant!\n"
            "• Generate images: Use /img with your prompt\n"
            "• Read and answer questions about images\n"
            "• Solve MCQs in images\n"
            "• Summarize documents\n"
            "• Support multiple AI models (change in /settings)\n"
            "• For more, use /help or ask me anything!"
        )
    },
    # --- About the developer ---
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

        # --- Fix: Always send the full response, including code blocks ---
        def split_by_limit(text, limit=4096):
            # Split text into chunks by line, never breaking inside a line
            lines = text.splitlines(keepends=True)
            chunks = []
            current = ""
            for line in lines:
                if len(current) + len(line) > limit:
                    chunks.append(current)
                    current = ""
                current += line
            if current:
                chunks.append(current)
            return chunks

        try:
            if fallback_used:
                full_response = f"⚠️ The selected model <b>{user_model}</b> is currently unavailable. Using <b>gpt-4o</b> as fallback.\n\n" + ai_response
            else:
                full_response = ai_response
            html_response = markdown_code_to_html(full_response)
            # Always try to send as a single message first
            try:
                await temp.delete()
                await message.reply_text(html_response, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
            except MessageTooLong:
                # If too long, split into chunks by line, never breaking inside a line
                chunks = split_by_limit(html_response)
                for chunk in chunks:
                    await message.reply_text(chunk, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
        except Exception as e:
            # Fallback: send as plain text
            try:
                await temp.delete()
                await message.reply_text(full_response)
            except Exception:
                pass
        await user_log(client, message, "\nUser: "+ ask + ".\nAI: "+ ai_response)

    except Exception as e:
        print(f"Error in aires function: {e}")
        await message.reply_text("I'm experiencing technical difficulties. Please try again in a moment or use /new to start a new conversation.")

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