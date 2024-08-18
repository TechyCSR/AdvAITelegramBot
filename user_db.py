import os
from pymongo import MongoClient
from config import DATABASE_URL
from jwt_ import create_jwt, verify_jwt 
from cryptography import encrypt_message, decrypt_message

# Initialize the MongoDB client
client = MongoClient(DATABASE_URL)
db = client['aibotdb']
users_collection = db['users']
block_users_collection = db['blocked_users']

def authenticate_user(token):
    user_id = verify_jwt(token)
    if user_id:
        print(f"User {user_id} authenticated successfully.")
        return user_id
    else:
        print("Authentication failed.")
        return None

def check_and_add_user(user_id):
    encrypted_user_id = encrypt_message(user_id)
    user = users_collection.find_one({"user_id": encrypted_user_id})
    if not user:
        users_collection.insert_one({"user_id": user_id, "user_type": "user"})
        print(f"New User ID {user_id} was added to the users collection.")

def drop_user_id(user_id):
    """Remove a specific user ID from the users collection."""
    user_ids_encrypted = users_collection.distinct("user_id")
    result = users_collection.delete_one({"user_id": encrypted_user_id})
    if result.deleted_count == 1:
        print(f"User ID {user_id} was successfully deleted.")



def get_user_ids():
    """Retrieve all user IDs from the users collection."""
    user_ids = users_collection.distinct("user_id")
    user_ids_decrypted = [decrypt_message(uid) for uid in user_ids_encrypted]
    return user_ids_decrypted


block_users_collection = db['blocked_users']

def check_and_add_blocked_user(user_id):
    encrypted_user_id = encrypt_message(user_id)  # Encrypt user_id before storing
    user = block_users_collection.find_one({"user_id": encrypted_user_id})
    
    if not user:
        block_users_collection.insert_one({"user_id": encrypted_user_id})
        print(f"User ID {user_id} was added to the blocked users collection (encrypted).")
