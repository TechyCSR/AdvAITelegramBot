"""
Statistics Database Module - Tracks and stores bot usage metrics

This module provides functions to update and retrieve various statistics about
bot usage, including message counts, user activity, image generation, etc.
"""

import datetime
import logging
from typing import Dict, Any, Optional, List, Union
from modules.core.database import db_service

# Configure logger
logger = logging.getLogger(__name__)

# Collection names
STATS_COLLECTION = "bot_statistics"
USER_STATS_COLLECTION = "user_statistics"
DAILY_STATS_COLLECTION = "daily_statistics"

# Statistics types
STAT_TYPE_MESSAGE = "message"
STAT_TYPE_IMAGE = "image"
STAT_TYPE_VOICE = "voice"
STAT_TYPE_GROUP = "group"
STAT_TYPE_NEW_USER = "new_user"
STAT_TYPE_COMMAND = "command"

async def increment_stat(stat_type: str, user_id: Optional[int] = None, 
                         group_id: Optional[int] = None, metadata: Dict[str, Any] = None) -> bool:
    """
    Increment a statistic counter and update related collections
    
    Args:
        stat_type: Type of statistic (message, image, voice, etc.)
        user_id: User ID if applicable
        group_id: Group ID if applicable
        metadata: Additional metadata to store with the stat
        
    Returns:
        Success status
    """
    try:
        # Get current timestamp
        now = datetime.datetime.now()
        today_date = now.strftime("%Y-%m-%d")
        
        # Prepare metadata
        if metadata is None:
            metadata = {}
            
        # Add timestamp and types
        metadata["timestamp"] = now
        metadata["stat_type"] = stat_type
        if user_id:
            metadata["user_id"] = user_id
        if group_id:
            metadata["group_id"] = group_id
        
        # 1. Update global stats collection
        stats_coll = db_service.get_collection(STATS_COLLECTION)
        stats_coll.update_one(
            {"stats_id": "global"},
            {"$inc": {f"total_{stat_type}": 1, "total_operations": 1}},
            upsert=True
        )
        
        # 2. Update user stats if user_id provided
        if user_id:
            user_stats_coll = db_service.get_collection(USER_STATS_COLLECTION)
            user_stats_coll.update_one(
                {"user_id": user_id},
                {
                    "$inc": {
                        f"total_{stat_type}": 1,
                        "total_operations": 1
                    },
                    "$set": {"last_activity": now}
                },
                upsert=True
            )
            
            # If this is a new user stat, update the user's created_at timestamp
            if stat_type == STAT_TYPE_NEW_USER:
                user_stats_coll.update_one(
                    {"user_id": user_id},
                    {"$set": {"created_at": now}},
                    upsert=True
                )
        
        # 3. Update daily stats
        daily_stats_coll = db_service.get_collection(DAILY_STATS_COLLECTION)
        daily_stats_coll.update_one(
            {"date": today_date},
            {"$inc": {f"{stat_type}_count": 1, "total_operations": 1}},
            upsert=True
        )
        
        # 4. Store detailed stat record for analysis
        detailed_stats_coll = db_service.get_collection(f"detailed_{stat_type}_stats")
        detailed_stats_coll.insert_one(metadata)
        
        return True
    except Exception as e:
        logger.error(f"Error incrementing stat {stat_type}: {str(e)}")
        return False

async def update_user_activity(user_id: int, username: Optional[str] = None, 
                               name: Optional[str] = None, is_group: bool = False) -> bool:
    """
    Update user activity timestamp and metadata
    
    Args:
        user_id: User or group ID
        username: Username if available
        name: User's name if available
        is_group: Whether this is a group
        
    Returns:
        Success status
    """
    try:
        now = datetime.datetime.now()
        
        # Get user collection directly
        from modules.core.database import get_user_collection
        user_coll = get_user_collection()
        
        # Build update document
        update_doc = {"$set": {"last_activity": now}}
        
        if is_group:
            update_doc["$set"]["is_group"] = True
        
        if username:
            update_doc["$set"]["username"] = username
        
        if name:
            update_doc["$set"]["name"] = name
        
        # Update the user document
        user_coll.update_one(
            {"user_id": user_id},
            update_doc,
            upsert=True
        )
        
        # Also increment activity count
        user_coll.update_one(
            {"user_id": user_id},
            {"$inc": {"activity_count": 1}}
        )
        
        return True
    except Exception as e:
        logger.error(f"Error updating user activity for {user_id}: {str(e)}")
        return False

