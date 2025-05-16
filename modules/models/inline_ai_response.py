import asyncio
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any
import re

from pyrogram import Client
from pyrogram.types import (
    InlineQuery, 
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineQueryResultCachedPhoto
)
from pyrogram.errors import QueryIdInvalid

from modules.models.ai_res import get_response
from config import LOG_CHANNEL

# Get the logger
logger = logging.getLogger(__name__)

# Store ongoing inline AI generations to prevent duplicates
# Format: {task_id: {"user_id": user_id, "prompt": prompt, "start_time": time}}
ongoing_generations = {}

# AI response cache system - store generated responses by user
# Format: {user_id: {"prompts": [prompt1, prompt2...], "responses": [response1, response2...], "timestamps": [time1, time2...]}}
ai_cache = {}
MAX_CACHE_PER_USER = 10  # Maximum number of cached responses per user

# Temporary query cache for handling inline query timeouts
# Format: {user_id: {"query": query, "response": response, "timestamp": time, "attempts": count}}
temp_query_cache = {}

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

def get_cached_response(user_id: int, prompt: str = None) -> Optional[List[Dict[str, str]]]:
    """Get a cached AI response for a user
    
    Args:
        user_id: The user ID
        prompt: Optional prompt to match (if None, return most recent response)
        
    Returns:
        List of matching responses with their prompts or None if not found
    """
    if user_id not in ai_cache:
        return None
    
    user_cache = ai_cache[user_id]
    
    if not user_cache["responses"]:
        return None
    
    # If no specific prompt requested, return the most recent response
    if prompt is None:
        return [{
            "prompt": user_cache["prompts"][0],
            "response": user_cache["responses"][0]
        }]
    
    # Store all matches
    matches = []
    
    # Try to find an exact match for the prompt
    for i, cached_prompt in enumerate(user_cache["prompts"]):
        if cached_prompt.lower() == prompt.lower():
            matches.append({
                "prompt": cached_prompt,
                "response": user_cache["responses"][i],
                "match_score": 1.0  # Perfect match
            })
    
    # Check for prompt with extra spaces (user might be adding spaces while waiting)
    if not matches:
        stripped_prompt = re.sub(r'\s+', ' ', prompt.lower()).strip()
        for i, cached_prompt in enumerate(user_cache["prompts"]):
            stripped_cached = re.sub(r'\s+', ' ', cached_prompt.lower()).strip()
            if stripped_prompt == stripped_cached:
                matches.append({
                    "prompt": cached_prompt,
                    "response": user_cache["responses"][i],
                    "match_score": 0.98  # Near perfect match (just spacing differences)
                })
    
    # No exact match, try to find a similar prompt (contains the same keywords)
    if not matches:
        prompt_keywords = set(re.sub(r'\s+', ' ', prompt.lower()).strip().split())
        
        for i, cached_prompt in enumerate(user_cache["prompts"]):
            stripped_cached = re.sub(r'\s+', ' ', cached_prompt.lower()).strip()
            cached_keywords = set(stripped_cached.split())
            
            # Skip if either prompt has too few keywords for meaningful comparison
            if len(prompt_keywords) < 2 or len(cached_keywords) < 2:
                continue
                
            # Calculate match score based on word similarity
            common_keywords = prompt_keywords.intersection(cached_keywords)
            
            # Calculate Jaccard similarity: intersection over union
            total_keywords = len(prompt_keywords.union(cached_keywords))
            if total_keywords > 0:
                jaccard_sim = len(common_keywords) / total_keywords
                
                # Calculate string similarity score
                from difflib import SequenceMatcher
                string_sim = SequenceMatcher(None, 
                                         re.sub(r'\s+', ' ', prompt.lower()).strip(),
                                         re.sub(r'\s+', ' ', cached_prompt.lower()).strip()).ratio()
                
                # Combined score (weighted average)
                score = 0.7 * string_sim + 0.3 * jaccard_sim
                
                # Only include if score is >= 0.8 (80% match) as requested
                if score >= 0.8:
                    matches.append({
                        "prompt": cached_prompt,
                        "response": user_cache["responses"][i],
                        "match_score": score
                    })
    
    # Check temporary query cache
    if not matches and user_id in temp_query_cache:
        temp_cache = temp_query_cache[user_id]
        stripped_prompt = re.sub(r'\s+', ' ', prompt.lower()).strip()
        stripped_temp = re.sub(r'\s+', ' ', temp_cache["query"].lower()).strip()
        
        if stripped_prompt == stripped_temp:
            matches.append({
                "prompt": temp_cache["query"],
                "response": temp_cache["response"],
                "match_score": 0.99  # Very high match from temp cache
            })
    
    # Sort matches by score, highest first
    if matches:
        matches.sort(key=lambda x: x["match_score"], reverse=True)
        return matches
    
    # No good match found
    return None

