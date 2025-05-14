"""
Main modules package for the Advanced AI Telegram Bot.
Contains various functionality modules like AI response, image processing, voice handling, etc.
"""

import os
import sys
import asyncio

# Add parent directory to python path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import important modules for initialization
try:
    # Import and initialize translation cache first
    from modules.lang_resources.translation_cache import preload_all_caches
    print("✓ Translation cache module initialized")
    
    # Preload translation caches
    preload_all_caches()
    print("✓ Translation caches preloaded")
except Exception as e:
    print(f"⚠ Warning: Failed to initialize translation cache: {e}")

# Common UI strings to preload translations for all languages
COMMON_UI_STRINGS = [
    "🔙 Back",
    "🌐 Language",
    "🎙️ Voice",
    "🤖 Assistant",
    "🔧 Others",
    "Settings",
    "Help",
    "Commands",
    "Support",
    "Add to Group"
]

# Supported languages
LANGUAGES = ['hi', 'zh', 'ar', 'fr', 'ru']

# Prefetch translations for common UI elements asynchronously
async def prefetch_ui_translations():
    try:
        from modules.lang import batch_translate
        
        # Create a batch translation task for each language
        tasks = []
        for lang in LANGUAGES:
            task = asyncio.create_task(batch_translate(COMMON_UI_STRINGS, lang=lang))
            tasks.append(task)
            
        # Wait for all translations to complete
        results = await asyncio.gather(*tasks)
        print(f"✓ Prefetched translations for {len(COMMON_UI_STRINGS)} UI strings in {len(LANGUAGES)} languages")
    except Exception as e:
        print(f"⚠ Warning: Failed to prefetch UI translations: {e}")

# Run the prefetch in the background if running in async context
def run_prefetch():
    try:
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        # Run the prefetch
        if loop.is_running():
            # Schedule as task if loop is already running
            asyncio.create_task(prefetch_ui_translations())
        else:
            # Run until complete if loop is not running
            loop.run_until_complete(prefetch_ui_translations())
    except Exception as e:
        print(f"⚠ Warning: Error in translation prefetch: {e}")

# Initialize other modules as needed
__all__ = [
    'user',
    'group',
    'image',
    'speech',
    'modles',
    'lang',
    'chatlogs',
    'feedback_nd_rating',
    'maintenance',
    'lang_resources'
]

# Schedule the prefetch to run
try:
    import threading
    prefetch_thread = threading.Thread(target=run_prefetch, daemon=True)
    prefetch_thread.start()
except Exception as e:
    print(f"⚠ Warning: Failed to start translation prefetch thread: {e}")

if __name__ == "__main__":
    pass