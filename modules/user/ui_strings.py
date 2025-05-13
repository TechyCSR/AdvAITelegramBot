"""
Module containing all UI strings used in the bot for easy translation.
"""

# Start and Help commands
START_MESSAGE = """
👋 Welcome to AdvChatGptBot!

I'm your advanced AI assistant powered by cutting-edge technology.

🔸 Chat directly with me
🔸 Send voice messages
🔸 Generate images with /img
🔸 Adjust settings with /settings
🔸 Clear chat history with /new

💡 For more information, use /help
"""

HELP_MESSAGE = """
**AdvChatGptBot Help**

**Commands:**
• /start - Start the bot
• /help - Show this help menu
• /settings - Configure bot settings
• /new or /newchat - Start a new conversation
• /img [prompt] - Generate an image
• /rate - Rate the bot

**Features:**
• Send text messages for AI responses
• Record voice messages for voice interaction
• Send images to extract text and get AI analysis
• In groups, use /ai to interact with the bot

Need more help? Use the settings menu to adjust language, voice preferences, and more.
"""

# Settings UI
SETTINGS_MAIN = "⚙️ **Bot Settings**\n\nCustomize your experience with AdvChatGptBot"
SETTINGS_VOICE = "🎙️ **Voice Settings**\n\nCurrent mode: {}\n\nChoose how you want to receive responses to voice messages"
SETTINGS_LANGUAGE = "🌐 **Language Settings**\n\nCurrent language: {}\n\nSelect your preferred interface language"
SETTINGS_ASSISTANT = "🤖 **Assistant Mode**\n\nCurrent mode: {}\n\nChoose the personality of your AI assistant"
SETTINGS_SUPPORT = "📞 **Support**\n\nGet help with using the bot"

# Buttons
BTN_BACK = "🔙 Back"
BTN_SETTINGS = "⚙️ Settings"
BTN_HELP = "❓ Help"
BTN_COMMANDS = "📋 Commands"

# Voice settings
VOICE_SETTING_UPDATED = "Voice setting updated to: {}"
TEXT_MODE = "Text mode"
VOICE_MODE = "Voice mode"

# Language settings
LANGUAGE_UPDATED = "Language updated to: {}"

# Assistant modes
MODE_UPDATED = "Assistant mode updated to: {}"
MODE_CHATBOT = "Chatbot"
MODE_CODER = "Coder"
MODE_PROFESSIONAL = "Professional"
MODE_TEACHER = "Teacher"
MODE_THERAPIST = "Therapist"
MODE_ASSISTANT = "Assistant"
MODE_GAMER = "Gamer"
MODE_TRANSLATOR = "Translator"

# Image generation
GENERATING_IMAGES = "🖼️ Generating images. Please wait..."
IMAGES_GENERATED = "Images generated for prompt: {}"

# Voice messages
PROCESSING_VOICE = "🎙️ Processing your voice message..."
VOICE_NOT_UNDERSTOOD = "Sorry, I couldn't understand the audio."
VOICE_SERVICE_ERROR = "There was an issue with the speech recognition service. Please try again later."

# OCR
EXTRACTING_TEXT = "🔍 Extracting text from image..."
OCR_ERROR = "Error: Failed to extract text from image. {}"

# New chat
CHAT_CLEARED = "Your chat history has been cleared. You can start a new conversation now."

# Rate bot
RATE_MESSAGE = "⭐ Please rate your experience with AdvChatGptBot"
RATE_THANK_YOU = "Thank you for your feedback! Your rating: {}/5"

# Error messages
ERROR_OCCURRED = "An error occurred: {}"
COMMAND_NOT_ALLOWED = "You are not allowed to use this command."