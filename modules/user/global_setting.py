from pyrogram import Client, filters
from config import DATABASE_URL, LOG_CHANNEL
from pymongo import MongoClient
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from modules.lang import async_translate_to_lang

# Initialize the MongoDB client
mongo_client = MongoClient(DATABASE_URL)

# Access or create the database and collection
db = mongo_client['aibotdb']
user_lang_collection = db['user_lang']
user_voice_collection = db["user_voice_setting"]
ai_mode_collection = db['ai_mode']

modes = {
    "chatbot": "Chatbot",
    "coder": "Coder/Developer",
    "professional": "Professional",
    "teacher": "Teacher",
    "therapist": "Therapist",
    "assistant": "Personal Assistant",
    "gamer": "Gamer",
    "translator": "Translator"
}

languages = {
    "en": "🇬🇧 English",
    "hi": "🇮🇳 Hindi",
    "zh": "🇨🇳 Chinese",
    "ar": "🇸🇦 Arabic",
    "fr": "🇫🇷 French",
    "ru": "🇷🇺 Russian"
}

async def global_setting_command(client, message):
    user_id = message.from_user.id
    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
    if user_lang_doc:
        current_language = user_lang_doc['language']
    else:
        current_language = "en"
        user_lang_collection.insert_one({"user_id": user_id, "language": current_language})
    current_language_label = languages[current_language]
    user_settings = user_voice_collection.find_one({"user_id": user_id})
    if user_settings:
        voice_setting = user_settings.get("voice", "voice")
        if voice_setting == "text":
            voice_setting_label = "💬 Text"
        else:
            voice_setting_label = "🎙️ Voice"
    else:
        voice_setting = "voice"
        voice_setting_label = "🎙️ Voice"
        user_voice_collection.insert_one({"user_id": user_id, "voice": "voice"})
    user_mode_doc = ai_mode_collection.find_one({"user_id": user_id})
    if user_mode_doc:
        current_mode = user_mode_doc['mode']
    else:
        current_mode = "chatbot"
        ai_mode_collection.insert_one({"user_id": user_id, "mode": current_mode})
    current_mode_label = modes[current_mode]
    # Modern summary at the top
    summary = (
        f"⚙️ <b>Your Settings</b>\n\n"
        f"<b>Language:</b> {languages.get(current_language, current_language)}\n"
        f"<b>Voice:</b> {voice_setting_label}\n"
        f"<b>Assistant Mode:</b> {current_mode_label}\n"
    )
    # Main settings panel buttons
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌐 Language", callback_data="settings_lans"),
            InlineKeyboardButton("🎙️ Voice", callback_data="settings_v")
        ],
        [
            InlineKeyboardButton("🤖 Assistant Mode", callback_data="settings_assistant"),
            InlineKeyboardButton("📞 Support", callback_data="settings_support")
        ],
        [
            InlineKeyboardButton("🔄 Reset Conversation", callback_data="settings_reset")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back")
        ]
    ])
    temp = await message.reply_text("**Loading your settings...**")
    await message.reply(
        summary + "\n<b>Select a setting to change:</b>",
        reply_markup=keyboard,
        parse_mode="html",
        disable_web_page_preview=True
    )
    await temp.delete()