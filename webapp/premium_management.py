"""
Premium Management System for AdvAI Image Generator Webapp
Handles premium user status, benefits, and restrictions for webapp users.
Uses the same database collections as the main bot for consistency.
"""

import datetime
from typing import Tuple, Optional, Dict, Any, List
import logging
from database_service import get_premium_users_collection
from config import ADMINS

# Configure logging
logger = logging.getLogger(__name__)

# Premium-related constants (same as bot)
TEXT_MODELS = {
    "gpt-4o": "GPT-4o",
    "gpt-4.1": "GPT-4.1",
    "qwen3": "Qwen3",
    "deepseek-r1": "DeepSeek-R1"
}

IMAGE_MODELS = {
    "dall-e3": "DALL-E 3",
    "flux": "Flux",
    "flux-pro": "Flux Pro"
}

# Restricted models (premium only)
RESTRICTED_TEXT_MODELS = {"gpt-4.1", "qwen3", "deepseek-r1"}
RESTRICTED_IMAGE_MODELS = {"flux-pro"}

# Image generation limits
STANDARD_IMAGES_PER_REQUEST = 1
PREMIUM_IMAGES_PER_REQUEST = 4

async def is_user_premium(user_id: int) -> Tuple[bool, int, Optional[datetime.datetime]]:
    """
    Checks if a user is premium. Returns (is_premium, remaining_days, expires_at).
    Same logic as the bot's implementation.
    """
    print(f"[DEBUG] is_user_premium called with user_id: {user_id} (type: {type(user_id)})")
    
    if not isinstance(user_id, int):
        print(f"[DEBUG] user_id is not int, returning False")
        return False, 0, None
        
    try:
        collection = get_premium_users_collection()
        print(f"[DEBUG] Got premium users collection: {collection}")
        
        user_record = collection.find_one({"user_id": user_id, "is_premium": True})
        print(f"[DEBUG] Database query result for user {user_id}: {user_record}")
        
        if not user_record:
            print(f"[DEBUG] No premium record found for user {user_id}")
            return False, 0, None

        expires_at = user_record.get("premium_expires_at")
        if not expires_at or not isinstance(expires_at, datetime.datetime):
            logger.warning(f"User {user_id} has invalid premium_expires_at: {expires_at}")
            return False, 0, None

        now = datetime.datetime.now(datetime.timezone.utc)
        print(f"[DEBUG] Current time: {now}, expires_at: {expires_at}")
        
        if expires_at > now:
            remaining_time = expires_at - now
            # Calculate remaining_days, ensuring it's at least 1 if there's any positive time left.
            remaining_days = remaining_time.days
            if remaining_time.total_seconds() > 0 and remaining_days == 0:
                remaining_days = 1  # If less than a day but positive, count as 1 day remaining.
            elif remaining_time.days < 0:  # Should be caught by expires_at > now, but as a safeguard
                remaining_days = 0
            print(f"[DEBUG] User {user_id} is premium with {remaining_days} days remaining")
            return True, remaining_days, expires_at
        else:
            # Premium has expired, mark it in DB
            print(f"[DEBUG] User {user_id} premium has expired")
            if user_record.get("is_premium", False):
                await remove_premium_status(user_id)
            return False, 0, expires_at
    except Exception as e:
        logger.error(f"Error checking premium status for user {user_id}: {e}")
        print(f"[ERROR] Exception in is_user_premium: {e}")
        import traceback
        traceback.print_exc()
        return False, 0, None

async def add_premium_status(user_id: int, admin_id: int, days: int) -> bool:
    """
    Adds or updates a user's premium status.
    Same logic as the bot's implementation.
    """
    if not isinstance(user_id, int) or not isinstance(admin_id, int) or not isinstance(days, int):
        return False
    if days <= 0:  # Use to revoke premium manually if needed by setting days to 0 or less
        return await remove_premium_status(user_id, revoked_by_admin=True)

    try:
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
        
        get_premium_users_collection().update_one(
            {"user_id": user_id}, 
            {"$set": premium_record}, 
            upsert=True
        )
        logger.info(f"Premium status granted to user {user_id} for {days} days by admin {admin_id}")
        return True
    except Exception as e:
        logger.error(f"Error adding premium status for user {user_id}: {e}")
        return False

async def remove_premium_status(user_id: int, revoked_by_admin: bool = False) -> bool:
    """
    Marks a user as not premium. Can be called manually or by expiry checker.
    Same logic as the bot's implementation.
    """
    if not isinstance(user_id, int):
        return False
        
    try:
        update_fields = {
            "is_premium": False,
            "premium_expires_at": datetime.datetime.now(datetime.timezone.utc)  # Mark as expired now
        }
        if revoked_by_admin:
            update_fields["reason_for_removal"] = "Revoked by admin"

        result = get_premium_users_collection().update_one(
            {"user_id": user_id, "is_premium": True},
            {"$set": update_fields}
        )
        
        if result.modified_count > 0:
            logger.info(f"Premium status removed for user {user_id}")
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error removing premium status for user {user_id}: {e}")
        return False

