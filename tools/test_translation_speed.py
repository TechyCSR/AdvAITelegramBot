#!/usr/bin/env python3
"""
Translation Speed Test Script
This script benchmarks the performance of the translation system.
"""

import os
import sys
import time
import asyncio
import random
from typing import List, Dict

# Add parent directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)

# Import the translation functions
from modules.lang import async_translate_to_lang, batch_translate
from modules.lang_resources.translation_cache import (
    get_cached_translation, 
    add_to_translation_cache,
    get_translation_stats,
    preload_all_caches
)

# Common UI text elements that are frequently translated
UI_ELEMENTS = [
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

# Sample sentences for testing
SAMPLE_SENTENCES = [
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

# User mention examples
USER_MENTIONS = [
    "Setting Menu for User {mention}",
    "Welcome {mention}!",
    "Hello {mention}, how can I help you?",
    "Thank you {mention} for your message",
    "{mention} has requested an image generation"
]

# Target languages to test
TEST_LANGUAGES = ['hi', 'zh', 'ar', 'fr', 'ru']

async def measure_single_translation_speed():
    """Measure speed of translating individual strings"""
    print("\n=== Testing Single Translation Speed ===")
    
    results = {}
    for lang in TEST_LANGUAGES:
        print(f"\nTesting language: {lang}")
        
        # First pass (should use online translation if not cached)
        total_time = 0
        for text in SAMPLE_SENTENCES:
            start_time = time.time()
            translated = await async_translate_to_lang(text, lang=lang)
            elapsed = time.time() - start_time
            total_time += elapsed
            print(f"  '{text[:20]}...' => '{translated[:20]}...' ({elapsed:.3f}s)")
        
        print(f"First pass average: {total_time/len(SAMPLE_SENTENCES):.3f}s per string")
        
        # Second pass (should use cache)
        start_time = time.time()
        for text in SAMPLE_SENTENCES:
            await async_translate_to_lang(text, lang=lang)
        elapsed = time.time() - start_time
        
        print(f"Second pass total: {elapsed:.3f}s for {len(SAMPLE_SENTENCES)} strings")
        print(f"Second pass average: {elapsed/len(SAMPLE_SENTENCES):.3f}s per string")
        
        # Calculate speedup
        speedup = (total_time / elapsed) if elapsed > 0 else float('inf')
        print(f"Cache speedup: {speedup:.1f}x faster")
        
        results[lang] = {
            "first_pass_avg": total_time/len(SAMPLE_SENTENCES),
            "second_pass_avg": elapsed/len(SAMPLE_SENTENCES),
            "speedup": speedup
        }
        
    return results

async def measure_batch_translation_speed():
    """Measure speed of batch translation"""
    print("\n=== Testing Batch Translation Speed ===")
    
    results = {}
    for lang in TEST_LANGUAGES:
        print(f"\nTesting language: {lang}")
        
        # First, clear caches to ensure we're measuring true performance
        # (Don't do this in production, just for benchmarking)
        for text in SAMPLE_SENTENCES:
            # Force translation to happen again
            pass
        
        # Individually translated
        start_time = time.time()
        for text in SAMPLE_SENTENCES:
            await async_translate_to_lang(text, lang=lang)
        individual_time = time.time() - start_time
        
        print(f"Individual translation total: {individual_time:.3f}s")
        
        # Batch translated
        start_time = time.time()
        await batch_translate(SAMPLE_SENTENCES, lang=lang)
        batch_time = time.time() - start_time
        
        print(f"Batch translation total: {batch_time:.3f}s")
        
        # Calculate speedup
        speedup = (individual_time / batch_time) if batch_time > 0 else float('inf')
        print(f"Batch speedup: {speedup:.1f}x faster")
        
        results[lang] = {
            "individual_time": individual_time,
            "batch_time": batch_time,
            "speedup": speedup
        }
        
    return results

async def test_mention_translation():
    """Test how well mention placeholders are preserved"""
    print("\n=== Testing Mention Placeholder Preservation ===")
    
    mention = "@TestUser"
    
    for lang in TEST_LANGUAGES:
        print(f"\nTesting language: {lang}")
        
        for text in USER_MENTIONS:
            # Format with mention
            original = text.format(mention=mention)
            
            # Translate
            translated = await async_translate_to_lang(original, lang=lang)
            
            # Check if mention is preserved
            mention_preserved = mention in translated
            print(f"  '{original}' => '{translated}' (Mention preserved: {mention_preserved})")

async def main():
    """Run all tests"""
    # Preload caches
    print("Preloading translation caches...")
    preload_all_caches()
    
    # Print initial cache stats
    stats = get_translation_stats()
    print("\nInitial cache statistics:")
    print(f"  Cache entries: {stats['cache_entries']}")
    print(f"  Hit rate: {stats.get('hit_rate', 0)}%")
    print(f"  Memory usage: {stats.get('memory_usage', 0)} MB")
    
    # Run tests
    await measure_single_translation_speed()
    await measure_batch_translation_speed()
    await test_mention_translation()
    
    # Print final cache stats
    stats = get_translation_stats()
    print("\nFinal cache statistics:")
    print(f"  Cache entries: {stats['cache_entries']}")
    print(f"  Hit rate: {stats.get('hit_rate', 0)}%")
    print(f"  Memory usage: {stats.get('memory_usage', 0)} MB")
    
    print("\nTranslation performance tests completed!")

if __name__ == "__main__":
    asyncio.run(main()) 