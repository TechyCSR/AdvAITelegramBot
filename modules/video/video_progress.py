import asyncio
import random
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, MessageNotModified

class ProgressAnimator:
    """Modern progress animation system with multiple styles."""
    
    # Different progress bar styles
    MODERN_BARS = {
        "blocks": ["█", "▓", "▒", "░"],
        "dots": ["●", "◐", "◑", "◒", "◓", "○"],
        "arrows": ["▶", "▷", "▻", "▸", "▹", "▫"],
        "waves": ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"],
        "circles": ["◯", "◔", "◑", "◕", "●"],
        "squares": ["▰", "▱"]
    }
    
    # Advanced stage definitions with emojis and descriptions
    GENERATION_STAGES = [
        {
            "name": "Initializing",
            "emoji": "🚀",
            "description": "Preparing your creative vision",
            "start": 0, "end": 8,
            "tips": ["AI is understanding your prompt", "Setting up generation parameters"]
        },
        {
            "name": "AI Processing", 
            "emoji": "🧠",
            "description": "AI analyzing and enhancing prompt",
            "start": 8, "end": 20,
            "tips": ["Neural networks are working", "Prompt optimization in progress"]
        },
        {
            "name": "Scene Planning",
            "emoji": "🎯", 
            "description": "Planning visual composition",
            "start": 20, "end": 35,
            "tips": ["Designing camera angles", "Planning visual elements"]
        },
        {
            "name": "Visual Creation",
            "emoji": "🎨",
            "description": "Generating visual frames", 
            "start": 35, "end": 60,
            "tips": ["Creating stunning visuals", "Applying artistic styles"]
        },
        {
            "name": "Motion Synthesis",
            "emoji": "🎬",
            "description": "Adding movement and dynamics",
            "start": 60, "end": 80,
            "tips": ["Animating scenes", "Creating smooth transitions"]
        },
        {
            "name": "Audio Generation",
            "emoji": "🔊",
            "description": "Creating immersive audio",
            "start": 80, "end": 92,
            "tips": ["Generating ambient sounds", "Syncing audio with visuals"]
        },
        {
            "name": "Final Rendering",
            "emoji": "✨",
            "description": "Polishing and finalizing",
            "start": 92, "end": 100,
            "tips": ["Applying final touches", "Preparing your masterpiece"]
        }
    ]
    
    def __init__(self, style: str = "modern"):
        self.style = style
        self.animation_frame = 0
        self.last_tip_index = 0
    
    def get_progress_bar(self, progress: int, length: int = 20) -> str:
        """Generate modern progress bar with animations."""
        if self.style == "modern":
            filled = int(length * progress / 100)
            bar_chars = self.MODERN_BARS["blocks"]
            
            # Create animated progress bar
            bar = ""
            for i in range(length):
                if i < filled - 1:
                    bar += bar_chars[0]  # Filled
                elif i == filled - 1 and progress < 100:
                    # Animated current position
                    anim_chars = ["▓", "▒", "░"]
                    bar += anim_chars[self.animation_frame % len(anim_chars)]
                else:
                    bar += bar_chars[-1]  # Empty
            
            return bar
        
        elif self.style == "waves":
            chars = self.MODERN_BARS["waves"]
            bar = ""
            for i in range(length):
                wave_pos = (i + self.animation_frame) % len(chars)
                if i <= int(length * progress / 100):
                    bar += chars[min(wave_pos, len(chars) - 1)]
                else:
                    bar += chars[0]
            return bar
        
        else:  # Default blocks
            filled = int(length * progress / 100)
            return "█" * filled + "░" * (length - filled)
    
    def get_current_stage(self, progress: int) -> Dict[str, Any]:
        """Get current generation stage info."""
        for stage in self.GENERATION_STAGES:
            if stage["start"] <= progress <= stage["end"]:
                return stage
        return self.GENERATION_STAGES[-1]  # Fallback to last stage
    
    def get_animated_emoji(self, base_emoji: str) -> str:
        """Add animation to emojis."""
        animations = {
            "🧠": ["🧠", "🤔", "💭", "🧠"],
            "🎨": ["🎨", "🖌️", "🖍️", "🎨"],
            "🎬": ["🎬", "🎥", "📹", "🎬"],
            "🔊": ["🔊", "🔉", "🔈", "🔊"],
            "✨": ["✨", "⭐", "🌟", "✨"],
            "🚀": ["🚀", "🌠", "⭐", "🚀"]
        }
        
        if base_emoji in animations:
            return animations[base_emoji][self.animation_frame % len(animations[base_emoji])]
        return base_emoji
    
    def update_animation(self):
        """Update animation frame."""
        self.animation_frame += 1

