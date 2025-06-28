# Example configuration for AdvAITelegramBot

# --- Required ---
BOT_TOKEN = "your_telegram_bot_token"  # From BotFather
API_KEY = "your_telegram_api_key"      # From my.telegram.org
API_HASH = "your_telegram_api_hash"    # From my.telegram.org
DATABASE_URL = "mongodb://localhost:27017/"  # MongoDB connection string
ADMINS = [123456789]  # List of Telegram user IDs with admin rights

# --- Optional Advanced Settings ---
# Minutes before uploaded images are auto-deleted (default: 2)
IMAGE_CONTEXT_EXPIRY_MINUTES = 2
# List of premium models (shown only to premium users)
PREMIUM_MODELS = ["gpt-4o", "dalle3"]
# Enable multi-bot support (one process per bot)
MULTI_BOT = True

# Add any other custom settings below as needed 