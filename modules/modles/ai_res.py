import os
import asyncio
import time
import re
 from pyrogram import Client, filters, enums
efrom modules.chatlogs import user_log


mongo_client = MongoClient(DATABASE_URL)

# Access or create the database and collection
db = mongo_client['aibotdb']
history_collection = db['history']

# Initialize the GPT-4 client
gpt_client = GPTClient(provider="PollinationsAI")

def get_response(history):  
    try:
        response = gpt_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=history
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating response: {e}")
        return "I'm having trouble generating a response right now. Please try again later."

def get_streaming_response(history):
    try:
        # Stream parameter set to True to get response chunks
        response = gpt_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=history,
            stream=True
        )
        return response
    except Exception as e:
        print(f"Error generating streaming response: {e}")
        return None

def sanitize_markdown(text):
    """
    Fixes incomplete markdown elements to ensure the message renders properly
    even during partial streaming updates.
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

async def aires(client, message):
    try:
        await client.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)
        temp = await message.reply_text("...")
        user_id = message.from_user.id
        ask = message.text
        
        # Fetch user history from MongoDB
        user_history = history_collection.find_one({"user_id": user_id})
        if user_history:
            history = user_history['history']
        else: 
            history = [
    {
        "role": "assistant",
        "content": (
            "I am an AI chatbot assistant, developed by CHANDAN SINGH(i.e.@TechyCSR) and a his dedicated team of students from Lovely Professional University (LPU). "
            "Our core team also includes Ankit and Aarushi. who have all worked together to create a bot that facilitates user tasks and "
            "improves productivity in various ways. Our goal is to make interactions smoother and more efficient, providing accurate and helpful "
            "responses to your queries. The bot leverages the latest advancements in AI technology to offer features such as speech-to-text, "
            "text-to-speech, image generation, and more. Our mission is to continuously enhance the bot's capabilities, ensuring it meets the "
            "growing needs of our users. The current version is V-2.O, which includes significant improvements in response accuracy and speed, "
            "as well as a more intuitive user interface. We aim to provide a seamless and intelligent chat experience, making the AI assistant a "
            "valuable tool for users across various domains. To Reach out Chandan Singh, you can contact him on techycsr.me or on his email csr.info.in@gmail.com."
        )
    }
]

        # Add the new user query to the history
        history.append({"role": "user", "content": ask})

        # Get streaming response
        streaming_response = get_streaming_response(history)
        
        if streaming_response:
            # Initialize variables for accumulated response
            complete_response = ""
            buffer = ""
            last_update_time = time.time()
            
            # Dynamic update interval - start faster, then slow down as response grows
            base_update_interval = 0.2
            min_chars_per_update = 10  # Minimum characters before updating
            typing_action_interval = 3.0  # Show typing action every 3 seconds
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
                                
                                # Calculate dynamic update interval based on response length
                                update_interval = base_update_interval + (len(complete_response) / 2000)
                                update_interval = min(update_interval, 1.0)  # Cap at 1 second
                                
                                # Update message if enough time has passed or buffer is large enough
                                current_time = time.time()
                                if (current_time - last_update_time >= update_interval or 
                                    len(buffer) >= min_chars_per_update):
                                    try:
                                        # Apply markdown sanitization to ensure proper rendering
                                        display_text = sanitize_markdown(complete_response)
                                        await temp.edit_text(display_text)
                                        buffer = ""
                                        last_update_time = current_time
                                    except Exception as edit_error:
                                        print(f"Edit error (will continue): {edit_error}")
                
                # Final update with complete text
                if complete_response:
                    await temp.edit_text(complete_response)
                
            except Exception as stream_error:
                print(f"Streaming error: {stream_error}")
                # If streaming fails mid-way, make sure we have the response so far
                if complete_response:
                    await temp.edit_text(complete_response)
                    
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

        # Send confirmation message to the user
        await message.reply_text("Your chat history has been cleared. You can start a new conversation now.")

    except Exception as e:
        await message.reply_text(f"An error occurred while clearing chat history: {e}")
        print(f"Error in new_chat function: {e}")


