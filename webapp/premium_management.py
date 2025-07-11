"""
Premium Management System for AdvAI Image Generator Webapp
Handles premium user status, benefits, and restrictions for webapp users.
Uses the same database collections as the main bot for consistency.
"""

import asyncio
import logging
from typing import Dict, Any, Tuple, Optional, List
import datetime
from database_service import DatabaseService

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database service
db_service = DatabaseService()

# Configuration constants
STANDARD_IMAGES_PER_REQUEST = 1
PREMIUM_IMAGES_PER_REQUEST = 4

# Model definitions
TEXT_MODELS = {
    "gpt-4o": "GPT-4o",
    "gpt-4.1": "GPT-4.1", 
    "qwen3": "Qwen3"
}

IMAGE_MODELS = {
    "dall-e3": "DALL-E 3",
    "flux": "Flux",
    "flux-pro": "Flux Pro"
}

# Restricted models (premium-only)
RESTRICTED_TEXT_MODELS = {"gpt-4.1", "qwen3"}
RESTRICTED_IMAGE_MODELS = {"flux-pro"}

# Admin configuration
try:
    from config import ADMINS
except ImportError:
    import os
    ADMINS = [int(x) for x in os.environ.get('ADMIN_IDS', '123456789').split(',') if x.strip().isdigit()]

def get_premium_users_collection():
    """Get the premium users collection from database"""
    return db_service.get_collection('premium_users')

class PremiumManager:
    """Simplified and robust premium management system"""
    
    @staticmethod
    def debug_log(message: str, user_id: int = None):
        """Enhanced logging for debugging"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[PREMIUM-DEBUG {timestamp}] {message}"
        if user_id:
            log_msg += f" (User: {user_id})"
        print(log_msg)
        logger.info(log_msg)
    
    @staticmethod
    async def is_user_premium_simple(user_id: int) -> Tuple[bool, int, Optional[datetime.datetime]]:
        """
        Simplified premium check - just check if user exists in premium DB and not expired
        Returns: (is_premium, remaining_days, expires_at)
        """
        PremiumManager.debug_log(f"Starting premium check", user_id)
        
        if not isinstance(user_id, int):
            PremiumManager.debug_log(f"Invalid user_id type: {type(user_id)}", user_id)
            return False, 0, None
        
        try:
            collection = get_premium_users_collection()
            PremiumManager.debug_log(f"Got collection: {collection.name if hasattr(collection, 'name') else 'Unknown'}", user_id)
            
            # Find user record
            query = {"user_id": user_id, "is_premium": True}
            PremiumManager.debug_log(f"Query: {query}", user_id)
            
            user_record = collection.find_one(query)
            PremiumManager.debug_log(f"Raw DB result: {user_record}", user_id)
            
            if not user_record:
                PremiumManager.debug_log("No premium record found", user_id)
                return False, 0, None
            
            # Check expiration
            expires_at = user_record.get("premium_expires_at")
            PremiumManager.debug_log(f"Expires at: {expires_at} (type: {type(expires_at)})", user_id)
            
            if not expires_at:
                PremiumManager.debug_log("No expiration date found", user_id)
                return False, 0, None
            
            # Ensure both times are timezone-aware
            now = datetime.datetime.now(datetime.timezone.utc)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
            
            PremiumManager.debug_log(f"Now: {now}, Expires: {expires_at}", user_id)
            
            if expires_at > now:
                remaining_time = expires_at - now
                remaining_days = max(1, remaining_time.days) if remaining_time.total_seconds() > 0 else 0
                PremiumManager.debug_log(f"User is premium with {remaining_days} days remaining", user_id)
                return True, remaining_days, expires_at
            else:
                PremiumManager.debug_log("Premium has expired", user_id)
                return False, 0, expires_at
                
        except Exception as e:
            PremiumManager.debug_log(f"Exception during premium check: {str(e)}", user_id)
            import traceback
            traceback.print_exc()
            return False, 0, None
    
    @staticmethod
    def is_admin_user(user_id: int) -> bool:
        """Check if user is admin"""
        result = user_id in ADMINS
        PremiumManager.debug_log(f"Admin check: {result} (ADMINS: {ADMINS})", user_id)
        return result
    
    @staticmethod
    async def get_comprehensive_status(user_id: int) -> Dict[str, Any]:
        """Get complete premium status with all details"""
        PremiumManager.debug_log("Getting comprehensive premium status", user_id)
        
        try:
            # Basic premium check
            is_premium, remaining_days, expires_at = await PremiumManager.is_user_premium_simple(user_id)
            is_admin = PremiumManager.is_admin_user(user_id)
            
            # Calculate privileges
            has_premium_access = is_premium or is_admin
            image_limit = PREMIUM_IMAGES_PER_REQUEST if has_premium_access else STANDARD_IMAGES_PER_REQUEST
            
            # Get available models
            if has_premium_access:
                text_models = TEXT_MODELS
                image_models = IMAGE_MODELS
            else:
                text_models = {k: v for k, v in TEXT_MODELS.items() if k not in RESTRICTED_TEXT_MODELS}
                image_models = {k: v for k, v in IMAGE_MODELS.items() if k not in RESTRICTED_IMAGE_MODELS}
            
            status = {
                "user_id": user_id,
                "is_premium": is_premium,
                "is_admin": is_admin,
                "has_premium_access": has_premium_access,
                "remaining_days": remaining_days,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "image_limit": image_limit,
                "available_text_models": text_models,
                "available_image_models": image_models,
                "debug_info": {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "premium_check_result": f"is_premium={is_premium}, days={remaining_days}",
                    "admin_check_result": f"is_admin={is_admin}",
                    "admins_list": ADMINS
                }
            }
            
            PremiumManager.debug_log(f"Final status: {status}", user_id)
            return status
            
        except Exception as e:
            PremiumManager.debug_log(f"Error in comprehensive status: {str(e)}", user_id)
            return {
                "user_id": user_id,
                "is_premium": False,
                "is_admin": False,
                "has_premium_access": False,
                "remaining_days": 0,
                "expires_at": None,
                "image_limit": STANDARD_IMAGES_PER_REQUEST,
                "available_text_models": {k: v for k, v in TEXT_MODELS.items() if k not in RESTRICTED_TEXT_MODELS},
                "available_image_models": {k: v for k, v in IMAGE_MODELS.items() if k not in RESTRICTED_IMAGE_MODELS},
                "error": str(e)
            }

# Legacy function wrappers for compatibility
async def is_user_premium(user_id: int) -> Tuple[bool, int, Optional[datetime.datetime]]:
    """Legacy wrapper for backwards compatibility"""
    return await PremiumManager.is_user_premium_simple(user_id)

async def get_premium_status_info(user_id: int) -> Dict[str, Any]:
    """Legacy wrapper for backwards compatibility"""
    return await PremiumManager.get_comprehensive_status(user_id)

def is_admin_user(user_id: int) -> bool:
    """Legacy wrapper for backwards compatibility"""
    return PremiumManager.is_admin_user(user_id)

async def get_user_image_limit(user_id: int) -> int:
    """Get user's image generation limit"""
    status = await PremiumManager.get_comprehensive_status(user_id)
    return status["image_limit"]

