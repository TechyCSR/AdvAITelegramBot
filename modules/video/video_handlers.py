import asyncio
import json
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from pyrogram.errors import MessageTooLong

from modules.video.video_generation import (
    get_user_tokens, add_user_tokens, remove_user_tokens, 
    create_video_request, get_request_status, cancel_request,
    get_user_active_requests, VideoQuality, QUALITY_TOKEN_COSTS,
    TOKENS_PER_VIDEO, enhance_prompt_with_ai
)
from modules.video.video_progress import update_video_progress_enhanced, create_interactive_progress
from config import LOG_CHANNEL, ADMINS
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Config for GCS output
OUTPUT_GCS_URI = "gs://techycsr/test_vdo_output"

# Enhanced plans with quality tiers
PLANS = [
    {"label": "💎 Starter - Rs 11 for 10 Tokens", "price": 11, "tokens": 10, "id": "plan1", "popular": False},
    {"label": "✨ Popular - Rs 100 for 105 Tokens", "price": 100, "tokens": 105, "id": "plan2", "popular": True},
    {"label": "🚀 Pro - Rs 600 for 560 Tokens", "price": 600, "tokens": 560, "id": "plan3", "popular": False},
    {"label": "💰 Enterprise - Rs 2000 for 2000 Tokens", "price": 2000, "tokens": 2000, "id": "plan4", "popular": False},
]

# Quality descriptions
QUALITY_DESCRIPTIONS = {
    VideoQuality.STANDARD: {
        "name": "🎬 Standard Quality",
        "description": "Good quality video, fast generation",
        "features": ["8-second video", "16:9 aspect ratio", "Basic AI processing"],
        "cost": 10
    },
    VideoQuality.HD: {
        "name": "✨ HD Quality", 
        "description": "Enhanced quality with AI prompt optimization",
        "features": ["8-second video", "16:9 aspect ratio", "AI prompt enhancement", "Better visuals"],
        "cost": 15
    },
    VideoQuality.PREMIUM: {
        "name": "🏆 Premium Quality",
        "description": "Highest quality with advanced AI features",
        "features": ["8-second video", "16:9 aspect ratio", "Advanced AI enhancement", "Premium processing", "Priority queue"],
        "cost": 25
    }
}