def add_to_cache(user_id: int, prompt: str, response: str) -> None:
    """Add a generated AI response to the cache
    
    Args:
        user_id: The user ID
        prompt: The prompt used to generate the response
        response: The AI response
    """
    # Initialize user cache if not exists
    if user_id not in ai_cache:
        ai_cache[user_id] = {
            "prompts": [],
            "responses": [],
            "timestamps": []
        }
    
    user_cache = ai_cache[user_id]
    
    # Check if we already have this prompt (to avoid duplicates)
    for i, cached_prompt in enumerate(user_cache["prompts"]):
        stripped_prompt = re.sub(r'\s+', ' ', prompt.lower()).strip()
        stripped_cached = re.sub(r'\s+', ' ', cached_prompt.lower()).strip()
        if stripped_prompt == stripped_cached:
            # Replace with newer response
            user_cache["responses"][i] = response
            user_cache["timestamps"][i] = time.time()
            logger.info(f"Updated existing cache entry for user {user_id}, prompt: '{prompt}'")
            return
    
    # Add new response at the front (most recent first)
    user_cache["prompts"].insert(0, prompt)
    user_cache["responses"].insert(0, response)
    user_cache["timestamps"].insert(0, time.time())
    
    # Limit cache size
    if len(user_cache["prompts"]) > MAX_CACHE_PER_USER:
        user_cache["prompts"].pop()
        user_cache["responses"].pop()
        user_cache["timestamps"].pop()
        
    logger.info(f"Added AI response to cache for user {user_id}, prompt: '{prompt}'")
    
    # Also add to temporary query cache
    temp_query_cache[user_id] = {
        "query": prompt,
        "response": response,
        "timestamp": time.time(),
        "attempts": 0
    }

def clear_user_cache(user_id: int) -> None:
    """Clear the cache for a specific user
    
    Args:
        user_id: The user ID to clear cache for
    """
    if user_id in ai_cache:
        del ai_cache[user_id]
        logger.info(f"Cleared AI response cache for user {user_id}")
    if user_id in temp_query_cache:
        del temp_query_cache[user_id]
        logger.info(f"Cleared temporary query cache for user {user_id}")

def format_ai_response(response: str, prompt: str, username: str = None) -> str:
    """Format AI response for better readability in inline results
    
    Args:
        response: The raw AI response
        prompt: The original prompt/question
        username: Optional username to include
        
    Returns:
        Formatted response with proper markdown
    """
    # Clean the response of any problematic formatting
    # Replace triple backticks with double backticks to maintain code formatting without breaking Telegram markdown
    response = re.sub(r'```(?:\w+)?\n?(.*?)\n?```', r'`\1`', response, flags=re.DOTALL)
    
    # Ensure response doesn't exceed Telegram's limit (4096 chars)
    if len(response) > 3800:
        response = response[:3797] + "..."
    
    # Add modern formatting with emoji, the original question, and bot signature
    formatted_response = f"🤖 **AI Response**\n\n"
    formatted_response += f"📝 **Query**: {prompt}\n\n"
    formatted_response += f"🔍 **Response**:\n{response}\n\n"
    
    # Add username if provided
    # if username:
    #     formatted_response += f"👤 Request by {username}\n"
        
    formatted_response += f"**@AdvChatGptBot**"
    
    return formatted_response

