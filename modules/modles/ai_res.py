import os
from pymongo import MongoClient
from dotenv import load_dotenv
from pyrogram import Client, filters
from g4f.client import Client as GPTClient
from config import DATABASE_URL


# Get the MongoDB URI from environment variables
MONGO_URI = os.getenv("MONGO_URI")

# Initialize the MongoDB client
mongo_client = MongoClient(DATABASE_URL)

# Access or create the database and collection
db = mongo_client['aibotdb']
history_collection = db['history']

# Initialize the GPT-4 client
gpt_client = GPTClient(provider="Liaobots")

def get_response(history):
    response = gpt_client.chat.completions.create(
        model="gpt-4o",
        messages=history
    )
    return response.choices[0].message.content

async def aires(client, message):
    user_id = message.from_user.id
    user_mention = message.from_user.mention
    ask = message.text

    # Fetch user history from MongoDB
    user_history = history_collection.find_one({"user_id": user_id})
    if user_history:
        history = user_history['history']
    else:
        history = [{"role": "assistant", "content": "I am a chatbot assistant, designed to help you with your queries. Developed by @AdvanceAIBot Team, Core developer @TechyCSR (https://techycsr.tech). Current Version v1.02Beta"}]

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

    # Reply to the user's message with the AI response
    await message.reply_text(ai_response)


