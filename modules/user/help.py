import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from pyrogram.types import CallbackQuery
from modules.lang import async_translate_to_lang, batch_translate, translate_ui_element
from modules.chatlogs import channel_log


help_text = """
✨ **ADVANCED AI BOT - HELP CENTER** ✨

━━━━━━━━━━━━━━━━━━━

This intelligent bot was created by **Chandan Singh** (@techycsr) 
to bring powerful AI features directly to your Telegram chats.

**SELECT A CATEGORY BELOW:**
"""

ai_chat_help = """
🧠 **AI CHAT ASSISTANT** 🧠

━━━━━━━━━━━━━━━━━━━

The bot uses **GPT-4o** to provide intelligent responses to any question.

**KEY FEATURES:**
• 💬 **Context-aware** - Remembers conversation history
• 🧩 **Complex questions** - Detailed, thoughtful answers
• 💻 **Code generation** - With syntax highlighting
• 🔢 **Math solver** - Works with equations & problems
• 🌎 **Translation** - Works in multiple languages

**COMMANDS:**
• 💬 In private chats: Just type your message
• 🔄 In groups: Use `/ai`, `/ask`, or `/say` + question
• 🆕 Reset chat: Use `/new` or `/newchat`

**EXAMPLE:** 
`/ai What makes quantum computing different from classical computing?`

**💡 PRO TIP:** For code questions, mention the programming language for better formatting.
"""

image_gen_help = """
🖼️ **IMAGE GENERATION** 🖼️

━━━━━━━━━━━━━━━━━━━

Create stunning images from text descriptions using advanced AI.

**KEY FEATURES:**
• 🎨 **High-quality images** - Detailed & realistic
• 🏞️ **Multiple styles** - Realistic, Artistic, Sketch, 3D
• 🔄 **Regeneration** - One-click retry with same prompt
• 👥 **Works everywhere** - Private chats & groups

**COMMANDS:**
• 📝 `/generate [prompt]` - Full command
• 📸 `/img [prompt]` - Shorter alternative
• 🖌️ `/gen [prompt]` - Shortest version

**EXAMPLE:**
`/img a cyberpunk city at night with neon lights and flying cars`

**💡 PRO TIPS:**
• Be specific about details, lighting, and perspective
• Include artistic references for better results
• Try different styles for varied outputs
"""

voice_features_help = """
🎙️ **VOICE FEATURES** 🎙️

━━━━━━━━━━━━━━━━━━━

Convert between voice and text with advanced speech processing.

**KEY FEATURES:**
• 🗣️ **Voice-to-text** - Transcribe voice messages
• 🔊 **Text-to-voice** - Listen to bot responses
• 🌐 **Multilingual** - Works in multiple languages
• 💬 **Conversation** - Ask questions by voice

**HOW TO USE:**
1. 🎤 Send a voice message
2. 📝 Bot converts to text & understands
3. 💬 Bot responds to your question
4. ⚙️ Adjust voice settings in Settings menu

**💡 PRO TIPS:**
• Speak clearly in a quiet environment
• Keep messages under 1 minute for best results
• Set your preferred voice language in settings
"""

image_analysis_help = """
🔍 **IMAGE ANALYSIS** 🔍

━━━━━━━━━━━━━━━━━━━

Extract and analyze text from any image with smart OCR technology.

**KEY FEATURES:**
• 📱 **Text extraction** - From photos & screenshots
• 📄 **Document scanning** - Read printed documents
• ❓ **Follow-up questions** - Ask about extracted text
• 📊 **Data recognition** - Tables, receipts & more

**HOW TO USE:**
1. 📷 Send any image with text
2. 🔍 Bot extracts all readable text
3. 💬 Ask follow-up questions about the content
4. 📱 In groups, add "ai" in image caption

**💡 PRO TIPS:**
• Use good lighting for clearer results
• Capture text straight-on, not at angles
• Crop to focus on the important text
"""

