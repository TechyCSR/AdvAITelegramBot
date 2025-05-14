#!/usr/bin/env python3
"""
Translation cache test script
This script demonstrates how the translation cache system works
and can be used to test its functionality.
"""

import os
import sys
import time
import random

# Add parent directories to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
modules_dir = os.path.dirname(script_dir)
root_dir = os.path.dirname(modules_dir)
sys.path.extend([root_dir, modules_dir, script_dir])

# Import the translation functions
from modules.lang import translate_to_lang, async_translate_to_lang
from modules.lang_resources.translation_cache import (
    get_cached_translation, 
    add_to_translation_cache,
    get_translation_stats,
    preload_all_caches
)

# Test strings in English
TEST_STRINGS = [
    "Hello! How are you today?",
    "Welcome to our advanced AI bot!",
    "Please select an option from the menu below.",
    "Your message has been sent successfully.",
    "Would you like to continue with this operation?",
    "Thank you for your feedback!",
    "Processing your request, please wait...",
    "Image generation completed successfully.",
    "Voice message received and processed.",
    "Your settings have been updated."
]

# Target languages to test
TEST_LANGUAGES = ['hi', 'zh', 'ar', 'fr', 'ru']

def run_translation_test():
    """Run a test of the translation cache system"""
    print("Starting translation cache test...")
    
    # Preload the caches
    preload_all_caches()
    
    # Print initial stats
    print("\nInitial cache statistics:")
    stats = get_translation_stats()
    for lang, count in stats.items():
        print(f"  {lang}: {count} cached translations")
    
    # Test each language
    for lang in TEST_LANGUAGES:
        print(f"\nTesting translations for language: {lang}")
        
        # First pass - should use online translation and add to cache
        print(f"First pass (online translation):")
        start_time = time.time()
        for i, text in enumerate(TEST_STRINGS):
            translated = translate_to_lang(text, lang=lang)
            print(f"  [{i+1}] Original: '{text}'")
            print(f"      Translated: '{translated}'")
        first_pass_time = time.time() - start_time
        print(f"First pass completed in {first_pass_time:.2f} seconds")
        
        # Second pass - should use cache
        print(f"\nSecond pass (should use cache):")
        start_time = time.time()
        for i, text in enumerate(TEST_STRINGS):
            translated = translate_to_lang(text, lang=lang)
            cached = get_cached_translation(text, lang)
            print(f"  [{i+1}] Cached: {'Yes' if cached else 'No'} - '{translated}'")
        second_pass_time = time.time() - start_time
        print(f"Second pass completed in {second_pass_time:.2f} seconds")
        
        # Calculate speedup
        if first_pass_time > 0:
            speedup = first_pass_time / second_pass_time if second_pass_time > 0 else float('inf')
            print(f"Cache speedup: {speedup:.1f}x faster")
    
    # Final stats
    print("\nFinal cache statistics:")
    stats = get_translation_stats()
    for lang, count in stats.items():
        print(f"  {lang}: {count} cached translations")
    
    print("\nTranslation cache test completed successfully!")

if __name__ == "__main__":
    run_translation_test() 