import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from pyrogram.types import CallbackQuery
from modules.lang import translate_to_lang, default_lang
from modules.chatlogs import channel_log


help_text = """
**📚 Telegram @AdvChatGptBot 's Help Menu**

**🧠 AI-Powered Features:**
- **Intelligent ChatBot (GPT-4)** - Engage in dynamic, context-aware conversations
- **Voice Interaction** - Seamlessly convert speech to text and vice versa
- **Image Generation (DALL-E 3)** - Transform your ideas into stunning visuals
- **Visual Analysis (Google Lens)** - Extract insights and text from any image

**⚙️ Customization Options:**
- **🌐 Language Preferences** - Communicate in your preferred language
- **🔔 Smart Notifications** - Tailor alerts to your needs
- **🔒 Privacy Controls** - Manage your data securely

**Commands:**
- **/start** -Start the Bot
- **/ai** - Start a Chat with AI in Groups 
- **/img or /image** - Generate Text from Image
- **/new or /newchat ** - Start a New Chat and Clear Previous Chat History

**@AdvChatGptBot**
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

    await callback.answer()
    return
    
