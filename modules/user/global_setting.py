
from pyrogram import Client, filters


from config import DATABASE_URL, LOG_CHANNEL
from pymongo import MongoClient
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

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

global_settings_text = """
**Setting Menu for User {mention}**

**User ID**: {user_id}
**User language:** {default_lang}
**User voice**: {voice_setting}
**User mode**: {mode}

You can change your settings from @AdvChatGptBot's settings menu.
"""


async def global_setting_command(client, message):
    global global_settings_text
    temp= await message.reply_text("**Fetching your settings...**")

    user_id = message.from_user.id
    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
    if user_lang_doc:
        current_language = user_lang_doc['language']
    else:
        current_language = "en"
        user_lang_collection.insert_one({"user_id": user_id, "language": current_language})
    user_settings = user_voice_collection.find_one({"user_id": user_id})
    
    if user_settings:
        voice_setting = user_settings.get("voice", "voice")
    else:
        voice_setting = "voice"
        # If user doesn't exist, add them with default setting "voice"
        user_voice_collection.insert_one({"user_id": user_id, "voice": "voice"})
    
    user_mode_doc = ai_mode_collection.find_one({"user_id": user_id})

    if user_mode_doc:
        current_mode = user_mode_doc['mode']
    else:
        current_mode = "chatbot"
        ai_mode_collection.insert_one({"user_id": user_id, "mode": current_mode})
    
    current_mode_label = modes[current_mode]

    global_settings_text = global_settings_text.format(
        mention=message.from_user.mention,
        user_id=message.from_user.id,
        default_lang=current_language,
        voice_setting=voice_setting,
        mode=current_mode_label,
    )

    #on the keyboard, only onebutton to bot settings

    kbd=InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔧 Bot Settings", url=f"https://t.me/{client.me.username}?start=settings")
            ]
        ]
    )

    await message.reply_text(global_settings_text, reply_markup=kbd)
    await temp.delete()