"""
Admin Statistics Module - Comprehensive statistics tracking for admin panel

Collects and displays statistics about users, groups, image generation,
AI responses, and system performance metrics.
"""

import time
import datetime
import os
import psutil
from typing import Dict, Any, List, Tuple
import logging
from pyrogram import Client
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from modules.core.database import get_user_collection, get_feature_settings_collection
from modules.core.database import get_user_images_collection, get_history_collection, db_service
from modules.ui.theme import Theme, Colors
from modules.lang import async_translate_to_lang
from config import START_TIME, ADMINS

# Configure logger
logger = logging.getLogger(__name__)

# Statistics cache to avoid frequent DB queries
_stats_cache = {}
_stats_last_update = 0
CACHE_VALIDITY = 60  # Cache validity in seconds

async def get_bot_statistics() -> Dict[str, Any]:
    """
    Get comprehensive bot statistics including users, groups, images, responses
    
    Returns:
        Dictionary containing all statistics
    """
    global _stats_cache, _stats_last_update
    
    # Force refresh stats by clearing cache
    _stats_cache = {}
    _stats_last_update = 0
    
    # Return cached stats if valid
    current_time = time.time()
    if _stats_cache and current_time - _stats_last_update < CACHE_VALIDITY:
        return _stats_cache
    
    # Collect fresh statistics
    stats = {}
    
    try:
        # 1. User statistics
        user_collection = get_user_collection()
        stats['total_users'] = user_collection.count_documents({'is_group': {'$ne': True}})
        
        one_day_ago = datetime.datetime.now() - datetime.timedelta(days=1)
        seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        
        # Use proper date comparison based on database structure
        stats['active_users_24h'] = user_collection.count_documents({
            'is_group': {'$ne': True},
            'last_activity': {'$gt': one_day_ago}
        })
        stats['active_users_7d'] = user_collection.count_documents({
            'is_group': {'$ne': True},
            'last_activity': {'$gt': seven_days_ago}
        })
        
        # Check both created_at and join_date fields (depending on what's used)
        new_users_query = {
            'is_group': {'$ne': True},
            '$or': [
                {'created_at': {'$gt': one_day_ago}},
                {'join_date': {'$gt': one_day_ago}}
            ]
        }
        stats['new_users_24h'] = user_collection.count_documents(new_users_query)
        
        # 2. Group statistics - fix group identification
        group_query = {'is_group': True}
        stats['total_groups'] = user_collection.count_documents(group_query)
        
        active_groups_query = {
            'is_group': True,
            'last_activity': {'$gt': seven_days_ago}
        }
        stats['active_groups_7d'] = user_collection.count_documents(active_groups_query)
        
        # 3. Image generation statistics - make more resilient
        image_collection = get_user_images_collection()
        stats['total_images_generated'] = image_collection.count_documents({})
        
        # Try different date field names that might be used
        image_date_query = {
            '$or': [
                {'created_at': {'$gt': one_day_ago}},
                {'timestamp': {'$gt': one_day_ago}},
                {'date': {'$gt': one_day_ago}}
            ]
        }
        stats['images_last_24h'] = image_collection.count_documents(image_date_query)
        
        # 4. AI response statistics - improve query
        history_collection = get_history_collection()
        
        # Try different ways to identify bot responses
        bot_response_query = {
            '$or': [
                {'is_bot': True},
                {'sender_type': 'bot'},
                {'type': 'ai_response'}
            ]
        }
        stats['total_ai_responses'] = history_collection.count_documents(bot_response_query)
        
        # Recent responses with time check
        recent_responses_query = {
            '$or': [
                {'is_bot': True, 'timestamp': {'$gt': one_day_ago}},
                {'sender_type': 'bot', 'timestamp': {'$gt': one_day_ago}},
                {'type': 'ai_response', 'timestamp': {'$gt': one_day_ago}},
                {'is_bot': True, 'created_at': {'$gt': one_day_ago}},
                {'sender_type': 'bot', 'created_at': {'$gt': one_day_ago}},
                {'type': 'ai_response', 'created_at': {'$gt': one_day_ago}}
            ]
        }
        stats['ai_responses_24h'] = history_collection.count_documents(recent_responses_query)
        
        # 5. System statistics
        stats['uptime'] = get_uptime_formatted()
        stats['cpu_usage'] = psutil.cpu_percent()
        stats['memory_usage'] = psutil.virtual_memory().percent
        
        # 6. Feature usage statistics
        voice_query = {
            '$or': [
                {'type': 'voice'},
                {'message_type': 'voice'}
            ]
        }
        stats['voice_messages_processed'] = history_collection.count_documents(voice_query)
        
        # 7. Feature toggle status
        feature_settings = get_feature_settings_collection()
        settings_doc = feature_settings.find_one({"settings_id": "global"})
        if settings_doc:
            stats['maintenance_mode'] = settings_doc.get('maintenance_mode', False)
            stats['image_generation_enabled'] = settings_doc.get('image_generation', True)
            stats['voice_features_enabled'] = settings_doc.get('voice_features', True)
            stats['ai_response_enabled'] = settings_doc.get('ai_response', True)
        
        # 8. Additional stats from run.py bot_stats if available
        try:
            from run import bot_stats
            if bot_stats:
                if 'messages_processed' in bot_stats and not stats.get('total_ai_responses'):
                    stats['total_ai_responses'] = bot_stats.get('messages_processed', 0)
                
                if 'images_generated' in bot_stats and not stats.get('total_images_generated'):
                    stats['total_images_generated'] = bot_stats.get('images_generated', 0)
                
                if 'voice_messages_processed' in bot_stats and not stats.get('voice_messages_processed'):
                    stats['voice_messages_processed'] = bot_stats.get('voice_messages_processed', 0)
                
                if 'active_users' in bot_stats:
                    stats['active_users_session'] = len(bot_stats.get('active_users', set()))
        except:
            # Not critical if this fails
            pass
            
    except Exception as e:
        logger.error(f"Error collecting statistics: {str(e)}")
        # Fill with placeholders if database queries fail
        stats = {
            'total_users': 0,
            'active_users_24h': 0,
            'active_users_7d': 0,
            'new_users_24h': 0,
            'total_groups': 0,
            'active_groups_7d': 0,
            'total_images_generated': 0,
            'images_last_24h': 0,
            'total_ai_responses': 0,
            'ai_responses_24h': 0,
            'uptime': get_uptime_formatted(),
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent,
            'voice_messages_processed': 0,
            'maintenance_mode': False,
            'image_generation_enabled': True,
            'voice_features_enabled': True,
            'ai_response_enabled': True,
            'error': str(e)
        }
    
    # Check for inconsistent data and fix it
    if stats.get('total_images_generated', 0) == 0 and stats.get('images_last_24h', 0) > 0:
        stats['total_images_generated'] = stats['images_last_24h']
    
    if stats.get('total_ai_responses', 0) == 0 and stats.get('ai_responses_24h', 0) > 0:
        stats['total_ai_responses'] = stats['ai_responses_24h']
    
    # Update cache
    _stats_cache = stats
    _stats_last_update = current_time
    
    return stats