class VideoGenerationUI:
    """Modern UI components for video generation."""
    
    @staticmethod
    def create_quality_selection_keyboard() -> InlineKeyboardMarkup:
        """Create interactive quality selection keyboard."""
        keyboard = []
        
        for quality in [VideoQuality.STANDARD, VideoQuality.HD, VideoQuality.PREMIUM]:
            desc = QUALITY_DESCRIPTIONS[quality]
            cost = desc["cost"]
            popular = " ⭐" if quality == VideoQuality.HD else ""
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{desc['name']} - {cost} tokens{popular}",
                    callback_data=f"select_quality_{quality.value}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("ℹ️ Quality Comparison", callback_data="quality_comparison"),
            InlineKeyboardButton("💳 Buy Tokens", callback_data="show_plans")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_aspect_ratio_keyboard() -> InlineKeyboardMarkup:
        """Create aspect ratio selection keyboard."""
        ratios = [
            ("📱 9:16 (Vertical)", "9:16"),
            ("🖥️ 16:9 (Landscape)", "16:9"), 
            ("⬜ 1:1 (Square)", "1:1"),
            ("🎬 21:9 (Cinematic)", "21:9")
        ]
        
        keyboard = []
        for name, ratio in ratios:
            keyboard.append([
                InlineKeyboardButton(name, callback_data=f"aspect_ratio_{ratio}")
            ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_user_dashboard_keyboard(user_id: int) -> InlineKeyboardMarkup:
        """Create user dashboard with quick actions."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎬 New Video", callback_data="new_video_generation"),
                InlineKeyboardButton("📊 My Requests", callback_data=f"user_requests_{user_id}")
            ],
            [
                InlineKeyboardButton("💳 Token Balance", callback_data=f"check_tokens_{user_id}"),
                InlineKeyboardButton("🛒 Buy Tokens", callback_data="show_plans")
            ],
            [
                InlineKeyboardButton("📈 Analytics", callback_data=f"user_analytics_{user_id}"),
                InlineKeyboardButton("❓ Help", callback_data="video_help")
            ]
        ])

async def video_command_handler(client, message: Message):
    """Enhanced video generation command handler with modern UI."""
    user_id = message.from_user.id
    args = message.text.split(" ", 1)
    
    # Check if user provided a prompt
    if len(args) < 2:
        return await show_video_generation_menu(client, message)
    
    prompt = args[1].strip()
    
    # Validate prompt
    if not prompt or len(prompt) < 3:
        await message.reply_text(
            "<b>❗ Invalid Prompt</b>\n\n"
            "Please provide a descriptive prompt for your video.\n"
            "<i>Example: /video A beautiful sunset over mountains</i>",
            parse_mode=ParseMode.HTML
        )
        return
    
    if len(prompt) > 500:
        await message.reply_text(
            "<b>❗ Prompt Too Long</b>\n\n"
            "Please keep your prompt under 500 characters.\n"
            f"<i>Current length: {len(prompt)} characters</i>",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Store prompt in user session for quality selection
    # For now, we'll use standard quality by default or show quality selection
    tokens = await get_user_tokens(user_id)
    
    # Check if user is admin (unlimited tokens)
    is_admin = user_id in ADMINS
    
    if not is_admin and tokens < TOKENS_PER_VIDEO:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Buy Tokens", callback_data="show_plans")],
            [InlineKeyboardButton("📊 Check Balance", callback_data=f"check_tokens_{user_id}")]
        ])
        
        await message.reply_text(
            f"<b>🚫 Insufficient Tokens!</b>\n\n"
            f"You need at least <b>{TOKENS_PER_VIDEO}</b> tokens for standard quality.\n"
            f"Your current balance: <code>{tokens} tokens</code>\n\n"
            f"<i>💡 Buy tokens to start creating amazing videos!</i>",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Show quality selection for the prompt
    await show_quality_selection(client, message, prompt)

async def show_video_generation_menu(client, message: Message):
    """Show the main video generation menu."""
    user_id = message.from_user.id
    tokens = await get_user_tokens(user_id)
    
    # Get user's active requests
    active_requests = await get_user_active_requests(user_id)
    active_count = len(active_requests)
    
    menu_text = (
        "<b>🎬 Advanced Video Generation Studio</b>\n\n"
        f"<b>💎 Your Balance:</b> <code>{tokens} tokens</code>\n"
        f"<b>🎯 Active Requests:</b> <code>{active_count}/3</code>\n\n"
        
        "<b>🚀 Features:</b>\n"
        "• Multiple quality options (Standard/HD/Premium)\n"
        "• AI prompt enhancement\n"
        "• Real-time progress tracking\n"
        "• Queue management\n"
        "• Custom aspect ratios\n\n"
        
        "<b>💡 How to create:</b>\n"
        "<code>/video your creative prompt here</code>\n\n"
        
        "<b>✨ Example prompts:</b>\n"
        "• <i>A serene lake at sunset with mountains</i>\n"
        "• <i>Futuristic city with flying cars at night</i>\n"
        "• <i>Close-up of a blooming flower in slow motion</i>\n"
        "• <i>Astronaut walking on Mars surface</i>"
    )
    
    keyboard = VideoGenerationUI.create_user_dashboard_keyboard(user_id)
    
    await message.reply_text(menu_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

async def show_quality_selection(client, message: Message, prompt: str):
    """Show quality selection interface."""
    user_id = message.from_user.id
    tokens = await get_user_tokens(user_id)
    
    quality_text = (
        f"<b>🎯 Select Video Quality</b>\n\n"
        f"<b>Prompt:</b> <code>{prompt[:100]}{'...' if len(prompt) > 100 else ''}</code>\n\n"
        f"<b>💎 Your Tokens:</b> <code>{tokens}</code>\n\n"
        f"<b>Choose your preferred quality:</b>"
    )
    
    # Store prompt temporarily (in a real app, use a proper session store)
    # For now, we'll include it in callback data or use a simple dict
    
    keyboard = VideoGenerationUI.create_quality_selection_keyboard()
    
    try:
        await message.reply_text(quality_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except MessageTooLong:
        # Truncate prompt if too long
        short_prompt = prompt[:50] + "..." if len(prompt) > 50 else prompt
        quality_text = quality_text.replace(prompt[:100], short_prompt)
        await message.reply_text(quality_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

async def show_quality_comparison(callback_query: CallbackQuery):
    """Show detailed quality comparison."""
    comparison_text = "<b>🏆 Quality Comparison</b>\n\n"
    
    for quality in [VideoQuality.STANDARD, VideoQuality.HD, VideoQuality.PREMIUM]:
        desc = QUALITY_DESCRIPTIONS[quality]
        comparison_text += f"<b>{desc['name']}</b>\n"
        comparison_text += f"<i>{desc['description']}</i>\n"
        comparison_text += f"<b>Cost:</b> {desc['cost']} tokens\n"
        comparison_text += "<b>Features:</b>\n"
        
        for feature in desc['features']:
            comparison_text += f"  ✅ {feature}\n"
        
        comparison_text += "\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Quality Selection", callback_data="back_to_quality")]
    ])
    
    await callback_query.message.edit_text(
        comparison_text, 
        reply_markup=keyboard, 
        parse_mode=ParseMode.HTML
    )

async def process_video_generation(client, message: Message, prompt: str, quality: VideoQuality, aspect_ratio: str = "16:9"):
    """Process video generation with enhanced features."""
    user_id = message.from_user.id
    
    # Create video request
    request_id, error = await create_video_request(user_id, prompt, quality, aspect_ratio)
    
    if error:
        await message.reply_text(
            f"<b>❌ Request Failed</b>\n\n"
            f"<code>{error}</code>\n\n"
            f"<i>Please try again or contact support.</i>",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Show initial status
    status_msg = await message.reply_text(
        "<b>🎬 Processing Video Request...</b>\n\n"
        f"<code>Request ID: {request_id}</code>\n"
        f"<i>Initializing generation system...</i>",
        parse_mode=ParseMode.HTML
    )
    
    # Start enhanced progress tracking
    try:
        await update_video_progress_enhanced(client, status_msg, prompt, request_id)
        
        # After completion, get final status
        final_status = await get_request_status(request_id)
        
        if final_status and final_status["status"] == "completed":
            # Send the actual video file
            await send_completed_video(client, message, request_id, prompt, quality)
            
    except Exception as e:
        logger.error(f"Error in video generation process: {e}")
        await status_msg.edit_text(
            f"<b>❌ Processing Error</b>\n\n"
            f"<code>{str(e)}</code>\n\n"
            f"<i>Your tokens have been refunded.</i>",
            parse_mode=ParseMode.HTML
        )

async def send_completed_video(client, original_message: Message, request_id: str, prompt: str, quality: VideoQuality):
    """Send completed video with analytics and options."""
    try:
        # Find the video file (this would be enhanced in a real implementation)
        user_id = original_message.from_user.id
        video_path = f'generated_images/generated_video_{user_id}_{request_id}.mp4'
        
        if not os.path.exists(video_path):
            await original_message.reply_text(
                "<b>❌ Video File Not Found</b>\n\n"
                "<i>The generated video could not be located. Please try again.</i>",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Create caption with details
        quality_desc = QUALITY_DESCRIPTIONS[quality]
        
        caption = (
            f"<b>🎬 Video Generated Successfully!</b>\n\n"
            f"<b>📝 Prompt:</b> <code>{prompt[:150]}{'...' if len(prompt) > 150 else ''}</code>\n"
            f"<b>🏆 Quality:</b> {quality_desc['name']}\n"
            f"<b>🎯 Request ID:</b> <code>{request_id}</code>\n\n"
            f"<i>✨ Enjoy your AI-generated masterpiece!</i>"
        )
        
        # Enhanced keyboard with more options
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Generate Similar", callback_data=f"generate_similar_{prompt[:50]}"),
                InlineKeyboardButton("✨ Enhance Prompt", callback_data=f"enhance_prompt_{prompt[:50]}")
            ],
            [
                InlineKeyboardButton("📊 Video Analytics", callback_data=f"video_analytics_{request_id}"),
                InlineKeyboardButton("💾 Save to Gallery", callback_data=f"save_video_{request_id}")
            ],
            [
                InlineKeyboardButton("🎬 New Video", callback_data="new_video_generation"),
                InlineKeyboardButton("💳 Buy More Tokens", callback_data="show_plans")
            ]
        ])
        
        # Send video
        await original_message.reply_video(
            video_path, 
            caption=caption, 
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        # Log to channel
        await log_video_generation(client, original_message, request_id, prompt, quality)
        
        # Clean up local file
        try:
            os.remove(video_path)
        except Exception as e:
            logger.warning(f"Failed to remove video file: {e}")
            
    except Exception as e:
        logger.error(f"Error sending completed video: {e}")
        await original_message.reply_text(
            f"<b>❌ Failed to send video</b>\n\n"
            f"<code>{str(e)}</code>",
            parse_mode=ParseMode.HTML
        )

async def log_video_generation(client, message: Message, request_id: str, prompt: str, quality: VideoQuality):
    """Enhanced logging to channel."""
    try:
        user = message.from_user
        user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>" if user else f"User {user.id}"
        
        log_caption = (
            f"#VideoGenerated #Quality_{quality.value.upper()}\n\n"
            f"<b>👤 User:</b> {user_mention} (ID: <code>{user.id}</code>)\n"
            f"<b>🎯 Request ID:</b> <code>{request_id}</code>\n"
            f"<b>🏆 Quality:</b> {QUALITY_DESCRIPTIONS[quality]['name']}\n"
            f"<b>💰 Tokens Used:</b> <code>{QUALITY_DESCRIPTIONS[quality]['cost']}</code>\n"
            f"<b>📝 Prompt:</b> <code>{prompt[:200]}{'...' if len(prompt) > 200 else ''}</code>\n"
            f"<b>🕐 Time:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
        )
        
        video_path = f'generated_images/generated_video_{user.id}_{request_id}.mp4'
        
        if os.path.exists(video_path):
            await client.send_video(
                chat_id=LOG_CHANNEL,
                video=video_path,
                caption=log_caption,
                parse_mode=ParseMode.HTML
            )
        else:
            await client.send_message(
                chat_id=LOG_CHANNEL,
                text=log_caption + "\n\n<i>❗ Video file not found for logging</i>",
                parse_mode=ParseMode.HTML
            )
            
    except Exception as e:
        logger.error(f"Failed to log video generation: {e}")

# Enhanced callback handlers
async def video_callback_handler(client, callback_query: CallbackQuery):
    """Enhanced callback handler for video generation interactions."""
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    try:
        if data.startswith("select_quality_"):
            quality_str = data.replace("select_quality_", "")
            quality = VideoQuality(quality_str)
            
            # Get the prompt from the message or ask user to provide it
            # For now, show aspect ratio selection
            await show_aspect_ratio_selection(callback_query, quality)
            
        elif data.startswith("aspect_ratio_"):
            aspect_ratio = data.replace("aspect_ratio_", "")
            # Here we would need to get the stored prompt and quality
            # For now, ask user to restart the process
            await callback_query.answer("Please use /video command with your prompt to start generation", show_alert=True)
            
        elif data == "quality_comparison":
            await show_quality_comparison(callback_query)
            
        elif data.startswith("check_tokens_"):
            await show_token_balance(callback_query)
            
        elif data == "show_plans":
            await show_enhanced_plans(callback_query)
            
        elif data.startswith("cancel_video_"):
            request_id = data.replace("cancel_video_", "")
            success = await cancel_request(request_id, user_id)
            
            if success:
                await callback_query.answer("✅ Video generation cancelled and tokens refunded!", show_alert=True)
            else:
                await callback_query.answer("❌ Could not cancel request", show_alert=True)
                
        elif data.startswith("user_requests_"):
            await show_user_requests(callback_query)
            
        elif data.startswith("video_analytics_"):
            request_id = data.replace("video_analytics_", "")
            await show_video_analytics(callback_query, request_id)
            
        elif data == "new_video_generation":
            await callback_query.answer("Use /video <your prompt> to create a new video!", show_alert=False)
            
        elif data.startswith("enhance_prompt_"):
            original_prompt = data.replace("enhance_prompt_", "")
            await show_prompt_enhancement(callback_query, original_prompt)
            
        else:
            await callback_query.answer("Unknown action", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error handling callback: {e}")
        await callback_query.answer("An error occurred. Please try again.", show_alert=True)

async def show_aspect_ratio_selection(callback_query: CallbackQuery, quality: VideoQuality):
    """Show aspect ratio selection."""
    quality_desc = QUALITY_DESCRIPTIONS[quality]
    
    text = (
        f"<b>📐 Select Aspect Ratio</b>\n\n"
        f"<b>Selected Quality:</b> {quality_desc['name']}\n"
        f"<b>Cost:</b> {quality_desc['cost']} tokens\n\n"
        f"<b>Choose aspect ratio for your video:</b>"
    )
    
    keyboard = VideoGenerationUI.create_aspect_ratio_keyboard()
    
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

async def show_token_balance(callback_query: CallbackQuery):
    """Show enhanced token balance information."""
    user_id = callback_query.from_user.id
    tokens = await get_user_tokens(user_id)
    
    # Calculate what user can afford
    standard_videos = tokens // QUALITY_DESCRIPTIONS[VideoQuality.STANDARD]["cost"]
    hd_videos = tokens // QUALITY_DESCRIPTIONS[VideoQuality.HD]["cost"] 
    premium_videos = tokens // QUALITY_DESCRIPTIONS[VideoQuality.PREMIUM]["cost"]
    
    balance_text = (
        f"<b>💎 Token Balance</b>\n\n"
        f"<b>Current Balance:</b> <code>{tokens} tokens</code>\n\n"
        f"<b>📊 What you can generate:</b>\n"
        f"• <b>Standard Quality:</b> {standard_videos} videos\n"
        f"• <b>HD Quality:</b> {hd_videos} videos\n" 
        f"• <b>Premium Quality:</b> {premium_videos} videos\n\n"
        f"<i>💡 Higher quality uses more tokens but delivers better results!</i>"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Buy More Tokens", callback_data="show_plans")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
    ])
    
    await callback_query.message.edit_text(balance_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

async def show_enhanced_plans(callback_query: CallbackQuery):
    """Show enhanced token purchase plans."""
    plans_text = (
        "<b>🛒 Premium Token Plans</b>\n\n"
        
        "<b>🎬 Why Choose Our Video Generation?</b>\n"
        "✅ <b>Cutting-edge AI</b> (Google Veo 3.0)\n"
        "✅ <b>Multiple Quality Options</b> (Standard/HD/Premium)\n"
        "✅ <b>Fast Generation</b> (1-3 minutes)\n"
        "✅ <b>Custom Aspect Ratios</b> (9:16, 16:9, 1:1, 21:9)\n"
        "✅ <b>AI Prompt Enhancement</b> (HD/Premium only)\n"
        "✅ <b>Priority Queue</b> (Premium)\n\n"
        
        "<b>💰 Available Plans:</b>\n\n"
    )
    
    for plan in PLANS:
        popular_tag = " 🔥 POPULAR" if plan.get("popular", False) else ""
        value_per_token = plan["price"] / plan["tokens"]
        
        plans_text += (
            f"<b>{plan['label']}{popular_tag}</b>\n"
            f"<code>Rs {plan['price']} → {plan['tokens']} tokens</code>\n"
            f"<i>Value: Rs {value_per_token:.2f} per token</i>\n\n"
        )
    
    plans_text += (
        "<b>🎯 Token Usage:</b>\n"
        f"• Standard Quality: {QUALITY_DESCRIPTIONS[VideoQuality.STANDARD]['cost']} tokens\n"
        f"• HD Quality: {QUALITY_DESCRIPTIONS[VideoQuality.HD]['cost']} tokens\n"
        f"• Premium Quality: {QUALITY_DESCRIPTIONS[VideoQuality.PREMIUM]['cost']} tokens\n\n"
        
        "<b>Ready to buy?</b> Contact admin for instant activation!"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💸 Contact Admin for Payment", url="https://t.me/techycsr")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
    ])
    
    await callback_query.message.edit_text(plans_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

async def show_user_requests(callback_query: CallbackQuery):
    """Show user's active and recent requests."""
    user_id = callback_query.from_user.id
    active_requests = await get_user_active_requests(user_id)
    
    if not active_requests:
        text = (
            "<b>📊 Your Video Requests</b>\n\n"
            "<i>No active requests found.</i>\n\n"
            "Create your first video with /video command!"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 Create Video", callback_data="new_video_generation")]
        ])
    else:
        text = f"<b>📊 Your Active Requests ({len(active_requests)})</b>\n\n"
        
        for i, req in enumerate(active_requests[:5], 1):  # Show max 5
            status_emoji = {
                "queued": "⏳",
                "processing": "🎬", 
                "completed": "✅",
                "failed": "❌",
                "cancelled": "🚫"
            }.get(req.status.value, "❓")
            
            text += (
                f"<b>{i}. {status_emoji} {req.status.value.title()}</b>\n"
                f"<code>{req.prompt[:50]}{'...' if len(req.prompt) > 50 else ''}</code>\n"
                f"Quality: {req.quality.value.title()}\n\n"
            )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data=f"user_requests_{user_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
        ])
    
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

