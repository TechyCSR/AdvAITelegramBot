import asyncio
import time
from google.generativeai import genai  # Fixed import statement
from google.generativeai.types import GenerateVideosConfig
from google.cloud import storage
from database import user_db
from threading import Lock

# Configurable pricing
TOKEN_PRICE_RS = 9  # Rs 9 for 10 tokens
TOKENS_PER_VIDEO = 10
VIDEO_LENGTH_SECONDS = 8

# In-memory lock to ensure one video per user at a time
user_video_locks = {}
user_video_locks_lock = Lock()

def get_user_lock(user_id):
    with user_video_locks_lock:
        if user_id not in user_video_locks:
            user_video_locks[user_id] = asyncio.Lock()
        return user_video_locks[user_id]

# Token management
async def get_user_tokens(user_id):
    users_collection = user_db.get_user_collection()
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        users_collection.insert_one({"user_id": user_id, "video_tokens": 0})
        return 0
    return user.get("video_tokens", 0)

async def add_user_tokens(user_id, tokens):
    users_collection = user_db.get_user_collection()
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        users_collection.insert_one({"user_id": user_id, "video_tokens": tokens})
    else:
        users_collection.update_one({"user_id": user_id}, {"$inc": {"video_tokens": tokens}})

async def remove_user_tokens(user_id, tokens):
    users_collection = user_db.get_user_collection()
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        users_collection.insert_one({"user_id": user_id, "video_tokens": 0})
        return False
    if user.get("video_tokens", 0) < tokens:
        return False
    users_collection.update_one({"user_id": user_id}, {"$inc": {"video_tokens": -tokens}})
    return True

# Video generation logic
async def generate_video_for_user(user_id, prompt, output_gcs_uri):
    lock = get_user_lock(user_id)
    async with lock:
        tokens = await get_user_tokens(user_id)
        if tokens < TOKENS_PER_VIDEO:
            return None, "You need at least 10 tokens to generate a video."
        # Deduct tokens first to prevent double spending
        if not await remove_user_tokens(user_id, TOKENS_PER_VIDEO):
            return None, "Failed to deduct tokens. Please try again."
        client = genai.Client()
        start_time = time.time()
        try:
            operation = client.models.generate_videos(
                model="veo-3.0-generate-preview",
                prompt=prompt,
                config=GenerateVideosConfig(
                    aspect_ratio="16:9",
                    output_gcs_uri=output_gcs_uri,
                ),
            )
            while not operation.done:
                await asyncio.sleep(15)
                operation = client.operations.get(operation)
            total_time = time.time() - start_time
            if operation.response:
                video_uri = operation.result.generated_videos[0].video.uri
                # Download the video from GCS and save locally
                import re
                match = re.match(r'gs://([^/]+)/(.+)', video_uri)
                if match:
                    bucket_name, blob_name = match.groups()
                    storage_client = storage.Client()
                    bucket = storage_client.bucket(bucket_name)
                    blob = bucket.blob(blob_name)
                    local_path = f'generated_images/generated_video_{user_id}.mp4'
                    blob.download_to_filename(local_path)
                    return (local_path, total_time)
                else:
                    return (None, "Failed to parse GCS URI.")
            else:
                return (None, "Video generation failed.")
        except Exception as e:
            # Refund tokens on failure
            await add_user_tokens(user_id, TOKENS_PER_VIDEO)
            return (None, f"Error: {str(e)}") 