def get_uptime_formatted() -> str:
    """Get formatted uptime string"""
    if not hasattr(time, 'START_TIME'):
        time.START_TIME = getattr(START_TIME, time.time())
    
    uptime_seconds = int(time.time() - time.START_TIME)
    
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    
    return " ".join(parts)

async def generate_stats_text(user_id: int) -> str:
    """Generate formatted statistics text"""
    stats = await get_bot_statistics()
    
    # Translate headers
    user_header = await async_translate_to_lang("👥 User Statistics", user_id)
    group_header = await async_translate_to_lang("🌐 Group Statistics", user_id)
    image_header = await async_translate_to_lang("🖼️ Image Generation", user_id)
    ai_header = await async_translate_to_lang("🤖 AI Responses", user_id)
    system_header = await async_translate_to_lang("⚙️ System Status", user_id)
    feature_header = await async_translate_to_lang("🔧 Feature Status", user_id)
    
    # Format statistics message
    message = f"📊 **Administrative Statistics Dashboard**\n\n"
    
    # 1. User Stats
    message += f"**{user_header}**\n"
    message += f"• Total Users: {stats['total_users']:,}\n"
    message += f"• Active (24h): {stats['active_users_24h']:,}\n"
    message += f"• Active (7d): {stats['active_users_7d']:,}\n"
    message += f"• New Today: {stats['new_users_24h']:,}\n"
    if stats.get('active_users_session'):
        message += f"• Current Session: {stats['active_users_session']:,}\n"
    message += "\n"
    
    # 2. Group Stats
    message += f"**{group_header}**\n"
    message += f"• Total Groups: {stats['total_groups']:,}\n"
    message += f"• Active Groups (7d): {stats['active_groups_7d']:,}\n\n"
    
    # 3. Image Stats
    message += f"**{image_header}**\n"
    message += f"• Total Generated: {stats['total_images_generated']:,}\n"
    message += f"• Generated (24h): {stats['images_last_24h']:,}\n\n"
    
    # 4. AI Stats
    message += f"**{ai_header}**\n"
    message += f"• Total Responses: {stats['total_ai_responses']:,}\n"
    message += f"• Responses (24h): {stats['ai_responses_24h']:,}\n"
    message += f"• Voice Messages: {stats['voice_messages_processed']:,}\n\n"
    
    # 5. System Stats
    message += f"**{system_header}**\n"
    message += f"• Uptime: {stats['uptime']}\n"
    message += f"• CPU: {stats['cpu_usage']}%\n"
    message += f"• Memory: {stats['memory_usage']}%\n\n"
    
    # 6. Feature Status
    message += f"**{feature_header}**\n"
    message += f"• Maintenance: {'✅' if stats.get('maintenance_mode') else '❌'}\n"
    message += f"• Image Gen: {'✅' if stats.get('image_generation_enabled') else '❌'}\n"
    message += f"• Voice: {'✅' if stats.get('voice_features_enabled') else '❌'}\n"
    message += f"• AI: {'✅' if stats.get('ai_response_enabled') else '❌'}\n"
    
    # Add error message if there was an error collecting stats
    if 'error' in stats:
        message += f"\n⚠️ Some statistics may be incomplete: {stats['error'][:50]}...\n"
    
    return message