async def record_message(user_id: int, username: Optional[str] = None, 
                         name: Optional[str] = None, is_group: bool = False,
                         group_id: Optional[int] = None, text_length: Optional[int] = None) -> bool:
    """
    Record a message sent by a user
    
    Args:
        user_id: User ID
        username: Username if available
        name: User's name if available
        is_group: Whether this is in a group
        group_id: Group ID if applicable
        text_length: Length of the message if applicable
        
    Returns:
        Success status
    """
    try:
        # Update user activity first
        await update_user_activity(user_id, username, name, is_group=False)
        
        # If in a group, update group activity too
        if is_group and group_id:
            await update_user_activity(group_id, None, None, is_group=True)
        
        # Build metadata
        metadata = {}
        if text_length:
            metadata["text_length"] = text_length
        if is_group:
            metadata["is_group"] = True
            if group_id:
                metadata["group_id"] = group_id
        
        # Increment message stat
        await increment_stat(STAT_TYPE_MESSAGE, user_id, group_id, metadata)
        
        return True
    except Exception as e:
        logger.error(f"Error recording message for {user_id}: {str(e)}")
        return False

async def record_image_generation(user_id: int, username: Optional[str] = None,
                                 name: Optional[str] = None, prompt: Optional[str] = None) -> bool:
    """
    Record an image generation request
    
    Args:
        user_id: User ID
        username: Username if available
        name: User's name if available
        prompt: Image generation prompt if available
        
    Returns:
        Success status
    """
    try:
        # Update user activity first
        await update_user_activity(user_id, username, name)
        
        # Build metadata
        metadata = {}
        if prompt:
            metadata["prompt"] = prompt
        
        # Increment image stat
        await increment_stat(STAT_TYPE_IMAGE, user_id, None, metadata)
        
        return True
    except Exception as e:
        logger.error(f"Error recording image generation for {user_id}: {str(e)}")
        return False

async def record_voice_message(user_id: int, username: Optional[str] = None,
                              name: Optional[str] = None, duration: Optional[int] = None) -> bool:
    """
    Record a voice message processed
    
    Args:
        user_id: User ID
        username: Username if available
        name: User's name if available
        duration: Voice message duration in seconds if available
        
    Returns:
        Success status
    """
    try:
        # Update user activity first
        await update_user_activity(user_id, username, name)
        
        # Build metadata
        metadata = {}
        if duration:
            metadata["duration"] = duration
        
        # Increment voice stat
        await increment_stat(STAT_TYPE_VOICE, user_id, None, metadata)
        
        return True
    except Exception as e:
        logger.error(f"Error recording voice message for {user_id}: {str(e)}")
        return False

async def record_new_user(user_id: int, username: Optional[str] = None,
                         name: Optional[str] = None) -> bool:
    """
    Record a new user joining
    
    Args:
        user_id: User ID
        username: Username if available
        name: User's name if available
        
    Returns:
        Success status
    """
    try:
        # Update user activity with join date
        now = datetime.datetime.now()
        
        # Get user collection directly
        from modules.core.database import get_user_collection
        user_coll = get_user_collection()
        
        # Check if user already exists
        existing_user = user_coll.find_one({"user_id": user_id})
        if existing_user:
            # Just update the activity
            await update_user_activity(user_id, username, name)
            return True
        
        # Build user document for new user
        user_doc = {
            "user_id": user_id,
            "created_at": now,
            "join_date": now,
            "last_activity": now,
            "activity_count": 1
        }
        
        if username:
            user_doc["username"] = username
        
        if name:
            user_doc["name"] = name
        
        # Insert the new user
        user_coll.insert_one(user_doc)
        
        # Increment new user stat
        await increment_stat(STAT_TYPE_NEW_USER, user_id, None, {})
        
        return True
    except Exception as e:
        logger.error(f"Error recording new user {user_id}: {str(e)}")
        return False

