import datetime
from pymongo import MongoClient
from config import DATABASE_URL
from typing import Tuple, Optional
import asyncio
from modules.user.ai_model import revert_restricted_models_if_needed
from modules.core.database import db_service

# Initialize MongoDB client and collection
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']

def get_premium_users_collection():
    return db_service.get_collection('premium_users')

async def add_premium_status(user_id: int, admin_id: int, days: int) -> bool:
    """Adds or updates a user's premium status."""
    if not isinstance(user_id, int) or not isinstance(admin_id, int) or not isinstance(days, int):
        return False
    if days <= 0: # Use to revoke premium manually if needed by setting days to 0 or less
        return await remove_premium_status(user_id, revoked_by_admin=True)

    now = datetime.datetime.now(datetime.timezone.utc)
    expires_at = now + datetime.timedelta(days=days)
    
    premium_record = {
        "user_id": user_id,
        "is_premium": True,
        "premium_since": now,
        "premium_days_granted": days,
        "premium_expires_at": expires_at,
        "granted_by": admin_id,
        "last_updated": now
    }
    
    get_premium_users_collection().update_one({"user_id": user_id}, {"$set": premium_record}, upsert=True)
    return True

async def remove_premium_status(user_id: int, revoked_by_admin: bool = False) -> bool:
    """Marks a user as not premium. Can be called manually or by daily checker."""
    if not isinstance(user_id, int):
        return False
        
    update_fields = {
        "is_premium": False,
        "premium_expires_at": datetime.datetime.now(datetime.timezone.utc) # Mark as expired now
    }
    if revoked_by_admin:
        update_fields["reason_for_removal"] = "Revoked by admin"

    result = get_premium_users_collection().update_one(
        {"user_id": user_id, "is_premium": True},
        {"$set": update_fields}
    )
    # Revert restricted models if needed
    await revert_restricted_models_if_needed(user_id)
    return result.modified_count > 0

async def is_user_premium(user_id: int) -> Tuple[bool, int, Optional[datetime.datetime]]:
    """Checks if a user is premium. Returns (is_premium, remaining_days, expires_at)."""
    if not isinstance(user_id, int):
        return False, 0, None
        
    user_record = get_premium_users_collection().find_one({"user_id": user_id, "is_premium": True})
    if not user_record:
        return False, 0, None

    expires_at = user_record.get("premium_expires_at")
    if not expires_at or not isinstance(expires_at, datetime.datetime):
        # This case indicates bad data or an issue, log it and treat as not premium.
        print(f"Error: User {user_id} has invalid premium_expires_at: {expires_at}")
        return False, 0, None

    now = datetime.datetime.now(datetime.timezone.utc)
    if expires_at > now:
        remaining_time = expires_at - now
        # Calculate remaining_days, ensuring it's at least 1 if there's any positive time left.
        remaining_days = remaining_time.days
        if remaining_time.total_seconds() > 0 and remaining_days == 0:
            remaining_days = 1 # If less than a day but positive, count as 1 day remaining.
        elif remaining_time.days < 0: # Should be caught by expires_at > now, but as a safeguard
             remaining_days = 0
        return True, remaining_days, expires_at
    else:
        # Premium has expired, ensure it's marked in DB if not already
        if user_record.get("is_premium", False):
             asyncio.create_task(remove_premium_status(user_id))
        return False, 0, expires_at

async def get_premium_status_message(user_id: int) -> Optional[str]:
    """Generates a message about the user's premium status if they are premium."""
    is_premium, remaining_days, _ = await is_user_premium(user_id)
    if is_premium:
        days_str = "day" if remaining_days == 1 else "days"
        # Ensure remaining_days is at least 0 for the message
        display_days = max(0, remaining_days) 
        return f"✨ You are a Premium User! Your access is valid for {display_days} more {days_str}.\n\nUse /benefits to see the benefits of being a premium user."
    return None

