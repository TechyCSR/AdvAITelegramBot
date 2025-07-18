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
        

    
    async def show_progress(self, progress: int, stage_info: Dict[str, Any]):
        """Show enhanced progress with animations and tips - with better error handling."""
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
            
            # Enhanced progress message with percentage focus
            text = (
                f"<b>{animated_emoji} {current_stage['name']}</b>\n"
                f"<i>{current_stage['description']}</i>\n\n"
                f"<b>📝 Prompt:</b> <code>{self.prompt[:80]}{'...' if len(self.prompt) > 80 else ''}</code>\n\n"
                f"<code>[{progress_bar}]</code> <b>{progress}%</b>\n\n"
                f"<b>⏱️ Time:</b> <code>{elapsed}s elapsed, ~{remaining}s remaining</code>\n"
                f"<b>💡 Tip:</b> <i>{current_tip}</i>\n\n"
                f"<b>🎯 Status:</b> <code>Generating your amazing video...</code>"
            )
            
            # Add progress button that shows completion percentage
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"📊 {progress}% Completed", callback_data=f"progress_check_{self.request_id}")],
                [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_video_{self.request_id}")]
            ])
            
            # Try to edit the message with better error handling
            try:
                await self.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
                self.update_count += 1
            except MessageNotModified:
                # Content is the same, just update the button percentage
                try:
                    new_keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton(f"📊 {progress}% Completed", callback_data=f"progress_check_{self.request_id}")],
                        [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_video_{self.request_id}")]
                    ])
                    await self.message.edit_reply_markup(reply_markup=new_keyboard)
                    self.update_count += 1
                except Exception as e:
                    # If we can't update anything, just continue
                    print(f"Progress keyboard update error: {e}")
            except Exception as e:
                print(f"Progress message update error: {e}")
            
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"Progress update error: {e}")

    async def show_completion(self, local_path: str, generation_time: float, enhanced_prompt: Optional[str] = None):
        """Show completion message with download options."""
        completion_emojis = ["🎉", "✅", "🏆", "🌟"]
        emoji = completion_emojis[self.animator.animation_frame % len(completion_emojis)]
        
        text = (
            f"<b>{emoji} Video Generation Complete!</b>\n\n"
            f"<b>📝 Prompt:</b> <code>{self.prompt[:80]}{'...' if len(self.prompt) > 80 else ''}</code>\n\n"
            f"<b>📊 Progress:</b> <code>100%</code> ✅\n"
            f"<b>⏱️ Generation Time:</b> <code>{generation_time:.1f}s</code>\n"
            f"<b>📁 Status:</b> <code>Ready for delivery</code>\n\n"
            f"<i>🎬 Your masterpiece is ready!</i>"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ 100% Completed", callback_data=f"progress_check_{self.request_id}")]
        ])
        
        try:
            await self.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        except MessageNotModified:
            # Try to update just the keyboard
            try:
                await self.message.edit_reply_markup(reply_markup=keyboard)
            except Exception as e:
                print(f"Completion keyboard update error: {e}")
        except Exception as e:
            print(f"Completion update error: {e}")

    async def show_error(self, error_message: str):
        """Show error message with retry options."""
        error_emojis = ["❌", "😞", "💔", "😔"]
        emoji = error_emojis[self.animator.animation_frame % len(error_emojis)]
        
        text = (
            f"<b>{emoji} Generation Failed</b>\n\n"
            f"<b>📝 Prompt:</b> <code>{self.prompt[:80]}{'...' if len(self.prompt) > 80 else ''}</code>\n\n"
            f"<b>❗ Error:</b> <code>{error_message}</code>\n\n"
            f"<i>💡 Don't worry! Your tokens have been refunded.</i>"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Try Again", callback_data=f"retry_video_{self.prompt}")],
            [InlineKeyboardButton("🆘 Get Help", callback_data="video_help")]
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
    Enhanced video progress tracking with real-time percentage updates and modern UI.
    """
    progress_tracker = await create_interactive_progress(client, message, prompt, request_id)
    
    try:
        # Import here to avoid circular imports
        from modules.video.video_generation import get_request_status
        
        last_progress = 0
        consecutive_same_progress = 0
        max_updates = 100  # Prevent infinite loops
        update_interval = 3.0  # Standard update interval
        
        for update_count in range(max_updates):
            # Get current status
            status = await get_request_status(request_id)
            if not status:
                await progress_tracker.show_error("Request not found")
                break
            
            current_status = status["status"]
            progress = status.get("progress", 0)
            
            # Handle different states - simplified, no queue
            if current_status == "processing":
                await progress_tracker.show_progress(progress, status)
                update_interval = 3.0  # Consistent update interval
                
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
                if consecutive_same_progress > 8:  # If stuck for too long
                    update_interval = min(update_interval * 1.1, 5.0)  # Slightly slow down updates
            else:
                consecutive_same_progress = 0
                update_interval = 3.0  # Reset to normal speed
            
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