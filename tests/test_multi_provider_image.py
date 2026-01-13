"""
Test script for the multi-provider image generation system.
Run this to verify the providers are working correctly.
"""

import asyncio
import sys
sys.path.insert(0, '/home/techycsr/Documents/Projects/AdvAITelegramBot')

from modules.image.multi_provider_image import (
    generate_with_fallback,
    generate_with_provider,
    get_providers_for_model,
    IMAGE_PROVIDERS,
    DEFAULT_IMAGE_MODEL,
)


async def test_single_provider():
    """Test a single provider directly"""
    print("=" * 60)
    print("Testing single provider: BlackForestLabs_Flux1Dev with flux-dev")
    print("=" * 60)
    
    # Get BlackForestLabs provider
    provider = None
    for p in IMAGE_PROVIDERS:
        if p.name == "BlackForestLabs_Flux1Dev":
            provider = p
            break
    
    if not provider:
        print("❌ BlackForestLabs_Flux1Dev provider not found!")
        return
    
    urls, error = await generate_with_provider(
        provider=provider,
        prompt="A beautiful sunset over mountains, ultra realistic",
        model="flux-dev",
        width=512,
        height=512,
        num_images=1,
    )
    
    if urls:
        print(f"✅ SUCCESS! Generated {len(urls)} image(s)")
        for i, url in enumerate(urls):
            print(f"   Image {i+1}: {url[:80]}...")
    else:
        print(f"❌ FAILED: {error}")


async def test_multi_provider_fallback():
    """Test the full multi-provider fallback system"""
    print("\n" + "=" * 60)
    print("Testing multi-provider fallback system")
    print("=" * 60)
    
    urls, error = await generate_with_fallback(
        prompt="A cute cat playing with a ball of yarn, photorealistic",
        model=DEFAULT_IMAGE_MODEL,
        width=512,
        height=512,
        num_images=1,
        try_concurrent=True,
    )
    
    if urls:
        print(f"✅ SUCCESS! Generated {len(urls)} image(s)")
        for i, url in enumerate(urls):
            print(f"   Image {i+1}: {url[:80]}...")
    else:
        print(f"❌ FAILED: {error}")


async def test_all_providers():
    """Test each provider individually"""
    print("\n" + "=" * 60)
    print("Testing all providers individually")
    print("=" * 60)
    
    results = []
    
    for provider in IMAGE_PROVIDERS:
        model = provider.models[0]  # Use first available model
        print(f"\n🔄 Testing {provider.name} with model {model}...")
        
        urls, error = await generate_with_provider(
            provider=provider,
            prompt="A simple red apple on white background",
            model=model,
            width=512,
            height=512,
            num_images=1,
        )
        
        if urls:
            print(f"   ✅ SUCCESS: {urls[0][:60]}...")
            results.append((provider.name, model, True, None))
        else:
            print(f"   ❌ FAILED: {error[:60] if error else 'Unknown error'}...")
            results.append((provider.name, model, False, error))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r[2])
    print(f"\nTotal: {len(results)} providers tested")
    print(f"Success: {success_count}")
    print(f"Failed: {len(results) - success_count}")
    
    print("\nDetailed Results:")
    for name, model, success, error in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name} ({model})")


async def main():
    print("Multi-Provider Image Generation Test")
    print("=" * 60)
    print("Available providers:")
    for p in IMAGE_PROVIDERS:
        print(f"  - {p.name}: {p.models}")
    print(f"\nDefault model: {DEFAULT_IMAGE_MODEL}")
    print("=" * 60)
    
    # Run tests
    await test_single_provider()
    await test_multi_provider_fallback()
    
    # Optionally test all providers (slower)
    response = input("\nDo you want to test all providers individually? (y/n): ")
    if response.lower() == 'y':
        await test_all_providers()


if __name__ == "__main__":
    asyncio.run(main())
