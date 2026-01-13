#!/usr/bin/env python3
"""
Test script for multi-provider text generation system
"""

import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Direct import from the module file to avoid circular imports
import importlib.util
spec = importlib.util.spec_from_file_location(
    "multi_provider_text", 
    os.path.join(parent_dir, "modules/models/multi_provider_text.py")
)
multi_provider_text = importlib.util.module_from_spec(spec)
spec.loader.exec_module(multi_provider_text)

generate_text_sync = multi_provider_text.generate_text_sync
TEXT_PROVIDERS = multi_provider_text.TEXT_PROVIDERS
TEXT_MODEL_MAPPING = multi_provider_text.TEXT_MODEL_MAPPING
normalize_model_name = multi_provider_text.normalize_model_name

def test_text_generation():
    """Test text generation with multi-provider system"""
    print("=" * 60)
    print("Testing Multi-Provider Text Generation System")
    print("=" * 60)
    
    # Show available providers
    print("\nAvailable Providers:")
    for p in TEXT_PROVIDERS:
        print(f"  - {p['name']} (priority: {p['priority']}, models: {p.get('models', ['all'])})")
    
    # Show model mappings
    print("\nModel Mappings:")
    for user_model, actual_model in TEXT_MODEL_MAPPING.items():
        print(f"  - {user_model} → {actual_model}")
    
    # Test prompt
    test_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'Hello, multi-provider text works!' in exactly those words."}
    ]
    
    print("\n" + "=" * 60)
    print("Testing text generation with default model (qwen3)...")
    print("=" * 60)
    
    response, error = generate_text_sync(
        messages=test_messages,
        model="qwen3",
        temperature=0.7,
        max_tokens=100,
    )
    
    if error:
        print(f"❌ Error: {error}")
    else:
        print(f"✅ Response: {response[:200]}...")
        
    print("\n" + "=" * 60)
    print("Testing with gpt-4o model...")
    print("=" * 60)
    
    response2, error2 = generate_text_sync(
        messages=test_messages,
        model="gpt-4o",
        temperature=0.7,
        max_tokens=100,
    )
    
    if error2:
        print(f"❌ Error: {error2}")
    else:
        print(f"✅ Response: {response2[:200]}...")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_text_generation()