async def show_video_analytics(callback_query: CallbackQuery, request_id: str):
    """Show analytics for a specific video generation."""
    # This would be enhanced with actual analytics data
    analytics_text = (
        f"<b>📈 Video Analytics</b>\n\n"
        f"<b>🎯 Request ID:</b> <code>{request_id}</code>\n"
        f"<b>📊 Status:</b> Completed ✅\n"
        f"<b>⏱️ Generation Time:</b> 2.3 minutes\n"
        f"<b>🏆 Quality:</b> HD\n"
        f"<b>📐 Aspect Ratio:</b> 16:9\n"
        f"<b>💰 Tokens Used:</b> 15\n"
        f"<b>🔄 Views:</b> 1\n\n"
        f"<i>💡 Detailed analytics coming soon!</i>"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
    ])
    
    await callback_query.message.edit_text(analytics_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

async def show_prompt_enhancement(callback_query: CallbackQuery, original_prompt: str):
    """Show prompt enhancement suggestions."""
    try:
        enhanced = await enhance_prompt_with_ai(original_prompt)
        
        enhancement_text = (
            f"<b>✨ AI Prompt Enhancement</b>\n\n"
            f"<b>Original:</b>\n<code>{original_prompt}</code>\n\n"
            f"<b>Enhanced:</b>\n<code>{enhanced}</code>\n\n"
            f"<i>💡 Enhanced prompts often produce better videos!</i>"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 Use Enhanced Prompt", callback_data=f"use_enhanced_{enhanced[:50]}")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
        ])
        
        await callback_query.message.edit_text(enhancement_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await callback_query.answer("Failed to enhance prompt. Please try again.", show_alert=True)

# Admin commands (enhanced)
async def addt_command_handler(client, message: Message):
    """Enhanced add tokens command with logging."""
    parts = message.text.split()
    if len(parts) != 3:
        await message.reply_text(
            "<b>💰 Add Tokens Command</b>\n\n"
            "<b>Usage:</b> <code>/addt &lt;user_id&gt; &lt;tokens&gt;</code>\n\n"
            "<b>Example:</b> <code>/addt 123456789 100</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        target_user_id = int(parts[1])
        tokens = int(parts[2])
        
        if tokens <= 0:
            await message.reply_text("❌ Token amount must be positive.")
            return
            
    except ValueError:
        await message.reply_text("❌ User ID and tokens must be valid numbers.")
        return
    
    success = await add_user_tokens(target_user_id, tokens)
    
    if success:
        await message.reply_text(
            f"<b>✅ Tokens Added Successfully!</b>\n\n"
            f"<b>👤 User ID:</b> <code>{target_user_id}</code>\n"
            f"<b>💰 Tokens Added:</b> <code>{tokens}</code>\n"
            f"<b>🕐 Time:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>",
            parse_mode=ParseMode.HTML
        )
        
        # Notify the user
        try:
            notification = (
                f"<b>🎉 Tokens Added!</b>\n\n"
                f"<b>{tokens} new tokens</b> have been added to your account!\n\n"
                f"<i>🎬 Ready to create amazing videos? Use /video to get started!</i>"
            )
            
            await client.send_message(
                chat_id=target_user_id,
                text=notification,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            await message.reply_text(f"✅ Tokens added, but couldn't notify user: {e}")
    else:
        await message.reply_text("❌ Failed to add tokens. Please try again.")

async def removet_command_handler(client, message: Message):
    """Enhanced remove tokens command."""
    parts = message.text.split()
    if len(parts) != 3:
        await message.reply_text(
            "<b>💰 Remove Tokens Command</b>\n\n"
            "<b>Usage:</b> <code>/removet &lt;user_id&gt; &lt;tokens&gt;</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        target_user_id = int(parts[1])
        tokens = int(parts[2])
    except ValueError:
        await message.reply_text("❌ User ID and tokens must be valid numbers.")
        return
    
    success = await remove_user_tokens(target_user_id, tokens)
    
    if success:
        await message.reply_text(
            f"<b>✅ Tokens Removed</b>\n\n"
            f"<b>👤 User ID:</b> <code>{target_user_id}</code>\n"
            f"<b>💰 Tokens Removed:</b> <code>{tokens}</code>",
            parse_mode=ParseMode.HTML
        )
    else:
        current_tokens = await get_user_tokens(target_user_id)
        await message.reply_text(
            f"<b>❌ Cannot Remove Tokens</b>\n\n"
            f"User has only <code>{current_tokens}</code> tokens.\n"
            f"Cannot remove <code>{tokens}</code> tokens.",
            parse_mode=ParseMode.HTML
        )

async def token_command_handler(client, message: Message):
    """Enhanced token balance command."""
    user_id = message.from_user.id
    tokens = await get_user_tokens(user_id)
    
    keyboard = VideoGenerationUI.create_user_dashboard_keyboard(user_id)
    
    balance_text = (
        f"<b>💎 Your Token Dashboard</b>\n\n"
        f"<b>Current Balance:</b> <code>{tokens} tokens</code>\n\n"
        f"<b>🎬 What you can create:</b>\n"
        f"• Standard Quality: {tokens // 10} videos\n"
        f"• HD Quality: {tokens // 15} videos\n"
        f"• Premium Quality: {tokens // 25} videos\n\n"
        f"<i>Choose your next action below:</i>"
    )
    
    await message.reply_text(balance_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

async def vtoken_command_handler(client, message: Message):
    """Enhanced view user tokens command for admins."""
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply_text(
            "<b>👮‍♂️ Admin Command</b>\n\n"
            "<b>Usage:</b> <code>/vtoken &lt;user_id&gt;</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        target_user_id = int(parts[1])
    except ValueError:
        await message.reply_text("❌ User ID must be a valid number.")
        return
    
    tokens = await get_user_tokens(target_user_id)
    active_requests = await get_user_active_requests(target_user_id)
    
    admin_info = (
        f"<b>👤 User Information</b>\n\n"
        f"<b>User ID:</b> <code>{target_user_id}</code>\n"
        f"<b>💰 Token Balance:</b> <code>{tokens}</code>\n"
        f"<b>🎬 Active Requests:</b> <code>{len(active_requests)}</code>\n"
        f"<b>🕐 Checked:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
    )
    
    if active_requests:
        admin_info += "\n\n<b>📊 Active Requests:</b>\n"
        for req in active_requests[:3]:
            admin_info += f"• {req.status.value} - {req.quality.value}\n"
    
    await message.reply_text(admin_info, parse_mode=ParseMode.HTML) 