
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Global dictionary for storing current mode per user
current_mode = {}



# Dictionary of modes with labels
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

# Function to handle settings assistant callback
async def settings_assistant_callback(client, callback):
    user_id = callback.from_user.id
    # Set default value to Chatbot if not set
    if user_id not in current_mode:
        current_mode[user_id] = "chatbot"

    current_mode_label = modes[current_mode[user_id]]
    message_text = f"Current mode: {current_mode_label}"

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🤖 Chatbot", callback_data="mode_chatbot"),
                InlineKeyboardButton("💻 Coder/Developer", callback_data="mode_coder")
            ],
            [
                InlineKeyboardButton("👔 Professional", callback_data="mode_professional"),
                InlineKeyboardButton("📚 Teacher", callback_data="mode_teacher")
            ],
            [
                InlineKeyboardButton("🩺 Therapist", callback_data="mode_therapist"),
                InlineKeyboardButton("📝 Assistant", callback_data="mode_assistant")
            ],
            [
                InlineKeyboardButton("🎮 Gamer", callback_data="mode_gamer"),
                InlineKeyboardButton("🌐 Translator", callback_data="mode_translator")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="settings_back")
            ]
        ]
    )

    await callback.message.edit(
        text=message_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

# Function to handle mode setting change
async def change_mode_setting(client, callback):
    mode = callback.data.split("_")[1]
    user_id = callback.from_user.id
    current_mode[user_id] = mode

    current_mode_label = modes[current_mode[user_id]]
    message_text = f"Current mode: {current_mode_label}"

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🤖 Chatbot", callback_data="mode_chatbot"),
                InlineKeyboardButton("💻 Coder/Developer", callback_data="mode_coder")
            ],
            [
                InlineKeyboardButton("👔 Professional", callback_data="mode_professional"),
                InlineKeyboardButton("📚 Teacher", callback_data="mode_teacher")
            ],
            [
                InlineKeyboardButton("🩺 Therapist", callback_data="mode_therapist"),
                InlineKeyboardButton("📝 Assistant", callback_data="mode_assistant")
            ],
            [
                InlineKeyboardButton("🎮 Gamer", callback_data="mode_gamer"),
                InlineKeyboardButton("🌐 Translator", callback_data="mode_translator")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="settings_back")
            ]
        ]
    )

    await callback.message.edit(
        text=message_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