async def record_command(user_id: int, command: str, username: Optional[str] = None,
                        name: Optional[str] = None, is_group: bool = False,
                        group_id: Optional[int] = None) -> bool:
    """
    Record a command usage
    
    Args:
        user_id: User ID
        command: Command name
        username: Username if available
        name: User's name if available
        is_group: Whether this is in a group
        group_id: Group ID if applicable
        
    Returns:
        Success status
    """
    try:
        # Update user activity first
        await update_user_activity(user_id, username, name, is_group=False)
        
        # If in a group, update group activity too
        if is_group and group_id:
            await update_user_activity(group_id, None, None, is_group=True)
        
        # Build metadata
        metadata = {"command": command}
        if is_group:
            metadata["is_group"] = True
            if group_id:
                metadata["group_id"] = group_id
        
        # Increment command stat
        await increment_stat(STAT_TYPE_COMMAND, user_id, group_id, metadata)
        
        return True
    except Exception as e:
        logger.error(f"Error recording command for {user_id}: {str(e)}")
        return False

async def get_global_stats() -> Dict[str, Any]:
    """
    Get global statistics
    
    Returns:
        Dictionary of global statistics
    """
    try:
        stats_coll = db_service.get_collection(STATS_COLLECTION)
        stats_doc = stats_coll.find_one({"stats_id": "global"})
        
        if not stats_doc:
            return {
                "total_message": 0,
                "total_image": 0,
                "total_voice": 0,
                "total_new_user": 0,
                "total_command": 0,
                "total_operations": 0
            }
        
        # Remove MongoDB _id
        if "_id" in stats_doc:
            del stats_doc["_id"]
        
        return stats_doc
    except Exception as e:
        logger.error(f"Error getting global stats: {str(e)}")
        return {
            "total_message": 0,
            "total_image": 0,
            "total_voice": 0,
            "total_new_user": 0,
            "total_command": 0,
            "total_operations": 0,
            "error": str(e)
        }

async def get_daily_stats(days: int = 7) -> List[Dict[str, Any]]:
    """
    Get daily statistics for the last N days
    
    Args:
        days: Number of days to retrieve
        
    Returns:
        List of daily statistics
    """
    try:
        # Calculate date range
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)
        
        # Format dates for comparison
        start_date_str = start_date.strftime("%Y-%m-%d")
        
        # Query daily stats
        daily_stats_coll = db_service.get_collection(DAILY_STATS_COLLECTION)
        daily_stats = list(daily_stats_coll.find(
            {"date": {"$gte": start_date_str}},
            sort=[("date", 1)]  # Sort by date ascending
        ))
        
        # Remove MongoDB _id
        for stats in daily_stats:
            if "_id" in stats:
                del stats["_id"]
        
        return daily_stats
    except Exception as e:
        logger.error(f"Error getting daily stats: {str(e)}")
        return []

# Initialize collections
def init_stats_collections():
    """Initialize statistics collections with indexes"""
    try:
        # Global stats collection
        stats_coll = db_service.get_collection(STATS_COLLECTION)
        stats_coll.create_index("stats_id", unique=True)
        
        # User stats collection
        user_stats_coll = db_service.get_collection(USER_STATS_COLLECTION)
        user_stats_coll.create_index("user_id", unique=True)
        user_stats_coll.create_index("last_activity")
        
        # Daily stats collection
        daily_stats_coll = db_service.get_collection(DAILY_STATS_COLLECTION)
        daily_stats_coll.create_index("date", unique=True)
        
        # Detailed stats collections
        for stat_type in [STAT_TYPE_MESSAGE, STAT_TYPE_IMAGE, STAT_TYPE_VOICE, 
                          STAT_TYPE_GROUP, STAT_TYPE_NEW_USER, STAT_TYPE_COMMAND]:
            detailed_coll = db_service.get_collection(f"detailed_{stat_type}_stats")
            detailed_coll.create_index("timestamp")
            detailed_coll.create_index("user_id")
            if stat_type in [STAT_TYPE_MESSAGE, STAT_TYPE_COMMAND]:
                detailed_coll.create_index("group_id")
        
        logger.info("Statistics collections initialized")
        return True
    except Exception as e:
        logger.error(f"Error initializing stats collections: {str(e)}")
        return False

# Initialize indexes on import
init_stats_collections() 