async def daily_premium_check(client_for_notification=None):
    """Daily check for expired premium statuses."""
    print("Running daily premium check...")
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Find users whose premium has expired but are still marked as premium
    expired_users_docs = list(get_premium_users_collection().find({
        "is_premium": True,
        "premium_expires_at": {"$lte": now}
    }))
    
    count = 0
    if not expired_users_docs:
        print("No expired premium users found needing update.")
        return count

    for user_record in expired_users_docs:
        user_id = user_record["user_id"]
        print(f"Processing expired premium for user_id: {user_id}")
        if await remove_premium_status(user_id):
            count += 1
            print(f"Premium status successfully removed for user_id: {user_id}")
            if client_for_notification:
                try:
                    await client_for_notification.send_message(
                        user_id, 
                        "🔔 Your Premium User status has expired. We hope you enjoyed the benefits!"
                    )
                    print(f"Sent expiry notification to {user_id}")
                except Exception as e:
                    print(f"Failed to send premium expiry notification to {user_id}: {e}")
        else:
            print(f"Failed to remove premium status for user_id: {user_id}, or already marked as not premium.")
        # Always revert restricted models for expired users (safety)
        await revert_restricted_models_if_needed(user_id)
            
    if count > 0:
        print(f"Daily premium check: {count} users had their premium status expired and updated.")
    else:
        print("Daily premium check: No premium statuses were updated (they might have been already up to date).")
    return count 

async def get_premium_benefits_message(user_id: int) -> str:
    """
    Returns a clean, modern, and visually appealing HTML message comparing Standard and Premium benefits in a single, unified card.
    """
    from modules.user.ai_model import TEXT_MODELS, IMAGE_MODELS

    # --- Header ---
    header = (
        "<b>💎 Unlock Premium AI Power!</b>\n"
        "<i>Upgrade for the best AI experience, exclusive models, and more control.</i>\n"
    )

    # --- Feature Comparison (Compact, Card Style) ---
    features = [
        ("🧠 AI Text Models", "GPT-4o", "GPT-4o, GPT-4.1, Qwen3, DeepSeek-R1"),
        ("🖼️ Image Models", "DALL-E 3, Flux", "DALL-E 3, Flux, Flux Pro"),
        ("🖼️ Images per Request", "1", "Up to 4"),
        ("⚡ Image Speed", "Standard", "Priority (Faster)"),
        ("🚀 AI Response Time", "Standard", "Enhanced"),
        ("📈 Daily Usage", "Standard Limits", "Higher/No Limits"),
        ("🥇 New Features", "Standard Rollout", "Early Access"),
        ("🔒 Maintenance Access", "Restricted", "Uninterrupted"),
    ]
    feature_rows = "\n".join([
        f"<b>{icon}</b> <code>\nStandard:</code> {std}   <code>\nPremium:</code> {prem}\n" for icon, std, prem in features
    ])

    # --- Premium-Only Models ---
    premium_models = [TEXT_MODELS['gpt-4.1'], TEXT_MODELS['qwen3'], IMAGE_MODELS['flux-pro']]
    premium_models_section = (
        "\n<b>✨ Premium-Only Models:</b> <code>" + ", ".join(premium_models) + "</code>\n"
        "<i>\nAccess the most advanced AI and image models, only for Premium users.</i>"
    )
    # --- Call to Action ---
    upgrade_cta = (
        "\n\n<a href='https://t.me/techycsr'><b>🚀 Upgrade to Premium Now</b></a>"
    )

    # --- Compose Message ---
    message = (
        f"{header}"
        "<pre>─────────────────────────────</pre>\n"
        f"{feature_rows}\n"
        "<pre>─────────────────────────────</pre>\n"
        f"{premium_models_section}"
        f"{upgrade_cta}"
    )
    return message 

async def get_all_premium_users():
    """Returns a list of all users with active premium status, including user_id, premium_since, and premium_expires_at."""
    users = list(get_premium_users_collection().find({"is_premium": True}))
    result = []
    for user in users:
        result.append({
            "user_id": user["user_id"],
            "premium_since": user.get("premium_since"),
            "premium_expires_at": user.get("premium_expires_at")
        })
    return result

async def format_premium_users_list(users):
    """Formats the premium users list for admin display."""
    if not users:
        return "<b>No active premium users found.</b>"
    lines = ["<b>💎 Premium Users List</b>\n"]
    for u in users:
        since = u["premium_since"].strftime("%Y-%m-%d") if u["premium_since"] else "-"
        until = u["premium_expires_at"].strftime("%Y-%m-%d") if u["premium_expires_at"] else "-"
        lines.append(f"<b>User:</b> <code>{u['user_id']}</code> | <b>Start:</b> {since} | <b>Expires:</b> {until}")
    return "\n".join(lines) 