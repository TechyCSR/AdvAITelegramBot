#!/usr/bin/env python3
"""
Mention Fix Test Script
This script verifies that user mentions are properly preserved in translations
"""

import os
import sys
import asyncio

# Add parent directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)

# Import the translation functions
from modules.lang import async_translate_to_lang, format_with_mention
from modules.lang_resources.translation_cache import preload_all_caches

# Test templates with mentions
TEST_TEMPLATES = [
    "**Welcome {mention}!** 👋 How can I help you today?",
    "Hello {mention}, I've processed your request.",
    "Settings for user {mention}",
    "{mention} has requested an image generation",
    "Thank you {mention} for using our bot!",
]

# Test mentions
TEST_MENTIONS = [
    "@TestUser",
    "John Doe",
    "سعيد محمد",  # Arabic name
    "राम शर्मा",  # Hindi name
    "李明",  # Chinese name
]

# Languages to test
TEST_LANGUAGES = ['en', 'hi', 'zh', 'ar', 'fr', 'ru']

async def test_standard_translation():
    """Test how standard translation handles mentions"""
    print("\n=== Testing Standard Translation with Mentions ===")
    
    for lang in TEST_LANGUAGES:
        print(f"\nTesting language: {lang}")
        
        for template in TEST_TEMPLATES:
            for mention in TEST_MENTIONS[:2]:  # Use just a couple of mentions for brevity
                # Format the template with the mention
                text = template.replace("{mention}", mention)
                
                # Translate normally
                translated = await async_translate_to_lang(text, lang=lang)
                
                # Check if mention is preserved
                mention_preserved = mention in translated
                if not mention_preserved:
                    print(f"❌ FAILED: '{text}' => '{translated}'")
                else:
                    print(f"✓ PASSED: '{text}' => '{translated}'")

async def test_enhanced_mention_handling():
    """Test the enhanced mention handling function"""
    print("\n=== Testing Enhanced Mention Handling ===")
    
    for lang in TEST_LANGUAGES:
        print(f"\nTesting language: {lang}")
        
        for template in TEST_TEMPLATES:
            for mention in TEST_MENTIONS:
                # Format the template with the mention using the enhanced function
                translated = await format_with_mention(template, mention, lang=lang)
                
                # Check if mention is preserved
                mention_preserved = mention in translated
                if not mention_preserved:
                    print(f"❌ FAILED: '{template}' with '{mention}' => '{translated}'")
                else:
                    print(f"✓ PASSED: '{template}' with '{mention}' => '{translated}'")

async def main():
    """Run all tests"""
    # Preload caches
    print("Preloading translation caches...")
    preload_all_caches()
    
    # Run tests
    await test_standard_translation()
    await test_enhanced_mention_handling()
    
    print("\nMention handling tests completed!")

if __name__ == "__main__":
    asyncio.run(main()) 