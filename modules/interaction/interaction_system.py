import asyncio
import logging
from datetime import datetime, timedelta
from pyrogram import Client
from pymongo.collection import Collection
from modules.core.database import get_user_interactions_collection, get_history_collection
from modules.models.ai_res import get_response
from config import LOG_CHANNEL
from pyrogram.enums import ParseMode

INTERACTION_INTERVAL_MINUTES = 3  # For testing, 3 minutes
INTERACTION_CHECK_INTERVAL_SECONDS = 60  # Check every minute

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
            snippet = response.strip()
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
        await client.send_message(user_id, message, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
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

def start_interaction_system(client: Client):
    """
    Starts the background interaction system.
    Call this from run.py after the bot is started.
    """
    loop = asyncio.get_event_loop()
    loop.create_task(interaction_worker(client)) 