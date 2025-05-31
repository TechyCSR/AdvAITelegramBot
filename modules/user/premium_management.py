import datetime
from pymongo import MongoClient
from config import DATABASE_URL
from typing import Tuple, Optional
import asyncio
from modules.lang import async_translate_to_lang # Import for localization

# Initialize MongoDB client and collection
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
premium_users_collection = db['premium_users']

async def add_premium_status(user_id: int, admin_id: int, days: int) -> bool:
    """Adds or updates a user's premium status."""
    if not isinstance(user_id, int) or not isinstance(admin_id, int) or not isinstance(days, int):
        return False
    if days <= 0: # Use to revoke premium manually if needed by setting days to 0 or less
        return await remove_premium_status(user_id, revoked_by_admin=True)

    now = datetime.datetime.utcnow()
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
    
    premium_users_collection.update_one({"user_id": user_id}, {"$set": premium_record}, upsert=True)
    return True

async def remove_premium_status(user_id: int, revoked_by_admin: bool = False) -> bool:
    """Marks a user as not premium. Can be called manually or by daily checker."""
    if not isinstance(user_id, int):
        return False
        
    update_fields = {
        "is_premium": False,
        "premium_expires_at": datetime.datetime.utcnow() # Mark as expired now
    }
    if revoked_by_admin:
        update_fields["reason_for_removal"] = "Revoked by admin"

    result = premium_users_collection.update_one(
        {"user_id": user_id, "is_premium": True},
        {"$set": update_fields}
    )
    return result.modified_count > 0

async def is_user_premium(user_id: int) -> Tuple[bool, int, Optional[datetime.datetime]]:
    """Checks if a user is premium. Returns (is_premium, remaining_days, expires_at)."""
    if not isinstance(user_id, int):
        return False, 0, None
        
    user_record = premium_users_collection.find_one({"user_id": user_id, "is_premium": True})
    if not user_record:
        return False, 0, None

    expires_at = user_record.get("premium_expires_at")
    if not expires_at or not isinstance(expires_at, datetime.datetime):
        # This case indicates bad data or an issue, log it and treat as not premium.
        print(f"Error: User {user_id} has invalid premium_expires_at: {expires_at}")
        return False, 0, None

    now = datetime.datetime.utcnow()
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
    now = datetime.datetime.utcnow()
    
    # Find users whose premium has expired but are still marked as premium
    expired_users_docs = list(premium_users_collection.find({
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
            
    if count > 0:
        print(f"Daily premium check: {count} users had their premium status expired and updated.")
    else:
        print("Daily premium check: No premium statuses were updated (they might have been already up to date).")
    return count 

async def get_premium_benefits_message(user_id: int) -> str:
    """Generates a visually appealing HTML message comparing premium and regular user benefits."""
    
    header_text = "🌟 <b>Unlock Superpowers with Premium!</b> 🌟"
    # For potential future localization:
    # header_text = await async_translate_to_lang("🌟 <b>Unlock Superpowers with Premium!</b> 🌟", user_id)
    # sub_header_text = await async_translate_to_lang("Here's a glimpse of what you get:", user_id)
    # regular_user_title = await async_translate_to_lang("👤 Regular User", user_id)
    # premium_user_title = await async_translate_to_lang("✨ Premium User", user_id)
    # upgrade_prompt = await async_translate_to_lang("Ready to upgrade? Contact admin @techycsr", user_id)

    sub_header_text = "Here's a glimpse of what you get:"
    regular_user_title = "👤 Regular User"
    premium_user_title = "✨ Premium User"
    upgrade_prompt = "Ready to upgrade? Contact admin @techycsr"

    message = f"{header_text}\n{sub_header_text}\n\n"

    benefits = [
        {"feature": "🖼️ Image Generation Model", "regular": "Standard (DALL-E 2)", "premium": "🎨 Advanced (DALL-E 3 - Higher Quality & Accuracy)"},
        {"feature": "⚡ Image Generation Speed", "regular": "Standard Queue", "premium": "Priority Queue (Faster Results)"},
        {"feature": "🚀 AI Response Time", "regular": "Standard", "premium": "Enhanced (Quicker Bot Replies)"},
        {"feature": "🚧 Maintenance Mode Access", "regular": "⛔ Restricted Access", "premium": "✅ Uninterrupted Bot Usage"},
        {"feature": "👥 Group Chat Features", "regular": "Limited (Basic Commands)", "premium": "Full Access (All AI Features)"},
        {"feature": "📈 Daily Usage Limits", "regular": "Standard Limits", "premium": "Higher Limits / No Limits (Varies)"},
        {"feature": "🥇 New Feature Access", "regular": "Standard Rollout", "premium": "Early Access to Beta Features"},
        {"feature": "🆘 Support Priority", "regular": "Standard Support", "premium": "Priority Support Channel"}
    ]

    for item in benefits:
        message += f"<b>{item['feature']}</b>\n"
        message += f"  <code>{regular_user_title}:</code> {item['regular']}\n"
        message += f"  <code>{premium_user_title}:</code> {item['premium']}\n\n"
    
    message += f"\n{upgrade_prompt}"
    return message 