async def handle_stats_panel(client: Client, callback: CallbackQuery):
    """Display the statistics panel to admin"""
    user_id = callback.from_user.id
    
    # Check if user is admin
    if user_id not in ADMINS:
        await callback.answer("You don't have permission to access this panel", show_alert=True)
        return
    
    # Show "loading" message while generating stats
    loading_message = await async_translate_to_lang("⏳ Loading statistics...", user_id)
    try:
        await callback.message.edit(
            text=loading_message,
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Error showing loading message: {str(e)}")
        await callback.answer("Loading statistics...", show_alert=True)
        return
    
    # Generate statistics text
    stats_text = await generate_stats_text(user_id)
    
    # Button translations
    refresh_text = await async_translate_to_lang("🔄 Refresh", user_id)
    back_text = await async_translate_to_lang("🔙 Back", user_id)
    export_text = await async_translate_to_lang("📊 Export", user_id)
    
    # Create keyboard - ensure we're creating a proper structure for InlineKeyboardMarkup
    keyboard = [
        [Theme.primary_button(refresh_text, "admin_refresh_stats")],
        [
            Theme.admin_button(export_text, "admin_export_stats"),
            Theme.back_button("admin_panel")
        ]
    ]
    
    # Show stats
    try:
        await callback.message.edit(
            text=stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error displaying statistics panel: {str(e)}")
        await callback.answer(f"Error: {str(e)[:20]}...", show_alert=True)

async def handle_refresh_stats(client: Client, callback: CallbackQuery):
    """Handle refresh stats button click"""
    user_id = callback.from_user.id
    
    # Check if user is admin
    if user_id not in ADMINS:
        await callback.answer("You don't have permission to refresh stats", show_alert=True)
        return
    
    # Clear stats cache
    global _stats_cache, _stats_last_update
    _stats_cache = {}
    _stats_last_update = 0
    
    # Show stats panel with fresh data
    await handle_stats_panel(client, callback)

async def handle_export_stats(client: Client, callback: CallbackQuery):
    """Export statistics as a text file"""
    user_id = callback.from_user.id
    
    # Check if user is admin
    if user_id not in ADMINS:
        await callback.answer("You don't have permission to export stats", show_alert=True)
        return
    
    # Generate statistics text
    stats_text = await generate_stats_text(user_id)
    
    # Generate timestamp for filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"bot_stats_{timestamp}.txt"
    filepath = os.path.join("logs", filename)
    
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Write stats to file
    with open(filepath, "w") as f:
        f.write(stats_text)
    
    # Send file to admin
    await client.send_document(
        chat_id=user_id,
        document=filepath,
        caption="📊 Bot Statistics Export"
    )
    
    # Notify in the chat
    await callback.answer("Statistics exported! Check your private messages.", show_alert=True)

# Initialize hook for START_TIME if not set
if not hasattr(time, 'START_TIME'):
    time.START_TIME = time.time() 