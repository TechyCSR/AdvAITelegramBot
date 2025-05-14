import os
import asyncio
import logging
import time
import uuid
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Tuple
import requests
import io

from pyrogram import Client
from pyrogram.types import (
    InlineQuery, 
    InlineQueryResultPhoto, 
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineQueryResultCachedPhoto,
    InputMediaPhoto,
    Message
)
from pyrogram.errors import QueryIdInvalid, MessageNotModified

from ImgGenModel.g4f.client import Client as ImageClient
from ImgGenModel.g4f.Provider import PollinationsAI
from config import LOG_CHANNEL

# Get the logger
logger = logging.getLogger(__name__)

# Store ongoing inline image generations to prevent duplicates
# Format: {task_id: {"user_id": user_id, "prompt": prompt, "start_time": time}}
ongoing_generations = {}

# Store pending image generations and their messages
# Format: {task_id: {"user_id": user_id, "message": message_obj, "prompt": prompt}}
pending_generations = {}

# Image cache system - store generated images by user
# Format: {user_id: {"file_ids": [file_id1, file_id2...], "prompts": [prompt1, prompt2...], "timestamps": [time1, time2...]}}
image_cache = {}
MAX_CACHE_PER_USER = 5  # Maximum number of cached images per user

async def generate_inline_image(prompt: str) -> List[str]:
    """Generate images for inline query
    
    Args:
        prompt: The text prompt for image generation
        
    Returns:
        List of image URLs
    """
    logger.info(f"Generating inline image with prompt: '{prompt}'")
    
    # Enhanced prompt for realistic style by default
    enhanced_prompt = f"{prompt}, ultra realistic, detailed, photographic quality"
    logger.info(f"Enhanced inline prompt: '{enhanced_prompt}'")
    
    image_urls = []
    max_images = 1  # Only generate one image for inline queries to keep it fast
    
    # Try with PollinationsAI first, then fallback to default
    providers = ["PollinationsAI", None]
    
    for provider in providers:
        client = ImageClient()
        try:
            # Prepare provider configuration
            provider_obj = None
            model_name = "dall-e-3"  # Default model
            
            if provider == "PollinationsAI":
                try:
                    provider_obj = PollinationsAI
                    model_name = None  # PollinationsAI uses its own model
                    logger.info(f"Using PollinationsAI provider for inline query")
                except Exception as e:
                    logger.error(f"Failed to use PollinationsAI provider for inline: {str(e)}")
                    continue
            
            # Standard image size - smaller for inline to be faster
            width = 512
            height = 512
            
            # Prepare generation parameters
            generation_kwargs = {
                "prompt": enhanced_prompt,
                "n": max_images,
                "provider": provider_obj,
                "width": width,
                "height": height,
                "quality": "standard"
            }
            
            # Only add model parameter if specified
            if model_name:
                generation_kwargs["model"] = model_name
                
            # Generate with timeout
            logger.info(f"Sending inline generation request with provider {provider}")
            response = await asyncio.wait_for(
                client.images.async_generate(**generation_kwargs),
                timeout=25  # Timeout for inline queries
            )
            
            # Process response
            for image_data in response.data:
                image_urls.append(image_data.url)
                
            if image_urls:
                logger.info(f"Successfully generated {len(image_urls)} images for inline query")
                break
                
        except asyncio.TimeoutError:
            logger.warning(f"Inline image generation timed out with provider {provider}")
            continue
        except Exception as e:
            logger.error(f"Error generating inline image with provider {provider}: {str(e)}")
            continue
    
    # Process URLs to local paths - same method as in image_generation.py
    local_paths = []
    for url in image_urls:
        # Convert to local path
        if url.startswith("/images/"):
            # Ensure the directory exists
            os.makedirs("./generated_images", exist_ok=True)
            
            # Get the filename part
            filename = os.path.basename(url)
            local_path = f"./generated_images/{filename}"
            
            # For URLs from PollinationsAI that start with /images/,
            # the actual file is already saved in generated_images directory
            if os.path.exists(local_path):
                logger.info(f"Found existing local file at {local_path}")
                local_paths.append(local_path)
            else:
                # Try to download if not found
                try:
                    # Get the full URL
                    full_url = f"https://image.pollinations.ai{url}"
                    response = requests.get(full_url, timeout=10)
                    response.raise_for_status()
                    
                    # Save the image
                    with open(local_path, 'wb') as f:
                        f.write(response.content)
                    
                    logger.info(f"Downloaded image to {local_path}")
                    local_paths.append(local_path)
                except Exception as e:
                    logger.error(f"Failed to download image to {local_path}: {str(e)}")
        else:
            # For other URLs, try to download them
            unique_id = str(uuid.uuid4())
            local_path = f"./generated_images/inline_{unique_id}.jpg"
            
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"Downloaded image to {local_path}")
                local_paths.append(local_path)
            except Exception as e:
                logger.error(f"Failed to download image to {local_path}: {str(e)}")
    
    return local_paths