quick_start_help = """
🚀 **QUICK START GUIDE** 🚀

━━━━━━━━━━━━━━━━━━━

**GET STARTED IN 3 STEPS:**

1️⃣ **Chat with AI**
   • Private: Just type any message
   • Groups: Use `/ai` command

2️⃣ **Generate Images**
   • Use `/img` followed by description
   • Example: `/img sunset over mountains`

3️⃣ **Analyze Images**
   • Send any image with text
   • Bot will extract and analyze

**USEFUL COMMANDS:**
• `/start` - Main menu
• `/help` - This help center
• `/settings` - Configure bot preferences
• `/new` - Clear conversation history

**HAVING TROUBLE?**
• Select the Support button from main menu
• Try more specific prompts for better results
"""


async def help(client, message):
    user_id = message.from_user.id
    
    # Translate help text and button labels
    texts_to_translate = [
        help_text, 
        "🧠 AI Chat", 
        "🖼️ Image Generation", 
        "🎙️ Voice Features",
        "🔍 Image Analysis",
        "🚀 Quick Start",
        "📋 Commands"
    ]
    
    translated_texts = await batch_translate(texts_to_translate, user_id)
    
    translated_help = translated_texts[0]
    ai_btn = translated_texts[1]
    img_btn = translated_texts[2]
    voice_btn = translated_texts[3]
    analysis_btn = translated_texts[4]
    quickstart_btn = translated_texts[5]
    cmd_btn = translated_texts[6]
    
    # Create interactive keyboard with feature categories
    # No back button when accessed directly through /help command
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(ai_btn, callback_data="help_ai")],
        [InlineKeyboardButton(img_btn, callback_data="help_img")],
        [InlineKeyboardButton(voice_btn, callback_data="help_voice")],
        [InlineKeyboardButton(analysis_btn, callback_data="help_analysis")],
        [InlineKeyboardButton(quickstart_btn, callback_data="help_quickstart")],
        [InlineKeyboardButton(cmd_btn, callback_data="commands")]
    ])
    
    await client.send_message(
        chat_id=message.chat.id,
        text=translated_help,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

async def help_inline(bot, callback):
    user_id = callback.from_user.id
    
    # Translate help text and button labels
    texts_to_translate = [
        help_text, 
        "🧠 AI Chat", 
        "🖼️ Image Generation", 
        "🎙️ Voice Features",
        "🔍 Image Analysis",
        "🚀 Quick Start",
        "📋 Commands",
        "🔙 Back"
    ]
    
    translated_texts = await batch_translate(texts_to_translate, user_id)
    
    translated_help = translated_texts[0]
    ai_btn = translated_texts[1]
    img_btn = translated_texts[2]
    voice_btn = translated_texts[3]
    analysis_btn = translated_texts[4]
    quickstart_btn = translated_texts[5]
    cmd_btn = translated_texts[6]
    back_btn = translated_texts[7]
    
    # Create interactive keyboard with feature categories
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(ai_btn, callback_data="help_ai")],
        [InlineKeyboardButton(img_btn, callback_data="help_img")],
        [InlineKeyboardButton(voice_btn, callback_data="help_voice")],
        [InlineKeyboardButton(analysis_btn, callback_data="help_analysis")],
        [InlineKeyboardButton(quickstart_btn, callback_data="help_quickstart")],
        [InlineKeyboardButton(cmd_btn, callback_data="commands")],
        [InlineKeyboardButton(back_btn, callback_data="back")]
    ])

    await bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.id,
        text=translated_help,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

    await callback.answer()
    return
    
async def handle_help_category(client, callback):
    user_id = callback.from_user.id
    callback_data = callback.data
    
    help_content = help_text  # Default
    if callback_data == "help_ai":
        help_content = ai_chat_help
    elif callback_data == "help_img":
        help_content = image_gen_help
    elif callback_data == "help_voice":
        help_content = voice_features_help
    elif callback_data == "help_analysis":
        help_content = image_analysis_help
    elif callback_data == "help_quickstart":
        help_content = quick_start_help
    
    # Translate the selected help content
    translated_text = await async_translate_to_lang(help_content, user_id)
    back_btn = await translate_ui_element("🔙 Back to Help Menu", user_id)
    
    # Use "help" as callback_data to return to main help menu
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(back_btn, callback_data="help")]
    ])
    
    await client.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.id,
        text=translated_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    
    await callback.answer()
    return
    