class InteractiveVideoProgress:
    """Enhanced interactive video progress tracker."""
    
    def __init__(self, client: Client, message: Message, prompt: str, request_id: str):
        self.client = client
        self.message = message
        self.prompt = prompt
        self.request_id = request_id
        self.animator = ProgressAnimator("modern")
        self.start_time = time.time()
        self.last_update = 0
        self.update_count = 0
        self.is_cancelled = False
        
    async def show_queue_status(self, position: int, estimated_time: int):
        """Show queue position and estimated wait time."""
        wait_emoji = ["⏳", "⌛", "⏰", "🕐"][self.animator.animation_frame % 4]
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_video_{self.request_id}"),
                InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_status_{self.request_id}")
            ]
        ])
        
        text = (
            f"<b>{wait_emoji} Video Request Queued</b>\n\n"
            f"<code>{self.prompt[:60]}{'...' if len(self.prompt) > 60 else ''}</code>\n\n"
            f"<b>📍 Queue Position:</b> <code>#{position}</code>\n"
            f"<b>⏱️ Estimated Wait:</b> <code>{estimated_time // 60}m {estimated_time % 60}s</code>\n\n"
            f"<i>💡 Your video will start processing soon!</i>"
        )
        
        try:
            await self.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        except (FloodWait, MessageNotModified):
            pass
        
        self.animator.update_animation()
    
    async def show_progress(self, progress: int, stage_info: Dict[str, Any]):
        """Show enhanced progress with animations and tips."""
        try:
            self.animator.update_animation()
            current_stage = self.animator.get_current_stage(progress)
            animated_emoji = self.animator.get_animated_emoji(current_stage["emoji"])
            progress_bar = self.animator.get_progress_bar(progress)
            
            # Calculate elapsed and estimated time
            elapsed = int(time.time() - self.start_time)
            if progress > 5:  # Avoid division by very small numbers
                estimated_total = int(elapsed * 100 / progress)
                remaining = max(0, estimated_total - elapsed)
            else:
                remaining = 120  # Default estimate
            
            # Get random tip from current stage
            tips = current_stage.get("tips", ["Processing..."])
            if self.update_count % 3 == 0:  # Change tip every 3 updates
                self.last_tip_index = (self.last_tip_index + 1) % len(tips)
            current_tip = tips[self.last_tip_index]
            
            # Enhanced progress message
            text = (
                f"<b>{animated_emoji} {current_stage['name']}</b>\n"
                f"<i>{current_stage['description']}</i>\n\n"
                f"<code>{self.prompt[:50]}{'...' if len(self.prompt) > 50 else ''}</code>\n\n"
                f"<code>[{progress_bar}]</code> <b>{progress}%</b>\n\n"
                f"<b>⏱️ Time:</b> <code>{elapsed}s elapsed, ~{remaining}s remaining</code>\n"
                f"<b>💡 Tip:</b> <i>{current_tip}</i>\n\n"
                f"<b>🎯 Status:</b> <code>{stage_info.get('status', 'Processing')}</code>"
            )
            
            # Add interactive buttons
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_video_{self.request_id}"),
                    InlineKeyboardButton("📊 Stats", callback_data=f"video_stats_{self.request_id}")
                ]
            ])
            
            await self.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            self.update_count += 1
            
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except MessageNotModified:
            pass
        except Exception as e:
            print(f"Progress update error: {e}")
    
    async def show_completion(self, local_path: str, generation_time: float, enhanced_prompt: Optional[str] = None):
        """Show completion message with download options."""
        completion_emojis = ["🎉", "✅", "🏆", "🌟"]
        emoji = completion_emojis[self.animator.animation_frame % len(completion_emojis)]
        
        text = (
            f"<b>{emoji} Video Generation Complete!</b>\n\n"
            f"<code>{self.prompt[:60]}{'...' if len(self.prompt) > 60 else ''}</code>\n\n"
            f"<b>⏱️ Generation Time:</b> <code>{generation_time:.1f}s</code>\n"
            f"<b>📁 File:</b> <code>Ready for download</code>\n"
        )
        
        if enhanced_prompt:
            text += f"<b>✨ Enhanced Prompt:</b>\n<i>{enhanced_prompt[:100]}{'...' if len(enhanced_prompt) > 100 else ''}</i>\n"
        
        text += "\n<i>🎬 Your masterpiece is ready!</i>"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Generate Another", callback_data="new_video_generation"),
                InlineKeyboardButton("📊 Analytics", callback_data=f"video_analytics_{self.request_id}")
            ],
            [
                InlineKeyboardButton("💳 Buy More Tokens", callback_data="show_plans")
            ]
        ])
        
        try:
            await self.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        except Exception as e:
            print(f"Completion update error: {e}")
    
    async def show_error(self, error_message: str):
        """Show error message with retry options."""
        error_emojis = ["❌", "😞", "💔", "😔"]
        emoji = error_emojis[self.animator.animation_frame % len(error_emojis)]
        
        text = (
            f"<b>{emoji} Generation Failed</b>\n\n"
            f"<code>{self.prompt[:60]}{'...' if len(self.prompt) > 60 else ''}</code>\n\n"
            f"<b>❗ Error:</b> <code>{error_message}</code>\n\n"
            f"<i>💡 Don't worry! Your tokens have been refunded.</i>"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Try Again", callback_data=f"retry_video_{self.prompt}"),
                InlineKeyboardButton("✏️ Edit Prompt", callback_data="new_video_generation")
            ],
            [
                InlineKeyboardButton("🆘 Get Help", callback_data="video_help")
            ]
        ])
        
        try:
            await self.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        except Exception as e:
            print(f"Error update error: {e}")

