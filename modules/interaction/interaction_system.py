import asyncio
import logging
from datetime import datetime, timedelta
from pyrogram import Client
from pymongo.collection import Collection
from modules.core.database import get_user_interactions_collection, get_history_collection, get_creative_prompts_collection
from modules.models.ai_res import get_response
from config import LOG_CHANNEL
from pyrogram.enums import ParseMode

INTERACTION_INTERVAL_MINUTES = 180  # For 3 hours
INTERACTION_CHECK_INTERVAL_SECONDS = 600  # Check every 10 minutes

# --- New Configurable Interval for Image Prompt Suggestions ---
IMAGE_PROMPT_SUGGESTION_HOURS = 12  # Send every 12 hours (can be changed)
IMAGE_PROMPT_SUGGESTION_SECONDS = IMAGE_PROMPT_SUGGESTION_HOURS * 3600 #every hour
IMAGE_PROMPT_ACTIVE_DAYS = 7  # Only send to users active in the last 7 days

logger = logging.getLogger(__name__)

def get_last_interaction(user_id: int, interactions_col: Collection):
    doc = interactions_col.find_one({"user_id": user_id})
    if doc:
        return doc.get("last_interaction_time"), doc.get("last_type")
    return None, None

def set_last_interaction(user_id: int, interaction_type: str, interactions_col: Collection):
    interactions_col.update_one(
        {"user_id": user_id},
        {"$set": {"last_interaction_time": datetime.utcnow(), "last_type": interaction_type}},
        upsert=True
    )

async def generate_engagement_message(user_id: int, history_col: Collection) -> str:
    user_history = history_col.find_one({"user_id": user_id})
    if user_history and user_history.get("history"):
        # Use last 5 messages for context
        history = user_history["history"][-5:]
        prompt = (
            "You are an engaging human like assistant. Based on the user's recent chat history, "
            "generate a unique, interesting question or message to re-engage the user. "
            "Be creative, reference their interests or previous topics if possible. "
            "If they used images or prompt, then send unique creative prompt snippet with /img command. Example: ```/img a futuristic city at sunset``` "
            "Example: ```/img a stunning sunset over a serene lake```"
            "Don't give any other text or instructions. Just the creative beautiful prompt snippet if you think user used images or prompt. "
            "Don't give any other text or instructions. if its message or text then send friendly message & human like message"
        )
        ai_history = history + [{"role": "system", "content": prompt}] 
        try:
            response = get_response(ai_history, model="gpt-4o", provider="PollinationsAI")
            return response
        except Exception as e:
            logger.error(f"AI response error for user {user_id}: {e}")
            return "Hey! Let's chat again. What's new with you?"
    else:
        # No history: suggest image generation with unique prompt
        prompt = (
            "Generate a unique, creative image prompt text snippet with /img command for a new user. "
            "Reply ONLY with the image prompt inside triple backticks (```) so the user can copy-paste it. "
            "Keep the prompt creative , fun,unique and attractive. "
            "Example: ```/img a futuristic city at sunset```"
            "Don't give any other text or instructions or sponsor text. Just the creative prompt snippet"
            "Example: ```/img a stunning sunset over a serene lake```"
        )
        try:
            response = get_response([
                {"role": "system", "content": prompt}
            ], model="gpt-4o", provider="PollinationsAI")
            # Ensure the response is wrapped in triple backticks for Telegram code snippet
            snippet = response
            # print(snippet)  
            if not snippet.startswith("```"):
                snippet = f"```\n{snippet}\n```"
            return "🎨 Try this image idea!\nJust copy & paste below with /img to create:\n\n" + snippet
        except Exception as e:
            logger.error(f"AI response error for new user {user_id}: {e}")
            return (
                "🎨 Try this image idea!\nJust copy & paste below with /img to create:\n\n" +
                "```\n/img a beautiful sunset over a serene lake\n```"
            )

