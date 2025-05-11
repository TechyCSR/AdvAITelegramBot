import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from modules.chatlogs import channel_log
from modules.lang import translate_to_lang

command__text = """**Commands:**

**You directly start typing to chat with AI.**

**Here are some commands you can use to control the bot:**

- **/start** - 🚀 Start the Bot
- **/ai** - 🤖 Start a Chat with AI in Groups
(Eg: `/ai what is the capital of India?`)
- **/img or /image** - 🖼️ Generate image from given prompt
- **/settings** - ⚙️ Configure Bot Settings
- **/new or /newchat ** - 🔄 Start a New Chat and Clear Previous Chat History
- **/rate** - ⭐ Rate the Bot
- **/help** - ❓ Show this Help Menu


**Voice and Image Commands:**

Directly record a voice message or send an image to chat with AI.
In group send image with caption "ai" or "ask" to extract text from image and send it to ai.

Eg: `/img Sunset on a beach` or `/image Sunset on a beach` |

**@AdvChatGptBot**
"""

async def command_inline(client, callback):
    user_id = callback.from_user.id
    translated_text = translate_to_lang(command__text, user_id)
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔙 Back", callback_data="back")
            ]
        ]
    )
    await callback.message.edit(
        text=translated_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    