def create_task_id(user_id: int, prompt: str) -> str:
    """Create a unique task ID for the generation
    
    Args:
        user_id: User ID requesting the generation
        prompt: The prompt text
        
    Returns:
        A unique task ID string
    """
    unique_string = f"{user_id}:{prompt}:{time.time()}"
    task_id = hashlib.md5(unique_string.encode()).hexdigest()[:10]
    return task_id

def get_image_caption(prompt: str) -> str:
    """Get standard caption for generated images
    
    Args:
        prompt: The prompt used to generate the image
        
    Returns:
        Formatted caption with prompt and bot username
    """
    return f"🖼️ **AI Generated Image**\n\n📝 **Prompt**: `{prompt}`\n\n@AdvChatGptBot"

def get_cached_image(user_id: int, prompt: str = None) -> Optional[str]:
    """Get a cached image file_id for a user
    
    Args:
        user_id: The user ID
        prompt: Optional prompt to match (if None, return most recent image)
        
    Returns:
        File ID of cached image or None if not found
    """
    if user_id not in image_cache:
        return None
    
    user_cache = image_cache[user_id]
    
    if not user_cache["file_ids"]:
        return None
    
    # If no specific prompt requested, return the most recent image
    if prompt is None:
        return user_cache["file_ids"][0]  # Most recent is first
    
    # Try to find an exact match for the prompt
    for i, cached_prompt in enumerate(user_cache["prompts"]):
        if cached_prompt.lower() == prompt.lower():
            return user_cache["file_ids"][i]
    
    # No exact match, try to find a similar prompt (contains the same keywords)
    prompt_keywords = set(prompt.lower().split())
    best_match = None
    best_match_score = 0
    
    for i, cached_prompt in enumerate(user_cache["prompts"]):
        cached_keywords = set(cached_prompt.lower().split())
        common_keywords = prompt_keywords.intersection(cached_keywords)
        
        # Calculate match score based on common keywords
        if len(common_keywords) > best_match_score:
            best_match_score = len(common_keywords)
            best_match = user_cache["file_ids"][i]
    
    # Only return if there's a reasonable match (at least 3 common keywords)
    if best_match_score >= 3:
        return best_match
    
    # No good match, return the most recent image
    return user_cache["file_ids"][0]

def add_to_cache(user_id: int, file_id: str, prompt: str) -> None:
    """Add a generated image to the cache
    
    Args:
        user_id: The user ID
        file_id: The Telegram file_id
        prompt: The prompt used to generate the image
    """
    # Initialize user cache if not exists
    if user_id not in image_cache:
        image_cache[user_id] = {
            "file_ids": [],
            "prompts": [],
            "timestamps": []
        }
    
    user_cache = image_cache[user_id]
    
    # Check if we already have this prompt (to avoid duplicates)
    for i, cached_prompt in enumerate(user_cache["prompts"]):
        if cached_prompt.lower() == prompt.lower():
            # Replace with newer file_id
            user_cache["file_ids"][i] = file_id
            user_cache["timestamps"][i] = time.time()
            logger.info(f"Updated existing cache entry for user {user_id}, prompt: '{prompt}'")
            return
    
    # Add new image at the front (most recent first)
    user_cache["file_ids"].insert(0, file_id)
    user_cache["prompts"].insert(0, prompt)
    user_cache["timestamps"].insert(0, time.time())
    
    # Limit cache size
    if len(user_cache["file_ids"]) > MAX_CACHE_PER_USER:
        user_cache["file_ids"].pop()
        user_cache["prompts"].pop()
        user_cache["timestamps"].pop()
        
    logger.info(f"Added image to cache for user {user_id}, prompt: '{prompt}'")

