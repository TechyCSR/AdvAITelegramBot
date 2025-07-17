import asyncio
import random
from pyrogram import Client
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, MessageNotModified

async def update_video_progress(client: Client, message, prompt: str):
    """
    Shows a dynamic, modern progress bar for video generation with optimized updates.
    """
    progress_bar_chars = ["▰", "▱"]  # More modern looking bar characters
    stages = [
        ("🎯 Understanding your vision", 0, 15),
        ("🧠 Processing with AI", 15, 35),
        ("🎨 Creating visual elements", 35, 55),
        ("🎬 Rendering frames", 55, 75),
        ("🔊 Adding audio effects", 75, 90),
        ("✨ Final touches", 90, 100)
    ]
    
    try:
        current_stage = 0
        last_text = ""
        last_update_time = 0
        
        for i in range(101):
            # Only update every 3% progress or when stage changes
            if i % 3 != 0 and i not in [stage[1] for stage in stages]:
                await asyncio.sleep(0.5)
                continue
                
            # Minimum time between updates to prevent flood
            current_time = asyncio.get_event_loop().time()
            if current_time - last_update_time < 2:  # Minimum 2 seconds between updates
                await asyncio.sleep(0.5)
                continue
                
            # Update stage based on progress
            while current_stage < len(stages) - 1 and i >= stages[current_stage + 1][1]:
                current_stage += 1
            
            stage_text, start_percent, end_percent = stages[current_stage]
            
            filled_len = int(20 * i // 100)
            bar = progress_bar_chars[0] * filled_len + progress_bar_chars[1] * (20 - filled_len)
            
            new_text = (
                f"<b>🎥 Creating Your Video</b>\n\n"
                f"<code>{prompt[:50]}{'...' if len(prompt) > 50 else ''}</code>\n\n"
                f"<code>[{bar}]</code> <b>{i}%</b>\n"
                f"<i>{stage_text}</i>"
            )

            # Only update if text has changed
            if new_text != last_text:
                try:
                    await message.edit_text(new_text, parse_mode=ParseMode.HTML)
                    last_text = new_text
                    last_update_time = current_time
                except FloodWait as e:
                    await asyncio.sleep(e.value)  # Wait as requested by Telegram
                except MessageNotModified:
                    pass  # Ignore if message content is the same
                except Exception as e:
                    print(f"Progress update error: {str(e)}")
                    pass  # Continue on other errors
                
            await asyncio.sleep(random.uniform(1.5, 2.0))  # Longer sleep between updates
            
    except Exception as e:
        print(f"Progress bar error: {str(e)}")
        # Stop if message is deleted or inaccessible
        pass 