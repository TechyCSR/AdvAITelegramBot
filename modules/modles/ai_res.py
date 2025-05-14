import os
import asyncio
import time
import re
from pymongo import MongoClient
from pyrogram import Client, filters, enums
from g4f.client import Client as GPTClient
from config import DATABASE_URL
from modules.chatlogs import user_log


mongo_client = MongoClient(DATABASE_URL)

# Access or create the database and collection
db = mongo_client['aibotdb']
history_collection = db['history']

# Initialize the GPT client with a more efficient provider
gpt_client = GPTClient(provider="PollinationsAI")

def get_response(history):  
    try:
        response = gpt_client.chat.completions.create(
            model="gpt-4o",  # Using more capable model for higher quality responses
            messages=history
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating response: {e}")
        return "I'm experiencing technical difficulties. Please try again in a moment."

def get_streaming_response(history):
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

def sanitize_markdown(text):
    """
    Ensures proper markdown formatting in streaming responses
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
DEFAULT_SYSTEM_MESSAGE = {
    "role": "assistant",
    "content": (
        "I'm your advanced AI assistant, designed to provide helpful, accurate, and thoughtful responses. "
        "I can assist with a wide range of tasks including answering questions, creating content, "
        "analyzing information, and engaging in meaningful conversations. I'm continuously learning "
        "and improving to better serve your needs. How may I assist you today?"
    )
}

async def aires(client, message):
    try:
        await client.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)
        temp = await message.reply_text("⏳")
        user_id = message.from_user.id
        ask = message.text
        
        # Fetch user history from MongoDB
        user_history = history_collection.find_one({"user_id": user_id})
        if user_history:
            history = user_history['history']
        else: 
            history = [DEFAULT_SYSTEM_MESSAGE]

        # Add the new user query to the history
        history.append({"role": "user", "content": ask})

        # Get streaming response
        streaming_response = get_streaming_response(history)
        
        if streaming_response:
            # Initialize variables for accumulated response
            complete_response = ""
            buffer = ""
            last_update_time = time.time()
            
            # Optimized update intervals for smoother streaming experience
            base_update_interval = 0.1  # Faster initial updates
            min_chars_per_update = 15  # Increased minimum characters before updating
            typing_action_interval = 2.0  # Show typing action more frequently
            last_typing_action = time.time()
            
            # Track if we're in a code block to handle formatting properly
            in_code_block = False
            code_lang = ""
            
            try:
                # Process streaming response chunks
                for chunk in streaming_response:
                    # Maintain typing indicator
                    current_time = time.time()
                    if current_time - last_typing_action >= typing_action_interval:
                        await client.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)
                        last_typing_action = current_time
                    
                    if hasattr(chunk, 'choices') and chunk.choices:
                        choice = chunk.choices[0]
                        if hasattr(choice, 'delta') and choice.delta:
                            if hasattr(choice.delta, 'content') and choice.delta.content:
                                # Add new content to buffer and complete response
                                new_content = choice.delta.content
                                buffer += new_content
                                complete_response += new_content
                                
                                # Check for code block markers to track formatting
                                if '```' in new_content:
                                    in_code_block = not in_code_block
                                    if in_code_block and len(new_content.split('```')) > 1:
                                        code_lang = new_content.split('```')[1].strip()
                                
                                # Adaptive update interval based on response length with improved dynamics
                                update_interval = base_update_interval + (len(complete_response) / 5000)
                                update_interval = min(update_interval, 0.8)  # Cap at 0.8 second
                                
                                # Update message if enough time has passed or buffer is large enough
                                current_time = time.time()
                                if (current_time - last_update_time >= update_interval or 
                                    len(buffer) >= min_chars_per_update):
                                    try:
                                        # Apply markdown sanitization to ensure proper rendering
                                        display_text = sanitize_markdown(complete_response)
                                        
                                        # Store previous text to compare and avoid MESSAGE_NOT_MODIFIED errors
                                        prev_message_text = getattr(temp, 'text', '')
                                        
                                        # Only update if content has actually changed
                                        if display_text != prev_message_text:
                                            await temp.edit_text(display_text)
                                            # Store the new text for future comparisons
                                            temp.text = display_text
                                        
                                        buffer = ""
                                        last_update_time = current_time
                                    except Exception as edit_error:
                                        # Ignore MESSAGE_NOT_MODIFIED errors
                                        if "MESSAGE_NOT_MODIFIED" not in str(edit_error):
                                            print(f"Edit error (will continue): {edit_error}")
                
                # Final update with complete text
                if complete_response:
                    try:
                        final_text = complete_response + " "
                        
                        # Only update if content has actually changed
                        prev_message_text = getattr(temp, 'text', '')
                        if final_text != prev_message_text:
                            await temp.edit_text(final_text)
                    except Exception as final_edit_error:
                        if "MESSAGE_NOT_MODIFIED" not in str(final_edit_error):
                            print(f"Final edit error: {final_edit_error}")
                
            except Exception as stream_error:
                print(f"Streaming error: {stream_error}")
                # If streaming fails mid-way, make sure we have the response so far
                if complete_response:
                    try:
                        final_text = complete_response + " "
                        
                        # Only update if content has actually changed
                        prev_message_text = getattr(temp, 'text', '')
                        if final_text != prev_message_text:
                            await temp.edit_text(final_text)
                    except Exception as recovery_error:
                        if "MESSAGE_NOT_MODIFIED" not in str(recovery_error):
                            print(f"Recovery edit error: {recovery_error}")
                    
            # Add the AI response to the history
            history.append({"role": "assistant", "content": complete_response})
            
            # Update the user's history in MongoDB
            history_collection.update_one(
                {"user_id": user_id},
                {"$set": {"history": history}},
                upsert=True
            )
            
            await user_log(client, message, "\nUser: "+ ask + ".\nAI: "+ complete_response)
        else:
            # Fallback to non-streaming method if streaming fails
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

async def new_chat(client, message):
    try:
        user_id = message.from_user.id
        # Delete user history from MongoDB
        history_collection.delete_one({"user_id": user_id})

        # Send confirmation message with modern UI
        await message.reply_text("🔄 **Conversation Reset**\n\nYour chat history has been cleared. Ready for a fresh conversation!")

    except Exception as e:
        await message.reply_text(f"Error clearing chat history: {e}")
        print(f"Error in new_chat function: {e}")