def clear_user_cache(user_id: int) -> None:
    """Clear the cache for a specific user
    
    Args:
        user_id: The user ID to clear cache for
    """
    if user_id in image_cache:
        del image_cache[user_id]
        logger.info(f"Cleared cache for user {user_id}")

async def handle_inline_query(client: Client, inline_query: InlineQuery) -> None:
    """Handle inline queries for image generation
    
    This function processes inline queries and generates images when
    a prompt ends with a period to indicate it's complete.
    """
    query = inline_query.query.strip()
    user_id = inline_query.from_user.id
    query_id = inline_query.id
    
    # Check if the query is empty
    if not query:
        # Show instructions when query is empty
        try:
            await inline_query.answer(
                results=[
                    InlineQueryResultArticle(
                        title="Generate an image",
                        description="Type your prompt and end with a period (.) to generate an image",
                        input_message_content=InputTextMessageContent(
                            "To generate an image, type your prompt and end with a period (.).\n"
                            "Example: @YourBot beautiful landscape with mountains."
                        ),
                        thumb_url="https://img.icons8.com/color/452/picture.png"
                    )
                ],
                cache_time=1
            )
        except QueryIdInvalid:
            logger.warning(f"Query ID invalid for empty query from user {user_id}")
        except Exception as e:
            logger.error(f"Error answering empty inline query: {str(e)}")
        return
    
    # Check if the query ends with a period (indicating the prompt is complete)
    if not query.endswith("."):
        # Show waiting message
        try:
            await inline_query.answer(
                results=[
                    InlineQueryResultArticle(
                        title="Continue typing your prompt...",
                        description="End your prompt with a period (.) to generate",
                        input_message_content=InputTextMessageContent(
                            f"Your current prompt: {query}\n\n"
                            "Add a period (.) at the end when you're done to generate the image."
                        ),
                        thumb_url="https://img.icons8.com/color/452/hourglass.png"
                    )
                ],
                cache_time=1
            )
        except QueryIdInvalid:
            logger.warning(f"Query ID invalid for incomplete prompt from user {user_id}")
        except Exception as e:
            logger.error(f"Error answering incomplete inline query: {str(e)}")
        return
    
    # Remove the period from the end of the prompt
    prompt = query[:-1].strip()
    
    # If prompt is too short, ask for more detail
    if len(prompt) < 3:
        try:
            await inline_query.answer(
                results=[
                    InlineQueryResultArticle(
                        title="Prompt too short",
                        description="Please provide a more detailed prompt",
                        input_message_content=InputTextMessageContent(
                            "Your prompt is too short. Please provide more details for better results."
                        ),
                        thumb_url="https://img.icons8.com/color/452/high-importance.png"
                    )
                ],
                cache_time=1
            )
        except QueryIdInvalid:
            logger.warning(f"Query ID invalid for short prompt from user {user_id}")
        except Exception as e:
            logger.error(f"Error answering short prompt inline query: {str(e)}")
        return
    
    # Check for command to clear cache
    if prompt.lower() == "clear cache":
        clear_user_cache(user_id)
        try:
            await inline_query.answer(
                results=[
                    InlineQueryResultArticle(
                        title="Cache Cleared",
                        description="Your image cache has been cleared",
                        input_message_content=InputTextMessageContent(
                            "✅ Your image cache has been cleared. All new images will be freshly generated."
                        ),
                        thumb_url="https://img.icons8.com/color/452/delete.png"
                    )
                ],
                cache_time=1
            )
        except QueryIdInvalid:
            logger.warning(f"Query ID invalid for cache clear from user {user_id}")
        except Exception as e:
            logger.error(f"Error answering cache clear command: {str(e)}")
        return
    
    # Check for cached images first
    cached_file_id = get_cached_image(user_id, prompt)
    if cached_file_id:
        try:
            # Respond immediately with cached image
            await inline_query.answer(
                results=[
                    InlineQueryResultCachedPhoto(
                        photo_file_id=cached_file_id,
                        title=f"AI Generated Image",
                        description=prompt,
                        caption=get_image_caption(prompt)
                    )
                ],
                cache_time=3600  # Cache for an hour
            )
            logger.info(f"Answered query from user {user_id} with cached image for prompt: '{prompt}'")
            
            # Still trigger background generation to refresh the cache if user isn't
            # currently generating something else
            if not any(data["user_id"] == user_id for data in ongoing_generations.values()):
                # Generate a unique task ID for this request
                task_id = create_task_id(user_id, prompt)
                ongoing_generations[task_id] = {
                    "user_id": user_id,
                    "prompt": prompt,
                    "start_time": time.time(),
                    "is_cache_refresh": True
                }
                # Start background generation to refresh cache
                asyncio.create_task(generate_and_cache_image(client, user_id, prompt, task_id))
                
            return
        except Exception as e:
            logger.error(f"Error answering with cached image: {str(e)}")
            # Continue to generate new image if cached image failed
    
    # Check if there's an ongoing generation in progress for this user
    for task_id, data in ongoing_generations.items():
        if data["user_id"] == user_id and time.time() - data["start_time"] < 30:
            # Show waiting message
            try:
                await inline_query.answer(
                    results=[
                        InlineQueryResultArticle(
                            title="Still generating your image...",
                            description="Please wait, this can take a few seconds",
                            input_message_content=InputTextMessageContent(
                                f"Still generating your image for: {prompt}\n\n"
                                "⏳Please wait... Add space after every 5-7 seconds, if image is not generated."
                            ),
                            thumb_url="https://img.icons8.com/color/452/hourglass.png"
                        )
                    ],
                    cache_time=1
                )
            except QueryIdInvalid:
                logger.warning(f"Query ID invalid for ongoing generation message from user {user_id}")
            except Exception as e:
                logger.error(f"Error answering ongoing generation message: {str(e)}")
            return
    
    # Generate a unique task ID for this request
    task_id = create_task_id(user_id, prompt)
    
    # Store local paths for cleanup
    local_paths = []
    
    # Start the immediate generation
    try:
        # Store this query in ongoing generations
        ongoing_generations[task_id] = {
            "user_id": user_id,
            "prompt": prompt,
            "start_time": time.time(),
            "query_id": query_id,
            "inline_query": inline_query
        }
        
        # Show initial "generating" message
        await inline_query.answer(
            results=[
                InlineQueryResultArticle(
                    title="🎨 Generating your image...",
                    description=f"Prompt: {prompt}\n⏳Please wait... Add space after every 5-7 seconds, if image is not generated.",
                    input_message_content=InputTextMessageContent(
                        f"🖼️ **Generating Image**\n\n📝 **Prompt**: `{prompt}`\n⏳Please wait... Add space after every 5-7 seconds, if image is not generated."
                    ),
                    thumb_url="https://img.icons8.com/color/452/hourglass.png"
                )
            ],
            cache_time=1
        )
        
        # Generate the image - this returns local file paths directly
        local_paths = await generate_inline_image(prompt)
        
        # If no images were generated, show error
        if not local_paths:
            logger.warning(f"No images generated for task {task_id}, user {user_id}")
            try:
                await inline_query.answer(
                    results=[
                        InlineQueryResultArticle(
                            title="❌ Failed to generate image",
                            description="Please try a different prompt",
                            input_message_content=InputTextMessageContent(
                                f"Failed to generate image for: {prompt}\n\n"
                                "Please try a different prompt or try again later."
                            ),
                            thumb_url="https://img.icons8.com/color/452/cancel.png"
                        )
                    ],
                    cache_time=5
                )
            except QueryIdInvalid:
                logger.warning(f"Query ID invalid for failed generation from user {user_id}")
            except Exception as e:
                logger.error(f"Error answering failed generation: {str(e)}")
            
            # Clean up any partial files
            for path in local_paths:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                        logger.info(f"Cleaned up local file after failure: {path}")
                except Exception as e:
                    logger.error(f"Error cleaning up file {path}: {str(e)}")
                    
            return
            
        # First, upload images to Telegram (via the log channel) to get file_ids
        file_ids = []
        for local_path in local_paths:
            if not os.path.exists(local_path):
                logger.error(f"Local file does not exist: {local_path}")
                continue
                
            try:
                # Upload the photo to get the file_id
                sent_photo = await client.send_photo(
                    chat_id=LOG_CHANNEL,
                    photo=local_path,
                    caption=f"#ImgLog #InlineGenerated\n**Prompt**: `{prompt}`\n"\
                            f"**User**: [User {user_id}](tg://user?id={user_id})\n"\
                            f"**Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                
                # Get the file_id
                if hasattr(sent_photo, 'photo') and sent_photo.photo:
                    file_id = sent_photo.photo.file_id
                    file_ids.append(file_id)
                    logger.info(f"Got file_id {file_id} for {local_path}")
                    
                    # Add to cache
                    add_to_cache(user_id, file_id, prompt)
                else:
                    logger.error(f"Failed to get file_id from uploaded photo: {local_path}")
            except Exception as e:
                logger.error(f"Error uploading photo to get file_id: {str(e)}")
                
        # Prepare results using the file_ids
        results = []
        for i, file_id in enumerate(file_ids):
            # Create a cached photo result
            results.append(
                InlineQueryResultCachedPhoto(
                    photo_file_id=file_id,
                    title=f"AI Generated Image",
                    description=prompt,
                    caption=get_image_caption(prompt)
                )
            )
                
        # No valid results
        if not results:
            logger.error(f"No valid results for task {task_id}, user {user_id}")
            try:
                await inline_query.answer(
                    results=[
                        InlineQueryResultArticle(
                            title="❌ Failed to process image",
                            description="Please try again",
                            input_message_content=InputTextMessageContent(
                                f"Failed to process image for: {prompt}\n\n"
                                "Please try again."
                            ),
                            thumb_url="https://img.icons8.com/color/452/cancel.png"
                        )
                    ],
                    cache_time=5
                )
            except QueryIdInvalid:
                logger.warning(f"Query ID invalid for no valid results from user {user_id}")
            except Exception as e:
                logger.error(f"Error answering no valid results: {str(e)}")
                
            # Clean up files
            for path in local_paths:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                        logger.info(f"Cleaned up local file after processing failure: {path}")
                except Exception as e:
                    logger.error(f"Error cleaning up file {path}: {str(e)}")
                    
            return
            
        # Answer with results
        try:
            await inline_query.answer(
                results=results,
                cache_time=3600  # Cache for an hour
            )
            logger.info(f"Successfully answered inline query for user {user_id} with {len(results)} results")
            
            # Delete local files immediately after answering successfully
            for path in local_paths:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                        logger.info(f"Cleaned up local file after successful answer: {path}")
                except Exception as e:
                    logger.error(f"Error cleaning up file {path}: {str(e)}")
                    
        except QueryIdInvalid:
            logger.warning(f"Query ID invalid for final results from user {user_id}")
            # Clean up files
            for path in local_paths:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                        logger.info(f"Cleaned up local file after query invalid: {path}")
                except Exception as e:
                    logger.error(f"Error cleaning up file {path}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error answering with final results: {str(e)}")
            # Clean up files
            for path in local_paths:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                        logger.info(f"Cleaned up local file after answer error: {path}")
                except Exception as e2:
                    logger.error(f"Error cleaning up file {path}: {str(e2)}")
            
    except Exception as e:
        logger.error(f"Error in inline generation for task {task_id}: {str(e)}")
        try:
            await inline_query.answer(
                results=[
                    InlineQueryResultArticle(
                        title="❌ Error generating image",
                        description="An error occurred",
                        input_message_content=InputTextMessageContent(
                            f"Error generating image: {str(e)}"
                        ),
                        thumb_url="https://img.icons8.com/color/452/cancel.png"
                    )
                ],
                cache_time=5
            )
        except QueryIdInvalid:
            logger.warning(f"Query ID invalid for error message from user {user_id}")
        except Exception as e2:
            logger.error(f"Error answering with error message: {str(e2)}")
            
        # Clean up files
        for path in local_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    logger.info(f"Cleaned up local file after general error: {path}")
            except Exception as e3:
                logger.error(f"Error cleaning up file {path}: {str(e3)}")
    finally:
        # Clean up
        if task_id in ongoing_generations:
            del ongoing_generations[task_id]

async def generate_and_cache_image(client: Client, user_id: int, prompt: str, task_id: str) -> None:
    """Generate an image in the background and add it to the cache
    
    Args:
        client: The Pyrogram client
        user_id: User ID requesting the generation
        prompt: The prompt text
        task_id: Task ID for tracking
    """
    logger.info(f"Background generation for cache refresh, user {user_id}, prompt: '{prompt}'")
    
    local_paths = []
    try:
        # Generate the image
        local_paths = await generate_inline_image(prompt)
        
        if not local_paths:
            logger.warning(f"No images generated for cache refresh, user {user_id}")
            return
            
        # Upload to get file_id
        for local_path in local_paths:
            if not os.path.exists(local_path):
                continue
                
            try:
                # Upload quietly to log channel
                sent_photo = await client.send_photo(
                    chat_id=LOG_CHANNEL,
                    photo=local_path,
                    caption=f"#ImgLog #CacheRefresh\n**Prompt**: `{prompt}`\n"\
                            f"**User**: [User {user_id}](tg://user?id={user_id})\n"\
                            f"**Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                
                # Get file_id and update cache
                if hasattr(sent_photo, 'photo') and sent_photo.photo:
                    file_id = sent_photo.photo.file_id
                    add_to_cache(user_id, file_id, prompt)
                    logger.info(f"Added new image to cache for user {user_id}")
                    break  # Just need one image for cache
            except Exception as e:
                logger.error(f"Error uploading photo for cache refresh: {str(e)}")
                
            # Delete this file once uploaded
            try:
                if os.path.exists(local_path):
                    os.remove(local_path)
                    logger.info(f"Cleaned up local file after cache refresh: {local_path}")
            except Exception as e:
                logger.error(f"Error cleaning up file {local_path}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error in background cache refresh: {str(e)}")
    finally:
        # Clean up
        if task_id in ongoing_generations:
            del ongoing_generations[task_id]
            
        # Clean up any remaining files
        for path in local_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    logger.info(f"Cleaned up local file in cache refresh finally block: {path}")
            except Exception as e:
                logger.error(f"Error cleaning up file {path}: {str(e)}")

# Cleanup old ongoing generations and cache periodically
async def cleanup_ongoing_generations():
    """Periodically clean up stale ongoing generations and old cache entries"""
    while True:
        try:
            current_time = time.time()
            to_remove = []
            
            # Clean up stale generations
            for task_id, data in ongoing_generations.items():
                # Remove if older than 2 minutes
                if current_time - data["start_time"] > 120:
                    to_remove.append(task_id)
            
            for task_id in to_remove:
                del ongoing_generations[task_id]
                
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} stale inline generations")
                
            # Clean up old cache entries (older than 24 hours)
            cache_cleanup_count = 0
            for user_id in list(image_cache.keys()):
                user_cache = image_cache[user_id]
                indices_to_remove = []
                
                for i, timestamp in enumerate(user_cache["timestamps"]):
                    if current_time - timestamp > 86400:  # 24 hours
                        indices_to_remove.append(i)
                
                # Remove old entries (in reverse order to maintain indices)
                for i in sorted(indices_to_remove, reverse=True):
                    user_cache["file_ids"].pop(i)
                    user_cache["prompts"].pop(i)
                    user_cache["timestamps"].pop(i)
                    cache_cleanup_count += 1
                
                # Remove user from cache if no images left
                if not user_cache["file_ids"]:
                    del image_cache[user_id]
            
            if cache_cleanup_count > 0:
                logger.info(f"Cleaned up {cache_cleanup_count} old cache entries")
                
            # Check for any stray files in the generated_images directory
            try:
                if os.path.exists("./generated_images"):
                    cutoff_time = current_time - 3600  # Files older than 1 hour
                    for filename in os.listdir("./generated_images"):
                        if filename.startswith("inline_"):
                            file_path = os.path.join("./generated_images", filename)
                            file_mod_time = os.path.getmtime(file_path)
                            
                            if file_mod_time < cutoff_time:
                                try:
                                    os.remove(file_path)
                                    logger.info(f"Cleaned up stray file: {file_path}")
                                except Exception as e:
                                    logger.error(f"Error removing stray file {file_path}: {str(e)}")
            except Exception as e:
                logger.error(f"Error checking for stray files: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")
            
        await asyncio.sleep(30)  # Run every 30 seconds 