import os
from pymongo import MongoClient
from config import DATABASE_URL

client = MongoClient(DATABASE_URL)
db = client['aibotdb']
users_collection = db['users']


def check_and_add_user(user_id):
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        users_collection.insert_one({"user_id": user_id, "user_type": "user"})
        print(f"New User ID {user_id} was added to the users collection.")

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



block_users_collection = db['blocked_users']

def check_and_add_blocked_user(user_id):
    user = block_users_collection.find_one({"user_id": user_id})
    if not user:
        users_collection.insert_one({"user_id": user_id})
        print(f"User ID {user_id} was added to the blocked users collection.")

#get all user ids and send one message to all users one by one

# async def get_user_ids_message(client, message, text):
#     user_ids = users_collection.distinct("user_id")
#     reply.send_message(us

#     for user_id in user_ids:
#         try:
#             client.send_message(user_id, text)
#         except Exception as e:
#             print(f"Error sending message to user ID {user_id}: {e}")