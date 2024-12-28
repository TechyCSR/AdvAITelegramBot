
import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery

from modules.chatlogs import channel_log


from modules.lang import translate_to_lang, default_lang


command__text = """**Commands:**
- **/start** - 🚀 Start the Bot
- **/help** - ❓ Show this Help Menu
- **/settings** - ⚙️ Configure Bot Settings

**Features:**
- **AI ChatBot (GPT-4)** - 🧠 Intelligent Conversations
- **AI Speech to Text & Vice Versa** - 🎙️ Seamless Voice Interaction
- **AI Generative Images (DALL-E 3 Model)** - 🎨 Create Stunning Images
- **AI Image to Text (Google Lens)** - 🖼️ Extract Text from Images
- **Mutiple Modes** - 🔄 Change ChatBot Modes
- **Can be added to Groups** - 👥 Enable in Group Chats"""

async def command_inline(client, callback):
    global command__text
    keyboard=InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔙 Back", callback_data="back")
            ]
        ]
    )
    await callback.message.edit(
        text=command__text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    


