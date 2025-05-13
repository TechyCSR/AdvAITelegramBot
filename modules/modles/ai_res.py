import os
from pymongo import MongoClient
from pyrogram import Client, filters, enums
from g4f.client import Client as GPTClient
from config import DATABASE_URL
from modules.chatlogs import user_log
from modules.lang import get_ui_message, get_user_language


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

async def aires(client, message):
    try:
        user_id = message.from_user.id
        
        await client.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)
        temp = await message.reply_text(get_ui_message("typing", user_id))
        
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

        # Get the AI response
        ai_response = get_response(history)
        
        # Add the AI response to the history
        history.append({"role": "assistant", "content": ai_response})

        # Update the user's history in MongoDB
        history_collection.update_one(
            {"user_id": user_id},
            {"$set": {"history": history}},
            upsert=True
        )

        # edit to the user's message with the AI response
        await temp.edit_text(ai_response)
        await user_log(client, message, "\nUser: "+ ask + ".\nAI: "+ ai_response)

    except Exception as e:
        error_msg = get_ui_message("ai_processing_error", user_id)
        await message.reply_text(f"{error_msg}: {e}")
        print(f"Error in aires function: {e}")

async def new_chat(client, message):
    try:
        user_id = message.from_user.id
        # Delete user history from MongoDB
        history_collection.delete_one({"user_id": user_id})

        # Send confirmation message to the user
        await message.reply_text(get_ui_message("new_chat_started", user_id))

    except Exception as e:
        error_msg = get_ui_message("clear_history_error", user_id)
        if error_msg == "clear_history_error":
            error_msg = "An error occurred while clearing chat history"
        await message.reply_text(f"{error_msg}: {e}")
        print(f"Error in new_chat function: {e}")


