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
    generate_video_direct, get_request_status, cancel_request,
    get_user_active_requests, VideoQuality, QUALITY_TOKEN_COSTS,
    TOKENS_PER_VIDEO, enhance_prompt_with_ai
)
# Removed video progress imports since we're using direct generation
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

# Updated quality descriptions - only Premium now
QUALITY_DESCRIPTIONS = {
    VideoQuality.PREMIUM: {
        "name": "🏆 Premium Quality",
        "description": "High quality video with advanced AI features",
        "features": ["8-second video", "16:9 aspect ratio", "Advanced AI enhancement", "Premium processing", "Priority queue"],
        "cost": 10  # All videos cost 10 tokens now
    }
}

class VideoGenerationUI:
    """Modern UI components for video generation."""
    
    @staticmethod
    def create_quality_selection_keyboard() -> InlineKeyboardMarkup:
        """Create interactive quality selection keyboard - simplified for Premium only."""
        quality = VideoQuality.PREMIUM
        desc = QUALITY_DESCRIPTIONS[quality]
        cost = desc["cost"]
        
        keyboard = [
            [InlineKeyboardButton(
                f"{desc['name']} - {cost} tokens",
                callback_data=f"select_quality_{quality.value}"
            )],
            [
                InlineKeyboardButton("ℹ️ Quality Info", callback_data="quality_comparison"),
                InlineKeyboardButton("💳 Buy Tokens", callback_data="show_plans")
            ]
        ]
        
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
    def create_user_dashboard_keyboard(user_id: int, show_new_video: bool = True) -> InlineKeyboardMarkup:
        """Create user dashboard with quick actions - simplified."""
        keyboard_rows = []
        
        # First row - just token balance and buy tokens
        keyboard_rows.append([
            InlineKeyboardButton("💳 Token Balance", callback_data=f"check_tokens_{user_id}"),
            InlineKeyboardButton("🛒 Buy Tokens", callback_data="show_plans")
        ])
        
        # Second row - just help
        keyboard_rows.append([
            InlineKeyboardButton("❓ Help", callback_data="video_help")
        ])
        
        return InlineKeyboardMarkup(keyboard_rows)

async def video_command_handler(client, message: Message):
    """Enhanced video generation command handler with modern UI."""
    try:
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
                f"You need at least <b>{TOKENS_PER_VIDEO}</b> tokens to generate a video.\n"
                f"Your current balance: <code>{tokens} tokens</code>\n\n"
                f"<i>💡 Buy tokens to start creating amazing videos!</i>",
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            return
        
        # Directly start video generation with Premium quality
        await process_video_generation(client, message, prompt, VideoQuality.PREMIUM, "16:9")
        
    except Exception as e:
        logger.error(f"Error in video command handler: {e}")
        await message.reply_text(
            f"<b>❌ Command Error</b>\n\n"
            f"<code>{str(e)}</code>\n\n"
            f"<i>Please try again or contact support.</i>",
            parse_mode=ParseMode.HTML
        )

