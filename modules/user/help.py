


import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from pyrogram.types import CallbackQuery



from modules.lang import translate_to_lang, default_lang
from modules.chatlogs import channel_log


help_text = """

**📚 Help Menu**

**Commands:**
- **/start** - 🚀 Start the Bot
- **/help** - ❓ Show this Help Menu
- **/settings** - ⚙️ Configure Bot Settings
- **/support** - 🛠️ Contact Support Team
- **/features** - 🌟 View Bot Features
- **/about** - ℹ️ About This Bot

**Features:**
- **AI ChatBot (GPT-4)** - 🧠 Intelligent Conversations
- **AI Speech to Text & Vice Versa** - 🎙️ Seamless Voice Interaction
- **AI Generative Images (DALL-E Model)** - 🎨 Create Stunning Images
- **AI Image to Text (Google Lens)** - 🖼️ Extract Text from Images

**Configuration Options:**
- **Language Preferences** - 🌐 Multi-Language Support
- **Notification Settings** - 🔔 Customize Notifications
- **Privacy Settings** - 🔒 Secure Your Data



"""


async def help(client, message):
    global help_text
    # if default_lang !="en":
    #     help_text = translate_to_lang(help_text, default_lang )
    await client.send_message(
        chat_id=message.chat.id,
        text=help_text,
        disable_web_page_preview=True
    )
    await channel_log(client, message, "/help")

async def help_inline(bot, callback):
    global help_text
    keyboard=InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔙 Back", callback_data="back")
            ]
        ]
    )

    # if default_lang !="en":
    #     help_text = translate_to_lang(help_text, default_lang )
    await bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.id,
        text=help_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

    await channel_log(bot, callback.message, "/help")
    await callback.answer()
    return
    