async def send_interaction_message(client: Client, user_id: int, message: str):
    try:
        await client.send_message(user_id, message, parse_mode=ParseMode.DEFAULT, disable_web_page_preview=True)
        return True
    except Exception as e:
        logger.error(f"Failed to send interaction to {user_id}: {e}")
        try:
            await client.send_message(LOG_CHANNEL, f"[InteractionSystem] Failed to send to {user_id}: {e}", parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass
        return False

async def interaction_worker(client: Client):
    interactions_col = get_user_interactions_collection()
    history_col = get_history_collection()
    while True:
        now = datetime.utcnow()
        # Only users with last_interaction_time older than threshold
        users = interactions_col.find({
            "last_interaction_time": {"$exists": True, "$lt": now - timedelta(minutes=INTERACTION_INTERVAL_MINUTES)}
        })
        for user in users:
            user_id = user["user_id"]
            msg = await generate_engagement_message(user_id, history_col)
            sent = await send_interaction_message(client, user_id, msg)
            if sent:
                set_last_interaction(user_id, "interaction_system", interactions_col)
        await asyncio.sleep(INTERACTION_CHECK_INTERVAL_SECONDS)

async def generate_unique_image_prompt(existing_prompts=None):
    """
    Generate a unique, creative, beautiful image prompt using the AI model.
    Optionally pass a set of existing prompts to avoid duplicates.
    """
    prompt = (
        "Generate a unique, creative, beautiful, and visually stunning image prompt for an AI image generator. "
        "Do NOT repeat any previous prompt. Do NOT include any sponsor or unrelated text. "
        "Reply ONLY with the prompt inside triple backticks (```). "
        "Do NOT include the /img prefix in your response. "
        "Example: ```a futuristic city at sunset with neon lights```. "
        "Make it fun, attractive, and different from previous prompts."
    )
    ai_history = [
        {"role": "system", "content": prompt}
    ]
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, get_response, ai_history, "gpt-4o", "PollinationsAI")
    snippet = response.strip()
    if not snippet.startswith("```"):
        snippet = f"""```
{snippet}
```"""
    # Extract the prompt inside triple backticks
    import re
    match = re.search(r"```\s*(.*?)```", snippet, re.DOTALL)
    if match:
        prompt_text = match.group(1).strip()
        # Always add /img prefix, never duplicate
        if prompt_text.lower().startswith("/img"):
            prompt_text = prompt_text[4:].strip()
        prompt_text = "/img " + prompt_text
        # Check for duplicates
        if existing_prompts and prompt_text in existing_prompts:
            return None  # Duplicate, skip
        return prompt_text
    return None

# --- Image Prompt Suggestion Worker (DISABLED as per user request) ---
# async def image_prompt_suggestion_worker(client: Client):
#     creative_prompts_col = get_creative_prompts_collection()
#     interactions_col = get_user_interactions_collection()
#     while True:
#         now = datetime.utcnow()
#         # Only users who have interacted in the last N days
#         active_since = now - timedelta(days=IMAGE_PROMPT_ACTIVE_DAYS)
#         users = interactions_col.find({
#             "last_interaction_time": {"$exists": True, "$gte": active_since}
#         })
#         # Get all creative prompts
#         all_prompts = list(creative_prompts_col.find({}, {"prompt": 1}))
#         prompt_texts = [p["prompt"] for p in all_prompts]
#         # If not enough prompts, generate more
#         needed = max(0, len(list(users)) - len(prompt_texts))
#         for _ in range(needed):
#             new_prompt = None
#             tries = 0
#             while not new_prompt and tries < 5:
#                 new_prompt = await generate_unique_image_prompt(set(prompt_texts))
#                 tries += 1
#             if new_prompt:
#                 creative_prompts_col.insert_one({"prompt": new_prompt, "created_at": datetime.utcnow()})
#                 prompt_texts.append(new_prompt)
#         # Re-fetch users (cursor was exhausted)
#         users = interactions_col.find({
#             "last_interaction_time": {"$exists": True, "$gte": active_since}
#         })
#         # For each user, send a prompt they haven't received yet
#         for user in users:
#             user_id = user["user_id"]
#             # Track which prompts this user has received
#             received = user.get("image_prompts_sent", [])
#             # Find a prompt not yet sent to this user
#             available = [p for p in prompt_texts if p not in received]
#             if not available:
#                 # Reset if all used
#                 received = []
#                 available = prompt_texts.copy()
#             import random
#             prompt_to_send = random.choice(available)
#             # Send the prompt
#             try:
#                 await client.send_message(user_id, f"🎨 Try this creative image idea!\nJust copy & paste below with /img to create:\n\n```\n{prompt_to_send}\n```", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
#                 # Update user's sent prompts
#                 interactions_col.update_one(
#                     {"user_id": user_id},
#                     {"$set": {"image_prompts_sent": received + [prompt_to_send]}}
#                 )
#             except Exception as e:
#                 logger.error(f"Failed to send image prompt to {user_id}: {e}")
#                 try:
#                     await client.send_message(LOG_CHANNEL, f"[ImagePromptSuggestion] Failed to send to {user_id}: {e}")
#                 except Exception:
#                     pass
#         await asyncio.sleep(IMAGE_PROMPT_SUGGESTION_SECONDS)

def start_interaction_system(client: Client):
    """
    Starts the background interaction system and image prompt suggestion system.
    Call this from run.py after the bot is started.
    """
    loop = asyncio.get_event_loop()
    loop.create_task(interaction_worker(client))
    # loop.create_task(image_prompt_suggestion_worker(client))  # DISABLED as per user request 