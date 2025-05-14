"""
Language resources module for the Advanced AI Telegram Bot.
Contains translation cache and other language-related resources.
"""

from modules.lang_resources.translation_cache import (
    get_cached_translation,
    add_to_translation_cache,
    preload_all_caches
)

__all__ = [
    'get_cached_translation',
    'add_to_translation_cache',
    'preload_all_caches'
] 