async def generate_ai_response(prompt: str) -> str:
    """Generate AI response for inline query
    
    Args:
        prompt: The text prompt for AI response
        
    Returns:
        AI response text
    """
    logger.info(f"Generating inline AI response with prompt: '{prompt}'")
    
    try:
        # Prepare history for AI model
        history = [
            {
                "role": "system", 
                "content": "You are a helpful AI assistant. Provide concise, accurate, and helpful responses."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # Get response from AI model
        response = get_response(history)
        
        if not response:
            return "Sorry, I couldn't generate a response. Please try again."
        
        logger.info(f"Successfully generated AI response for inline query")
        return response
        
    except Exception as e:
        logger.error(f"Error generating inline AI response: {str(e)}")
        return f"Sorry, an error occurred: {str(e)}"

async def handle_inline_ai_query(client: Client, inline_query: InlineQuery, prompt: str) -> None:
    """Handle inline queries for AI response generation
    
    Args:
        client: Pyrogram client instance
        inline_query: The inline query object
        prompt: The processed prompt text (without the ending punctuation)
    """
    user_id = inline_query.from_user.id
    query_id = inline_query.id
    username = inline_query.from_user.username or inline_query.from_user.first_name
    
    # Check if prompt is too short
    if len(prompt) < 3:
        try:
            await inline_query.answer(
                results=[
                    InlineQueryResultArticle(
                        title="Prompt too short",
                        description="Please provide a more detailed prompt",
                        input_message_content=InputTextMessageContent(
                            "🤔 Your prompt is too short. Please provide more details for better results."
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
                        description="Your AI response cache has been cleared",
                        input_message_content=InputTextMessageContent(
                            "✅ Your AI response cache has been cleared. All new responses will be freshly generated."
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
    
    # Check for cached responses first
    cached_responses = get_cached_response(user_id, prompt)
    if cached_responses:
        try:
            # Respond with cached responses (up to 3)
            results = []
            for i, match in enumerate(cached_responses[:3]):  # Limit to top 3 matches
                # Format with question included
                formatted_response = format_ai_response(
                    match["response"].split("\n\n", 2)[1] if "\n\n" in match["response"] else match["response"],
                    match["prompt"],
                    username
                )
                
                # For multiple results, show different titles
                if len(cached_responses) > 1:
                    title = f"🔄 Matched Response #{i+1} ({int(match['match_score']*100)}% match)"
                else:
                    title = f"🔄 AI Response (Cached)"
                
                results.append(
                    InlineQueryResultArticle(
                        title=title,
                        description=f"Q: {match['prompt'][:50]}{'...' if len(match['prompt']) > 50 else ''}",
                        input_message_content=InputTextMessageContent(
                            formatted_response,
                            disable_web_page_preview=True
                        ),
                        thumb_url="https://img.icons8.com/color/452/chatgpt.png"
                    )
                )
            
            await inline_query.answer(
                results=results,
                cache_time=5  # Short cache time for inline results
            )
            logger.info(f"Answered query from user {user_id} with {len(results)} cached AI responses")
            return
        except Exception as e:
            logger.error(f"Error answering with cached AI responses: {str(e)}")
            # Continue to generate new response if cached response failed
    
    # Check if there's an ongoing generation in progress for this user
    for task_id, data in ongoing_generations.items():
        if data["user_id"] == user_id and time.time() - data["start_time"] < 30:
            # Show waiting message with instruction to add space
            try:
                await inline_query.answer(
                    results=[
                        InlineQueryResultArticle(
                            title="⏳ Still generating your response...",
                            description="Add a space every 5-7 seconds if no response appears",
                            input_message_content=InputTextMessageContent(
                                f"🤖 **Generating AI Response**\n\n📝 **Question**: `{prompt}`\n\n⏳ Please wait... Add a space every 5-7 seconds if no response appears."
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
    
    # Start the generation
    try:
        # Store this query in ongoing generations
        ongoing_generations[task_id] = {
            "user_id": user_id,
            "prompt": prompt,
            "start_time": time.time(),
            "query_id": query_id,
            "inline_query": inline_query
        }
        
        # Show initial "generating" message with more modern UI and space instruction
        await inline_query.answer(
            results=[
                InlineQueryResultArticle(
                    title="🤖 Generating AI response...",
                    description=f"Question: {prompt[:50]}{'...' if len(prompt) > 50 else ''}\n⏳ Add a space every 5-7 seconds if no response appears",
                    input_message_content=InputTextMessageContent(
                        f"🤖 **Generating AI Response**\n\n📝 **Question**: `{prompt}`\n\n⏳ Please wait... Add a space every 5-7 seconds if no response appears."
                    ),
                    thumb_url="https://img.icons8.com/color/452/artificial-intelligence.png"
                )
            ],
            cache_time=1
        )
        
        # Generate the AI response
        response = await generate_ai_response(prompt)
        
        # Format response with question included and username
        formatted_response = format_ai_response(response, prompt, username)
        
        # Add to cache
        add_to_cache(user_id, prompt, formatted_response)
        
        # Determine if it's a question (ended with ?) for better UI
        was_question = prompt.strip().endswith("?")
        icon = "❓" if was_question else "🤖"
        
        # Extract a short preview for the description
        short_preview = response[:100] + "..." if len(response) > 100 else response
        
        # Answer with results with improved UI and NO markdown
        try:
            await inline_query.answer(
                results=[
                    InlineQueryResultArticle(
                        title=f"{icon} AI Response",
                        description=f"Q: {prompt[:50]}{'...' if len(prompt) > 50 else ''}",
                        input_message_content=InputTextMessageContent(
                            formatted_response,
                            disable_web_page_preview=True
                        ),
                        thumb_url="https://img.icons8.com/color/452/artificial-intelligence.png"
                    )
                ],
                cache_time=5  # Short cache time
            )
            logger.info(f"Successfully answered inline AI query for user {user_id}")
                    
        except QueryIdInvalid:
            logger.warning(f"Query ID invalid for final results from user {user_id}")
            # Store in temp_query_cache for potential retry with spaces
            temp_query_cache[user_id] = {
                "query": prompt,
                "response": formatted_response,
                "timestamp": time.time(),
                "attempts": 0
            }
            
        except Exception as e:
            logger.error(f"Error answering with final results: {str(e)}")
            # Store in temp_query_cache for potential retry
            temp_query_cache[user_id] = {
                "query": prompt,
                "response": formatted_response,
                "timestamp": time.time(),
                "attempts": 0
            }
            
    except Exception as e:
        logger.error(f"Error in inline AI generation for task {task_id}: {str(e)}")
        try:
            await inline_query.answer(
                results=[
                    InlineQueryResultArticle(
                        title="❌ Error generating AI response",
                        description="An error occurred",
                        input_message_content=InputTextMessageContent(
                            f"❌ Error generating AI response: {str(e)}"
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
    finally:
        # Clean up
        if task_id in ongoing_generations:
            del ongoing_generations[task_id]

# Cleanup old ongoing generations and cache periodically
async def cleanup_ongoing_generations():
    """Periodically clean up stale ongoing generations and temp query cache"""
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
                logger.info(f"Cleaned up {len(to_remove)} stale inline AI generations")
                
            # Clean up temporary query cache (after 20 seconds)
            temp_cache_to_remove = []
            for user_id, data in temp_query_cache.items():
                if current_time - data["timestamp"] > 20:  # 20 seconds expiry
                    temp_cache_to_remove.append(user_id)
            
            for user_id in temp_cache_to_remove:
                del temp_query_cache[user_id]
                
            if temp_cache_to_remove:
                logger.info(f"Cleaned up temporary query cache for {len(temp_cache_to_remove)} users")
                
            # Clean up regular cache entries (older than 24 hours)
            cache_cleanup_count = 0
            for user_id in list(ai_cache.keys()):
                user_cache = ai_cache[user_id]
                indices_to_remove = []
                
                for i, timestamp in enumerate(user_cache["timestamps"]):
                    if current_time - timestamp > 86400:  # 24 hours
                        indices_to_remove.append(i)
                
                # Remove old entries (in reverse order to maintain indices)
                for i in sorted(indices_to_remove, reverse=True):
                    user_cache["prompts"].pop(i)
                    user_cache["responses"].pop(i)
                    user_cache["timestamps"].pop(i)
                    cache_cleanup_count += 1
                
                # Remove user from cache if no responses left
                if not user_cache["prompts"]:
                    del ai_cache[user_id]
            
            if cache_cleanup_count > 0:
                logger.info(f"Cleaned up {cache_cleanup_count} old AI cache entries")
                
        except Exception as e:
            logger.error(f"Error in AI cleanup task: {str(e)}")
            
        await asyncio.sleep(5)  # Run every 5 seconds for more responsive cleanup