async def get_available_models(user_id: int) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Get available models for user"""
    status = await PremiumManager.get_comprehensive_status(user_id)
    return status["available_text_models"], status["available_image_models"]

# Additional utility functions
async def add_premium_status(user_id: int, admin_id: int, days: int) -> bool:
    """Add premium status to a user"""
    if not isinstance(user_id, int) or not isinstance(admin_id, int) or not isinstance(days, int):
        return False
    if days <= 0:
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
        PremiumManager.debug_log(f"Premium status granted for {days} days by admin {admin_id}", user_id)
        return True
    except Exception as e:
        PremiumManager.debug_log(f"Error adding premium status: {str(e)}", user_id)
        return False

async def remove_premium_status(user_id: int, revoked_by_admin: bool = False) -> bool:
    """Remove premium status from a user"""
    if not isinstance(user_id, int):
        return False
        
    try:
        update_fields = {
            "is_premium": False,
            "premium_expires_at": datetime.datetime.now(datetime.timezone.utc)
        }
        if revoked_by_admin:
            update_fields["reason_for_removal"] = "Revoked by admin"

        result = get_premium_users_collection().update_one(
            {"user_id": user_id, "is_premium": True},
            {"$set": update_fields}
        )
        
        PremiumManager.debug_log(f"Premium status removed (revoked_by_admin={revoked_by_admin})", user_id)
        return result.modified_count > 0
    except Exception as e:
        PremiumManager.debug_log(f"Error removing premium status: {str(e)}", user_id)
        return False

async def get_all_premium_users() -> List[Dict[str, Any]]:
    """Get all premium users"""
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
    """Check if user has access to a specific model"""
    status = await PremiumManager.get_comprehensive_status(user_id)
    
    if status["has_premium_access"]:
        return True
    
    if model_type == 'text':
        return model_key not in RESTRICTED_TEXT_MODELS
    elif model_type == 'image':
        return model_key not in RESTRICTED_IMAGE_MODELS
    
    return True

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

async def get_premium_benefits_message() -> str:
    """Get premium benefits message for webapp"""
    header = "💎 Unlock Premium AI Power!"
    subtitle = "Upgrade for the best AI experience, exclusive models, and more control."

    features = [
        ("🧠 AI Text Models", "GPT-4o", "GPT-4o, GPT-4.1, Qwen3"),
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

    premium_models = [TEXT_MODELS['gpt-4.1'], TEXT_MODELS['qwen3'], IMAGE_MODELS['flux-pro']]
    premium_models_text = f"✨ Premium-Only Models: {', '.join(premium_models)}"
    
    return f"{header}\n{subtitle}\n\n{feature_text}\n\n{premium_models_text}\n\nAccess the most advanced AI and image models, only for Premium users." 