async def show_video_generation_menu(client, message: Message):
    """Show the main video generation menu - simplified."""
    try:
        user_id = message.from_user.id
        tokens = await get_user_tokens(user_id)
        
        menu_text = (
            "<b>🎬 AI Video Generation Studio</b>\n\n"
            f"<b>💎 Your Balance:</b> <code>{tokens} tokens</code>\n\n"
            
            "<b>🚀 Features:</b>\n"
            "• Premium quality videos (10 tokens each)\n"
            "• AI prompt enhancement\n"
            "• Real-time progress tracking\n"
            "• Multiple aspect ratios\n\n"
            
            "<b>💡 How to create:</b>\n"
            "<code>/video your creative prompt here</code>\n\n"
            
            "<b>✨ Example prompts:</b>\n"
            "• <i>A serene lake at sunset with mountains</i>\n"
            "• <i>Futuristic city with flying cars at night</i>\n"
            "• <i>Close-up of a blooming flower in slow motion</i>\n"
            "• <i>Astronaut walking on Mars surface</i>"
        )
        
        keyboard = VideoGenerationUI.create_user_dashboard_keyboard(user_id, show_new_video=False)
        
        await message.reply_text(menu_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error showing video generation menu: {e}")
        await message.reply_text("❌ Error loading menu. Please try again.")



async def process_video_generation(client, message: Message, prompt: str, quality: VideoQuality, aspect_ratio: str = "16:9"):
    """Process video generation with direct generation - no queue system."""
    try:
        user_id = message.from_user.id
        
        # Show initial status with direct generation approach - no request ID
        status_msg = await message.reply_text(
            "<b>🎬 Starting Video Generation...</b>\n\n"
            f"<b>📝 Prompt:</b> <code>{prompt[:120]}{'...' if len(prompt) > 120 else ''}</code>\n\n"
            f"<b>Progress:</b> <code>0%</code> - Initializing...\n\n"
            f"<i>🚀 Creating your amazing video...</i>",
            parse_mode=ParseMode.HTML
        )
        
        # Start direct video generation
        try:
            # Start generation in background and track progress
            import asyncio
            generation_task = asyncio.create_task(
                generate_video_direct(user_id, prompt, quality, aspect_ratio)
            )
            
            # Create a temporary request ID for progress tracking
            temp_request_id = f"temp_{user_id}_{int(time.time())}"
            
            # Track progress while generation is running
            progress = 0
            while not generation_task.done():
                try:
                    # Update progress display
                    progress = min(progress + 5, 95)
                    
                    # Determine current stage
                    if progress < 20:
                        stage = "Initializing AI systems"
                        emoji = "🚀"
                    elif progress < 40:
                        stage = "Processing your prompt"
                        emoji = "🧠"
                    elif progress < 60:
                        stage = "Generating video content"
                        emoji = "🎨"
                    elif progress < 80:
                        stage = "Adding final touches"
                        emoji = "✨"
                    else:
                        stage = "Almost ready"
                        emoji = "🎬"
                    
                    progress_text = (
                        f"<b>{emoji} {stage}</b>\n\n"
                        f"<b>📝 Prompt:</b> <code>{prompt[:100]}{'...' if len(prompt) > 100 else ''}</code>\n\n"
                        f"<b>Progress:</b> <code>{progress}%</code>\n\n"
                        f"<i>Creating your amazing video...</i>"
                    )
                    
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton(f"📊 {progress}% Completed", callback_data=f"progress_info_{progress}")]
                    ])
                    
                    try:
                        await status_msg.edit_text(progress_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
                    except Exception as e:
                        # If edit fails, just continue
                        pass
                    
                    # Wait before next update
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"Error updating progress: {e}")
                    await asyncio.sleep(2)
            
            # Get the result
            video_path, error, progress_data = await generation_task
            
            if error:
                # Generation failed
                await status_msg.edit_text(
                    f"<b>❌ Video Generation Failed</b>\n\n"
                    f"<b>📝 Prompt:</b> <code>{prompt[:100]}{'...' if len(prompt) > 100 else ''}</code>\n\n"
                    f"<b>❗ Error:</b> <code>{error}</code>\n\n"
                    f"<i>💡 Your tokens have been refunded. Please try again.</i>",
                    parse_mode=ParseMode.HTML
                )
                return
            
            if video_path and os.path.exists(video_path):
                # Generation successful - update status to completion
                await status_msg.edit_text(
                    f"<b>🎉 Video Generation Complete!</b>\n\n"
                    f"<b>📝 Prompt:</b> <code>{prompt[:100]}{'...' if len(prompt) > 100 else ''}</code>\n\n"
                    f"<b>📊 Progress:</b> <code>100%</code> ✅\n\n"
                    f"<i>🎬 Delivering your masterpiece...</i>",
                    parse_mode=ParseMode.HTML
                )
                
                # Send the completed video
                await send_completed_video_direct(client, message, video_path, prompt, quality)
                
            else:
                await status_msg.edit_text(
                    f"<b>❌ Video File Error</b>\n\n"
                    f"<b>📝 Prompt:</b> <code>{prompt[:100]}{'...' if len(prompt) > 100 else ''}</code>\n\n"
                    f"<i>Video was generated but file could not be found. Your tokens have been refunded.</i>",
                    parse_mode=ParseMode.HTML
                )
                
        except Exception as e:
            logger.error(f"Error in direct video generation process: {e}")
            await status_msg.edit_text(
                f"<b>❌ Processing Error</b>\n\n"
                f"<code>{str(e)}</code>\n\n"
                f"<i>Your tokens have been refunded.</i>",
                parse_mode=ParseMode.HTML
            )
    
    except Exception as e:
        logger.error(f"Error processing video generation: {e}")
        await message.reply_text(
            f"<b>❌ Generation Error</b>\n\n"
            f"<code>{str(e)}</code>",
            parse_mode=ParseMode.HTML
        )

