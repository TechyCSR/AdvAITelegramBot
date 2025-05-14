import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from pyrogram.types import CallbackQuery
from modules.lang import async_translate_to_lang, batch_translate, translate_ui_element
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
    user_id = message.from_user.id
    translated_text = await async_translate_to_lang(help_text, user_id)
    
    # Add back button for consistency
    back_btn = await translate_ui_element("🔙 Back", user_id)
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(back_btn, callback_data="back")
            ]
        ]
    )
    
    await client.send_message(
        chat_id=message.chat.id,
        text=translated_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

async def help_inline(bot, callback):
    user_id = callback.from_user.id
    translated_text = await async_translate_to_lang(help_text, user_id)
    
    # Translate back button
    back_btn = await translate_ui_element("🔙 Back", user_id)
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(back_btn, callback_data="back")
            ]
        ]
    )

    await bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.id,
        text=translated_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

    await callback.answer()
    return
    
