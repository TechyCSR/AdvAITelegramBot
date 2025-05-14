import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from pyrogram.types import CallbackQuery
from modules.lang import async_translate_to_lang, batch_translate, format_with_mention
from modules.chatlogs import channel_log
import database.user_db as user_db

# Define button texts
button_list = [
    "Add to Group",
    "Commands",
    "Help",
    "Settings",
    "Support"
]

welcome_text = """
**Welcome {user_mention}!** 👋

I'm an advanced AI-powered Telegram bot that can:
- Chat intelligently using GPT-4
- Convert voice messages to text and vice versa
- Generate images from text descriptions
- Extract text from images
- Support multiple languages

Use the buttons below to explore my features!

**@AdvChatGptBot**
"""

tip_text = "💡 Tip: You can use /help to see all available commands!"

LOGO = "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExdnp4MnR0YXk3ZGNjenR6NGRoaDNkc2h2NDgxa285NnExaGM1MTZmYyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/S60CrN9iMxFlyp7uM8/giphy.gif"

async def start(client, message):
    await user_db.check_and_add_user(message.from_user.id)
    if message.from_user.username:
        await user_db.check_and_add_username(message.from_user.id, message.from_user.username)

    # Get user info
    user_id = message.from_user.id
    mention = message.from_user.mention
    
    # First safely format the welcome text with mention preservation
    user_lang = user_db.get_user_language(user_id)
    translated_welcome = await format_with_mention(welcome_text.replace("{user_mention}", "{mention}"), mention, user_id, user_lang)
    
    # Translate other texts
    translated_texts = await batch_translate([tip_text] + button_list, user_id)
    translated_tip = translated_texts[0]
    translated_buttons = translated_texts[1:]

    # Create the inline keyboard buttons with translated text
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(translated_buttons[0] + " 🔥 ", url=f"https://t.me/{client.me.username}?startgroup=true")],
        [InlineKeyboardButton(translated_buttons[1] + " 🛠️ ", callback_data="commands"),
         InlineKeyboardButton(translated_buttons[2] + " 💬 ", callback_data="help")],
        [InlineKeyboardButton(translated_buttons[3] + " ⚙️ ", callback_data="settings"),
         InlineKeyboardButton(translated_buttons[4] + " 🆘 ", callback_data="support")]
    ])

    # Send the welcome message with the GIF and the keyboard
    await client.send_animation(
        chat_id=message.chat.id,
        animation=LOGO,
        caption=translated_welcome,
        reply_markup=keyboard
    )
    await message.reply_text(translated_tip)

async def start_inline(bot, callback):
    user_id = callback.from_user.id
    mention = callback.from_user.mention

    # First safely format the welcome text with mention preservation
    user_lang = user_db.get_user_language(user_id)
    translated_welcome = await format_with_mention(welcome_text.replace("{user_mention}", "{mention}"), mention, user_id, user_lang)
    
    # Translate button texts
    translated_buttons = await batch_translate(button_list, user_id)

    # Create the inline keyboard buttons with translated text
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(translated_buttons[0] + " 🔥 ", url=f"https://t.me/{bot.me.username}?startgroup=true")],
        [InlineKeyboardButton(translated_buttons[1] + " 🛠️ ", callback_data="commands"),
         InlineKeyboardButton(translated_buttons[2] + " 💬 ", callback_data="help")],
        [InlineKeyboardButton(translated_buttons[3] + " ⚙️ ", callback_data="settings"),
         InlineKeyboardButton(translated_buttons[4] + " 🆘 ", callback_data="support")]
    ])

    # Send the welcome message with the GIF and the keyboard
    await bot.edit_message_caption(
        chat_id=callback.message.chat.id,
        message_id=callback.message.id,
        caption=translated_welcome,
        reply_markup=keyboard
    )