async def send_completed_video_direct(client, original_message: Message, video_path: str, prompt: str, quality: VideoQuality):
    """Send completed video directly with simplified options."""
    try:
        user_id = original_message.from_user.id
        
        # Create caption with details - trim if too long for Telegram - no request ID
        quality_desc = QUALITY_DESCRIPTIONS[quality]
        
        # Calculate maximum prompt length (Telegram caption limit is 1024 chars)
        base_caption = (
            f"<b>🎬 Video Generated Successfully!</b>\n\n"
            f"<b>📝 Prompt:</b> "
        )
        end_caption = (
            f"\n<b>🏆 Quality:</b> {quality_desc['name']}\n"
            f"<b>💰 Tokens Used:</b> {quality_desc['cost']}\n\n"
            f"<i>✨ Enjoy your AI-generated masterpiece!</i>"
        )
        
        # Calculate available space for prompt
        available_space = 1024 - len(base_caption) - len(end_caption) - 20  # 20 chars buffer
        
        # Trim prompt if necessary
        if len(prompt) > available_space:
            trimmed_prompt = prompt[:available_space-3] + "..."
        else:
            trimmed_prompt = prompt
        
        caption = base_caption + f"<code>{trimmed_prompt}</code>" + end_caption
        
        # # Simplified keyboard - just generate similar and buy tokens
        # keyboard = InlineKeyboardMarkup([
        #     [
        #         InlineKeyboardButton("🔄 Generate Similar", callback_data=f"generate_similar_{prompt[:50]}"),
        #         InlineKeyboardButton("💳 Buy More Tokens", callback_data="show_plans")
        #     ]
        # ])
        
        # Send video
        await original_message.reply_video(
            video_path, 
            caption=caption, 
            parse_mode=ParseMode.HTML
        )
        
        # Log to channel (simplified without request_id)
        await log_video_generation_direct(client, original_message, prompt, quality)
        
        # Clean up local file
        try:
            os.remove(video_path)
            logger.info(f"Cleaned up video file: {video_path}")
        except Exception as e:
            logger.warning(f"Failed to remove video file: {e}")
            
    except Exception as e:
        logger.error(f"Error sending completed video: {e}")
        await original_message.reply_text(
            f"<b>❌ Failed to send video</b>\n\n"
            f"<code>{str(e)}</code>",
            parse_mode=ParseMode.HTML
        )

async def log_video_generation_direct(client, message: Message, prompt: str, quality: VideoQuality):
    """Enhanced logging to channel - simplified."""
    try:
        user = message.from_user
        user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>" if user else f"User {user.id}"
        
        log_caption = (
            f"#VideoGenerated #Quality_{quality.value.upper()}\n\n"
            f"<b>👤 User:</b> {user_mention} (ID: <code>{user.id}</code>)\n"
            f"<b>🏆 Quality:</b> {QUALITY_DESCRIPTIONS[quality]['name']}\n"
            f"<b>💰 Tokens Used:</b> <code>{QUALITY_DESCRIPTIONS[quality]['cost']}</code>\n"
            f"<b>📝 Prompt:</b> <code>{prompt[:200]}{'...' if len(prompt) > 200 else ''}</code>\n"
            f"<b>🕐 Time:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
        )
        
        await client.send_message(
            chat_id=LOG_CHANNEL,
            text=log_caption,
            parse_mode=ParseMode.HTML
        )
            
    except Exception as e:
        logger.error(f"Failed to log video generation: {e}")