def is_admin_user(user_id: int) -> bool:
    """Check if a user is an admin"""
    return user_id in ADMINS

async def get_user_image_limit(user_id: int) -> int:
    """Get the maximum number of images a user can generate per request"""
    is_premium, _, _ = await is_user_premium(user_id)
    is_admin = is_admin_user(user_id)
    
    if is_premium or is_admin:
        return PREMIUM_IMAGES_PER_REQUEST
    return STANDARD_IMAGES_PER_REQUEST

async def get_available_models(user_id: int) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Get available text and image models for a user based on their premium status"""
    is_premium, _, _ = await is_user_premium(user_id)
    is_admin = is_admin_user(user_id)
    
    # If user is premium or admin, return all models
    if is_premium or is_admin:
        return TEXT_MODELS, IMAGE_MODELS
    
    # Otherwise, filter out restricted models
    available_text_models = {k: v for k, v in TEXT_MODELS.items() if k not in RESTRICTED_TEXT_MODELS}
    available_image_models = {k: v for k, v in IMAGE_MODELS.items() if k not in RESTRICTED_IMAGE_MODELS}
    
    return available_text_models, available_image_models

async def get_premium_status_info(user_id: int) -> Dict[str, Any]:
    """Get comprehensive premium status information for a user"""
    is_premium, remaining_days, expires_at = await is_user_premium(user_id)
    is_admin = is_admin_user(user_id)
    
    return {
        "is_premium": is_premium,
        "is_admin": is_admin,
        "remaining_days": remaining_days,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "image_limit": await get_user_image_limit(user_id),
        "has_premium_access": is_premium or is_admin
    }

async def get_premium_benefits_message() -> str:
    """
    Returns a clean, modern premium benefits message for the webapp.
    """
    header = "💎 Unlock Premium AI Power!"
    subtitle = "Upgrade for the best AI experience, exclusive models, and more control."

    # Feature comparison
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
    
    feature_text = "\n".join([
        f"{icon} Standard: {std} | Premium: {prem}" for icon, std, prem in features
    ])

    # Premium-only models
    premium_models = [TEXT_MODELS['gpt-4.1'], TEXT_MODELS['qwen3'], IMAGE_MODELS['flux-pro']]
    premium_models_text = f"✨ Premium-Only Models: {', '.join(premium_models)}"
    
    return f"{header}\n{subtitle}\n\n{feature_text}\n\n{premium_models_text}\n\nAccess the most advanced AI and image models, only for Premium users."

def get_premium_pricing_info() -> List[Dict[str, Any]]:
    """Get premium pricing plans information"""
    return [
        {
            "name": "Weekly Access",
            "price": "₹249",
            "usd_price": "~$2.9",
            "duration": "7 days",
            "best_for": "Trial"
        },
        {
            "name": "Monthly Access",
            "price": "₹899", 
            "usd_price": "~$10.5",
            "duration": "30 days",
            "best_for": "Best Value",
            "popular": True
        },
        {
            "name": "Yearly Access",
            "price": "₹9499",
            "usd_price": "~$111.7", 
            "duration": "365 days",
            "best_for": "Ultimate Savings"
        }
    ]

async def get_all_premium_users() -> List[Dict[str, Any]]:
    """Returns a list of all users with active premium status"""
    try:
        users = list(get_premium_users_collection().find({"is_premium": True}))
        result = []
        for user in users:
            result.append({
                "user_id": user["user_id"],
                "premium_since": user.get("premium_since"),
                "premium_expires_at": user.get("premium_expires_at"),
                "granted_by": user.get("granted_by")
            })
        return result
    except Exception as e:
        logger.error(f"Error getting premium users list: {e}")
        return []

async def check_model_access(user_id: int, model_type: str, model_key: str) -> bool:
    """
    Check if a user has access to a specific model
    
    Args:
        user_id: User ID to check
        model_type: 'text' or 'image'
        model_key: Model key (e.g., 'gpt-4.1', 'flux-pro')
    
    Returns:
        True if user has access, False otherwise
    """
    is_premium, _, _ = await is_user_premium(user_id)
    is_admin = is_admin_user(user_id)
    
    if is_admin:
        return True
    
    if model_type == 'text':
        if model_key in RESTRICTED_TEXT_MODELS:
            return is_premium
    elif model_type == 'image':
        if model_key in RESTRICTED_IMAGE_MODELS:
            return is_premium
    
    return True  # Non-restricted models are available to everyone 