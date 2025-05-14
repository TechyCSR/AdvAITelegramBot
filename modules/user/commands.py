import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from pyrogram.types import CallbackQuery
from modules.lang import async_translate_to_lang, batch_translate, translate_ui_element
from modules.chatlogs import channel_log


command__text = """
**🤖 Bot Commands 🤖**

**/start** - Start the bot and see the welcome message
**/help** - Show help information
**/ai** - Use in groups to ask a question directly 
**/img** or **/image** - Generate an image from text prompt
**/settings** - Configure bot settings
**/new** or **/newchat** - Start a new chat and clear history
**/rate** - Rate your experience with the bot

**In Groups:**  
- Use `/ai [question]` to ask the AI directly
- Add an image with caption "ai" to extract text and analyze

**@AdvChatGptBot**
"""


async def command_inline(client, callback):
    user_id = callback.from_user.id
    
    # Translate both the command text and back button in parallel
    texts_to_translate = [command__text, "🔙 Back"]
    translated_texts = await batch_translate(texts_to_translate, user_id)
    
    # Extract translated results
    translated_command = translated_texts[0]
    back_btn = translated_texts[1]
    
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(back_btn, callback_data="back")
            ]
        ]
    )

    await client.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.id,
        text=translated_command,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

    await callback.answer()
    return