# Enhanced callback handlers
async def video_callback_handler(client, callback_query: CallbackQuery):
    """Enhanced callback handler for video generation interactions - simplified."""
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    try:
        if data.startswith("progress_info_"):
            progress = data.replace("progress_info_", "")
            await callback_query.answer(f"🎬 Your video is {progress}% completed. Please keep patience, we're working on it!", show_alert=True)
            return
        
        if data.startswith("progress_check_"):
            request_id = data.replace("progress_check_", "")
            
            # Get current status
            status = await get_request_status(request_id)
            
            if status:
                progress = status.get("progress", 0)
                current_status = status["status"]
                
                if current_status == "completed":
                    await callback_query.answer("🎉 Your video is 100% complete and ready!", show_alert=True)
                elif current_status == "processing":
                    await callback_query.answer(f"⏳ Your video is {progress}% completed. Please keep patience, we're working on it!", show_alert=True)
                elif current_status == "failed":
                    await callback_query.answer("❌ Video generation failed. Your tokens have been refunded.", show_alert=True)
                else:
                    await callback_query.answer(f"📊 Current progress: {progress}%. Please wait...", show_alert=True)
            else:
                await callback_query.answer("❌ Unable to check progress. Please try again.", show_alert=True)
            return
        
        await callback_query.answer()  # Always answer the callback first
        
        if data.startswith("check_tokens_"):
            await show_token_balance(callback_query)
            
        elif data == "show_plans":
            await show_enhanced_plans(callback_query)
                
        elif data.startswith("generate_similar_"):
            prompt = data.replace("generate_similar_", "")
            await callback_query.answer(f"Use /video {prompt} to generate a similar video!", show_alert=True)
            
        elif data == "video_help":
            help_text = (
                "<b>🎬 Video Generation Help</b>\n\n"
                "<b>Commands:</b>\n"
                "• <code>/video &lt;prompt&gt;</code> - Generate a video\n"
                "• <code>/token</code> - Check your balance\n\n"
                "<b>Cost:</b> 10 tokens per video\n\n"
                "<b>Tips:</b>\n"
                "• Use descriptive prompts\n"
                "• Include lighting and mood\n"
                "• Specify camera angles\n"
                "• Keep prompts under 500 characters\n\n"
                "<b>Examples:</b>\n"
                "• <i>A serene lake at sunset with mountains</i>\n"
                "• <i>Futuristic city with flying cars at night</i>"
            )
            await callback_query.message.edit_text(
                help_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
                ]),
                parse_mode=ParseMode.HTML
            )
            
        elif data == "back_to_menu":
            # Show main menu
            await show_main_video_menu(callback_query)
            
        else:
            await callback_query.answer("Unknown action", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error handling callback: {e}")
        await callback_query.answer("An error occurred. Please try again.", show_alert=True)



async def show_token_balance(callback_query: CallbackQuery):
    """Show enhanced token balance information."""
    try:
        user_id = callback_query.from_user.id
        tokens = await get_user_tokens(user_id)
        
        # Calculate what user can afford - simplified for Premium only
        premium_videos = tokens // QUALITY_DESCRIPTIONS[VideoQuality.PREMIUM]["cost"]
        
        balance_text = (
            f"<b>💎 Token Balance</b>\n\n"
            f"<b>Current Balance:</b> <code>{tokens} tokens</code>\n\n"
            f"<b>📊 What you can generate:</b>\n"
            f"• <b>Premium Quality Videos:</b> {premium_videos} videos\n\n"
            f"<i>💡 Each video costs 10 tokens and includes premium features!</i>"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Buy More Tokens", callback_data="show_plans")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
        ])
        
        await callback_query.message.edit_text(balance_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    
    except Exception as e:
        logger.error(f"Error showing token balance: {e}")
        await callback_query.answer("Error loading token balance.", show_alert=True)

async def show_enhanced_plans(callback_query: CallbackQuery):
    """Show enhanced token purchase plans."""
    try:
        plans_text = (
            "<b>🛒 Premium Token Plans</b>\n\n"
            
            "<b>🎬 Why Choose Our Video Generation?</b>\n"
            "✅ <b>Cutting-edge AI</b> (Google Veo 3.0)\n"
            "✅ <b>Premium Quality</b> (10 tokens per video)\n"
            "✅ <b>Fast Generation</b> (1-3 minutes)\n"
            "✅ <b>Custom Aspect Ratios</b> (9:16, 16:9, 1:1, 21:9)\n"
            "✅ <b>AI Prompt Enhancement</b> (Included)\n"
            "✅ <b>Priority Queue</b> (Fast processing)\n\n"
            
            "<b>💰 Available Plans:</b>\n\n"
        )
        
        for plan in PLANS:
            popular_tag = " 🔥 POPULAR" if plan.get("popular", False) else ""
            value_per_token = plan["price"] / plan["tokens"]
            videos_possible = plan["tokens"] // 10  # 10 tokens per video
            
            plans_text += (
                f"<b>{plan['label']}{popular_tag}</b>\n"
                f"<code>Rs {plan['price']} → {plan['tokens']} tokens → {videos_possible} videos</code>\n"
                f"<i>Value: Rs {value_per_token:.2f} per token</i>\n\n"
            )
        
        plans_text += (
            "<b>🎯 Token Usage:</b>\n"
            f"• Premium Quality: {QUALITY_DESCRIPTIONS[VideoQuality.PREMIUM]['cost']} tokens per video\n\n"
            
            "<b>Ready to buy?</b> Contact admin for instant activation!"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💸 Contact Admin for Payment", url="https://t.me/techycsr")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
        ])
        
        await callback_query.message.edit_text(plans_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    
    except Exception as e:
        logger.error(f"Error showing enhanced plans: {e}")
        await callback_query.answer("Error loading plans.", show_alert=True)





async def show_main_video_menu(callback_query: CallbackQuery):
    """Show the main video generation menu - simplified."""
    try:
        user_id = callback_query.from_user.id
        tokens = await get_user_tokens(user_id)
        
        menu_text = (
            "<b>🎬 AI Video Generation Studio</b>\n\n"
            f"<b>💎 Your Balance:</b> <code>{tokens} tokens</code>\n\n"
            
            "<b>🚀 Features:</b>\n"
            "• Premium quality videos (10 tokens each)\n"
            "• AI prompt enhancement\n"
            "• Real-time progress tracking\n"
            "• Multiple aspect ratios\n\n"
            
            "<b>💡 How to create:</b>\n"
            "<code>/video your creative prompt here</code>\n\n"
            
            "<b>✨ Example prompts:</b>\n"
            "• <i>A serene lake at sunset with mountains</i>\n"
            "• <i>Futuristic city with flying cars at night</i>\n"
            "• <i>Close-up of a blooming flower in slow motion</i>\n"
            "• <i>Astronaut walking on Mars surface</i>"
        )
        
        keyboard = VideoGenerationUI.create_user_dashboard_keyboard(user_id, show_new_video=False)
        
        try:
            await callback_query.message.edit_text(menu_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        except Exception as e:
            if "MESSAGE_NOT_MODIFIED" in str(e):
                # Message content is the same, just answer the callback
                pass
            else:
                raise e
        
    except Exception as e:
        logger.error(f"Error showing main video menu: {e}")
        await callback_query.answer("Error loading menu.", show_alert=True)

# Admin commands (enhanced)
async def addt_command_handler(client, message: Message):
    """Enhanced add tokens command with logging."""
    try:
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
    
    except Exception as e:
        logger.error(f"Error in addt command: {e}")
        await message.reply_text(f"❌ Command error: {str(e)}")

async def removet_command_handler(client, message: Message):
    """Enhanced remove tokens command."""
    try:
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
    
    except Exception as e:
        logger.error(f"Error in removet command: {e}")
        await message.reply_text(f"❌ Command error: {str(e)}")

async def token_command_handler(client, message: Message):
    """Enhanced token balance command."""
    try:
        user_id = message.from_user.id
        tokens = await get_user_tokens(user_id)
        
        keyboard = VideoGenerationUI.create_user_dashboard_keyboard(user_id)
        
        balance_text = (
            f"<b>💎 Your Token Dashboard</b>\n\n"
            f"<b>Current Balance:</b> <code>{tokens} tokens</code>\n\n"
            f"<b>🎬 What you can create:</b>\n"
            f"• Premium Quality Videos: {tokens // 10} videos\n\n"
            f"<i>Choose your next action below:</i>"
        )
        
        await message.reply_text(balance_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    
    except Exception as e:
        logger.error(f"Error in token command: {e}")
        await message.reply_text(f"❌ Command error: {str(e)}")

async def vtoken_command_handler(client, message: Message):
    """Enhanced view user tokens command for admins."""
    try:
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
    
    except Exception as e:
        logger.error(f"Error in vtoken command: {e}")
        await message.reply_text(f"❌ Command error: {str(e)}") 