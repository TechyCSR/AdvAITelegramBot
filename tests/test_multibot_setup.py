#!/usr/bin/env python3
"""
Multi-Bot Setup Test Script
This script tests and demonstrates how to set up multiple bot instances.
"""

import os
import sys
import subprocess
import tempfile

def test_single_bot_mode():
    """Test single bot mode configuration"""
    print("🧪 Testing Single Bot Mode...")
    
    # Set environment for single bot
    env = os.environ.copy()
    env['MULTIPLE_BOTS'] = 'false'
    env['NUM_OF_BOTS'] = '1'
    env['BOT_TOKEN'] = 'test_token_123:single'
    
    # Test configuration
    cmd = [
        sys.executable, '-c',
        'import config; print("Multi-bot:", config.MULTIPLE_BOTS); '
        'print("Num bots:", config.NUM_OF_BOTS); '
        'tokens = config.get_bot_tokens(); print("Tokens:", len(tokens))'
    ]
    
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    if "Multi-bot: False" in result.stdout and "Tokens: 1" in result.stdout:
        print("✅ Single bot mode test PASSED")
        return True
    else:
        print("❌ Single bot mode test FAILED")
        print("Output:", result.stdout)
        return False

def test_multi_bot_mode():
    """Test multi-bot mode configuration"""
    print("🧪 Testing Multi-Bot Mode...")
    
    # Set environment for multi-bot
    env = os.environ.copy()
    env['MULTIPLE_BOTS'] = 'true'
    env['NUM_OF_BOTS'] = '3'
    env['BOT_TOKEN1'] = 'test_token_123:bot1'
    env['BOT_TOKEN2'] = 'test_token_456:bot2'
    env['BOT_TOKEN3'] = 'test_token_789:bot3'
    
    # Test configuration
    cmd = [
        sys.executable, '-c',
        'import config; print("Multi-bot:", config.MULTIPLE_BOTS); '
        'print("Num bots:", config.NUM_OF_BOTS); '
        'tokens = config.get_bot_tokens(); print("Tokens:", len(tokens))'
    ]
    
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    if "Multi-bot: True" in result.stdout and "Tokens: 3" in result.stdout:
        print("✅ Multi-bot mode test PASSED")
        return True
    else:
        print("❌ Multi-bot mode test FAILED")
        print("Output:", result.stdout)
        return False

def test_missing_token_error():
    """Test that missing tokens cause proper error"""
    print("🧪 Testing Missing Token Error Handling...")
    
    # Set environment with missing token
    env = os.environ.copy()
    env['MULTIPLE_BOTS'] = 'true'
    env['NUM_OF_BOTS'] = '2'
    env['BOT_TOKEN1'] = 'test_token_123:bot1'
    # BOT_TOKEN2 is missing intentionally
    if 'BOT_TOKEN2' in env:
        del env['BOT_TOKEN2']
    
    # Test configuration
    cmd = [
        sys.executable, '-c',
        'import config; tokens = config.get_bot_tokens()'
    ]
    
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    if result.returncode != 0 and "BOT_TOKEN2 is required" in result.stderr:
        print("✅ Missing token error test PASSED")
        return True
    else:
        print("❌ Missing token error test FAILED")
        print("Return code:", result.returncode)
        print("Stderr:", result.stderr)
        return False

def show_setup_instructions():
    """Show instructions for setting up multi-bot mode"""
    print("\n" + "="*60)
    print("📖 HOW TO ENABLE MULTI-BOT MODE")
    print("="*60)
    print()
    
    print("1️⃣ Set Environment Variables:")
    print("   export MULTIPLE_BOTS=true")
    print("   export NUM_OF_BOTS=3")
    print("   export BOT_TOKEN1='your_first_bot_token'")
    print("   export BOT_TOKEN2='your_second_bot_token'")
    print("   export BOT_TOKEN3='your_third_bot_token'")
    print()
    
    print("2️⃣ Or create a .env file:")
    print("   MULTIPLE_BOTS=true")
    print("   NUM_OF_BOTS=3")
    print("   BOT_TOKEN1=your_first_bot_token")
    print("   BOT_TOKEN2=your_second_bot_token")
    print("   BOT_TOKEN3=your_third_bot_token")
    print()
    
    print("3️⃣ Run the bot:")
    print("   python run.py")
    print()
    
    print("📋 Example .env file for 2 bots:")
    print("   " + "-"*30)
    print("   MULTIPLE_BOTS=true")
    print("   NUM_OF_BOTS=2")
    print("   BOT_TOKEN1=123456789:ABCDefghijklmnopqrstuvwxyz")
    print("   BOT_TOKEN2=987654321:ZYXwvutsrqponmlkjihgfedcba")
    print("   " + "-"*30)
    print()

def create_sample_env_file():
    """Create a sample .env file for multi-bot setup"""
    sample_content = """# Multi-Bot Configuration
MULTIPLE_BOTS=true
NUM_OF_BOTS=2

# Bot Tokens (get these from @BotFather)
BOT_TOKEN1=your_first_bot_token_here
BOT_TOKEN2=your_second_bot_token_here

# Other required settings
API_ID=your_api_id
API_HASH=your_api_hash
DATABASE_URL=mongodb://localhost:27017/
ADMIN_IDS=your_user_id
OWNER_ID=your_user_id
"""
    
    try:
        with open('.env.multibot.example', 'w') as f:
            f.write(sample_content)
        print(f"✅ Created sample file: .env.multibot.example")
        print("💡 Copy this to .env and fill in your actual values")
    except Exception as e:
        print(f"❌ Error creating sample file: {e}")

def main():
    print("🚀 Multi-Bot Setup Test Suite")
    print("="*50)
    
    # Run tests
    tests_passed = 0
    total_tests = 3
    
    if test_single_bot_mode():
        tests_passed += 1
    
    if test_multi_bot_mode():
        tests_passed += 1
    
    if test_missing_token_error():
        tests_passed += 1
    
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests PASSED! Multi-bot configuration is working correctly.")
    else:
        print("⚠️  Some tests FAILED. Please check the configuration.")
    
    # Show setup instructions
    show_setup_instructions()
    
    # Create sample env file
    print("📁 Creating sample configuration file...")
    create_sample_env_file()
    
    print("\n🔧 Current Configuration Status:")
    try:
        import config
        print(f"   Multi-bot enabled: {config.MULTIPLE_BOTS}")
        print(f"   Number of bots: {config.NUM_OF_BOTS}")
        tokens = config.get_bot_tokens()
        print(f"   Available tokens: {len(tokens)}")
    except Exception as e:
        print(f"   Error reading config: {e}")

if __name__ == "__main__":
    main() 