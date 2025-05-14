import os
from pymongo import MongoClient
from config import DATABASE_URL
import asyncio

client = MongoClient(DATABASE_URL)
db = client['aibotdb']
users_collection = db['users']
user_lang_collection = db['user_lang']


#make it async

async def check_and_add_username(user_id, username):
    """Check if a username exists in the users collection, and add it if it doesn't."""
    user = users_collection.find_one({"user_id": user_id})
    if user:
        if "username" in user:
            if user["username"] == username:
                return
    users_collection.update_one({"user_id": user_id}, {"$set": {"username": username}})
    print(f"Username {username} was added to user ID {user_id}.")

    

async def check_and_add_user(user_id):
    """Check if a user ID exists in the users collection, and add it if it doesn't."""
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        users_collection.insert_one({"user_id": user_id})
        print(f"User ID {user_id} was added to the users collection.")

def drop_user_id(user_id):
    """Remove a specific user ID from the users collection."""
    result = users_collection.delete_one({"user_id": user_id})
    if result.deleted_count == 1:
        print(f"User ID {user_id} was successfully deleted.")



def get_user_ids():
    """Retrieve all user IDs from the users collection."""
    user_ids = users_collection.distinct("user_id")
    print(f"Retrieved {len(user_ids)} user IDs.")
    return user_ids

def get_user_language(user_id):
    """Get user's preferred language from database"""
    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
    if user_lang_doc:
        return user_lang_doc['language']
    return 'en'  # Default to English if not set


block_users_collection = db['blocked_users']

def check_and_add_blocked_user(user_id):
    user = block_users_collection.find_one({"user_id": user_id})
    if not user:
        users_collection.insert_one({"user_id": user_id})
        print(f"User ID {user_id} was added to the blocked users collection.")

#get all user ids and send one message to all users one by one

async def get_user_ids_message(bot, update, text):
    user_ids = users_collection.distinct("user_id")
    total=0
    await update.reply_text(f"Sending message to {len(user_ids)} users...")
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, text)
            await asyncio.sleep(0.05)
            total+=1
        except Exception as e:
            print(f"Error sending message to user ID {user_id}: {e}")
    await update.reply_text(f"Message sent to {total} users.")

#get all usernames from the users collection and send one message to all users one by one

async def get_usernames_message(bot, update, text):
    users = users_collection.find({"username": {"$exists": True}})
    total=0
    await update.reply_text(f"Sending message to users with usernames...")
    for user in users:
        try:
            # print(user["username"])
            await bot.send_message(user["username"], text)
            await asyncio.sleep(0.05)
            total+=1
        except Exception as e:
            print(f"Error sending message to user ID {user['user_id']}: {e}")
    await update.reply_text(f"Message sent to {total} users.")