async def create_interactive_progress(client: Client, message: Message, prompt: str, request_id: str) -> InteractiveVideoProgress:
    """Create and return an interactive progress tracker."""
    return InteractiveVideoProgress(client, message, prompt, request_id)

async def update_video_progress_enhanced(client: Client, message: Message, prompt: str, request_id: str, status_callback=None):
    """
    Enhanced video progress tracking with real-time updates and interactivity.
    """
    progress_tracker = await create_interactive_progress(client, message, prompt, request_id)
    
    try:
        # Import here to avoid circular imports
        from modules.video.video_generation import get_request_status
        
        last_progress = 0
        consecutive_same_progress = 0
        max_updates = 100  # Prevent infinite loops
        update_interval = 2.0  # Base update interval
        
        for update_count in range(max_updates):
            # Get current status
            status = await get_request_status(request_id)
            if not status:
                await progress_tracker.show_error("Request not found")
                break
            
            current_status = status["status"]
            progress = status.get("progress", 0)
            
            # Handle different states
            if current_status == "queued":
                queue_pos = status.get("queue_position", 1)
                estimated_time = status.get("estimated_time", 120)
                await progress_tracker.show_queue_status(queue_pos, estimated_time)
                update_interval = 5.0  # Slower updates for queue
                
            elif current_status == "processing":
                await progress_tracker.show_progress(progress, status)
                update_interval = 2.0 if progress < 50 else 3.0  # Adaptive interval
                
            elif current_status == "completed":
                # Get additional completion info if available
                enhanced_prompt = status.get("enhanced_prompt")
                generation_time = status.get("generation_time", 0)
                await progress_tracker.show_completion("completed", generation_time, enhanced_prompt)
                break
                
            elif current_status == "failed":
                error_msg = status.get("error_message", "Unknown error occurred")
                await progress_tracker.show_error(error_msg)
                break
                
            elif current_status == "cancelled":
                await progress_tracker.show_error("Request was cancelled")
                break
            
            # Detect stuck progress
            if progress == last_progress:
                consecutive_same_progress += 1
                if consecutive_same_progress > 10:  # If stuck for too long
                    update_interval = min(update_interval * 1.2, 10.0)  # Slow down updates
            else:
                consecutive_same_progress = 0
                update_interval = 2.0  # Reset to normal speed
            
            last_progress = progress
            
            # Call status callback if provided
            if status_callback:
                await status_callback(status)
            
            # Wait before next update
            await asyncio.sleep(update_interval)
            
    except asyncio.CancelledError:
        # Progress tracking was cancelled
        await progress_tracker.show_error("Progress tracking cancelled")
    except Exception as e:
        print(f"Enhanced progress error: {e}")
        await progress_tracker.show_error(f"Progress tracking error: {str(e)}")

# Legacy function for backwards compatibility
async def update_video_progress(client: Client, message: Message, prompt: str):
    """Legacy progress function - maintained for backwards compatibility."""
    # Generate a dummy request ID for legacy calls
    import uuid
    request_id = str(uuid.uuid4())
    await update_video_progress_enhanced(client, message, prompt, request_id) 