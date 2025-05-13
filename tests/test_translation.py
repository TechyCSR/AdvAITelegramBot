import asyncio
from modules.lang import async_translate_to_lang, batch_translate, translate_sync, extract_placeholders
from deep_translator import GoogleTranslator

async def test_translation():
    print("Testing individual translation...")
    
    text1 = "Hello, welcome to our translation test!"
    text2 = "This bot can translate text to multiple languages."
    
    # Test direct module function
    print("\n--- Testing our direct sync function ---")
    direct_hi = translate_sync(text1, "hi")
    print(f"Direct module function Hindi: {direct_hi}")
    
    direct_fr = translate_sync(text2, "fr")
    print(f"Direct module function French: {direct_fr}")
    
    # Test regular deep_translator directly 
    print("\n--- Testing deep_translator directly ---")
    try:
        direct_translator = GoogleTranslator(source='en', target='hi')
        direct_translated = direct_translator.translate(text1)
        print(f"Original: {text1}")
        print(f"Hindi (direct): {direct_translated}")
    except Exception as e:
        print(f"Direct translation error: {e}")
    
    # Test our async implementation
    print("\n--- Testing our async implementation ---")
    translated1 = await async_translate_to_lang(text1, lang="hi")
    print(f"Original: {text1}")
    print(f"Hindi (our implementation): {translated1}")
    
    # Test French translation 
    try:
        direct_translator_fr = GoogleTranslator(source='en', target='fr')
        direct_fr = direct_translator_fr.translate(text2)
        print(f"\nOriginal: {text2}")
        print(f"French (direct): {direct_fr}")
    except Exception as e:
        print(f"Direct French translation error: {e}")
    
    translated2 = await async_translate_to_lang(text2, lang="fr")
    print(f"French (our implementation): {translated2}")
    
    # Test placeholder handling
    print("\n--- Testing placeholder handling ---")
    text_with_placeholder = "Welcome {user_mention}! Your ID is {user_id}."
    placeholders = extract_placeholders(text_with_placeholder)
    print(f"Extracted placeholders: {placeholders}")
    
    translated_with_placeholders = translate_sync(text_with_placeholder, "zh")
    print(f"Original with placeholders: {text_with_placeholder}")
    print(f"Chinese with placeholders preserved: {translated_with_placeholders}")
    
    # Test async placeholder preservation
    async_translated_with_placeholders = await async_translate_to_lang(text_with_placeholder, lang="ar")
    print(f"Arabic with placeholders preserved: {async_translated_with_placeholders}")
    
    # Test with actual formatting
    text_with_format = "Setting Menu for User {mention}\n**User ID**: {user_id}\n**User Language:** {language}"
    
    translated_format_zh = await async_translate_to_lang(text_with_format, lang="zh")
    print(f"\nOriginal format: {text_with_format}")
    print(f"Chinese with formatting preserved: {translated_format_zh}")
    
    # Test formatted with actual values
    formatted_text = text_with_format.format(mention="@user123", user_id="12345", language="English")
    translated_formatted = await async_translate_to_lang(formatted_text, lang="ru")
    print(f"\nFormatted original: {formatted_text}")
    print(f"Russian with values: {translated_formatted}")
    
    # Test batch translation
    print("\n--- Testing batch translation ---")
    texts = [
        "The weather is nice today.",
        "How are you doing?",
        "Artificial intelligence is fascinating."
    ]
    
    # Test direct batch
    print("Testing direct batch translation...")
    try:
        direct_translator_zh = GoogleTranslator(source='en', target='zh-CN')
        direct_batch = [direct_translator_zh.translate(t) for t in texts]
        print("Original texts:")
        for i, text in enumerate(texts):
            print(f"- {text} -> {direct_batch[i]}")
    except Exception as e:
        print(f"Direct batch translation error: {e}")
    
    # Test our batch implementation
    print("\nTesting our batch implementation...")
    chinese_translations = await batch_translate(texts, lang="zh")
    print("Results:")
    for i, translation in enumerate(chinese_translations):
        print(f"- {texts[i]} -> {translation}")

if __name__ == "__main__":
    asyncio.run(test_translation()) 