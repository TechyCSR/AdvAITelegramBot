import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from pyrogram.types import CallbackQuery
from modules.lang import async_translate_to_lang, batch_translate, translate_ui_element
from modules.chatlogs import channel_log
from config import ADMINS


command__text = """
**🤖 Bot Commands 🤖**

Select a feature below to see detailed commands and examples.

**@AdvChatGptBot**
"""

ai_commands_text = """
**🧠 AI Chat Commands**

**In Private Chats:**
- Simply type your message and I'll respond
- Send a voice message to get voice-to-text conversion
- Use `/new` or `/newchat` to start a fresh conversation

**In Group Chats:**
- Use `/ai [question]` to ask me directly
  Example: `/ai What's the weather like in Paris?`
- Reply to my messages to continue the conversation
- Use `/ask [question]` or `/say [question]` as alternatives

**Pro Tips:**
- I remember conversation context in private chats
- For coding questions, include language for better formatting
- Use `/new` to reset our conversation history

**@AdvChatGptBot**
"""

image_commands_text = """
**🖼️ Image Generation Commands**

**In Private Chats:**
- Use `/generate [prompt]` or `/img [prompt]` to create images
  Example: `/img a serene mountain landscape at sunset`
- Choose from multiple artistic styles after entering your prompt
- Use the regenerate button to try again with the same prompt

**In Group Chats:**
- Use the same commands as in private chats
- Everyone can view and react to generated images
- Only the person who requested can regenerate images

**Image Analysis:**
- Send any image to extract and analyze its text
- Add "ai" in caption with an image to analyze it in groups

**Pro Tips:**
- Be specific with details for better results
- Try different styles for varied outputs
- Include artistic references for specific aesthetics

**@AdvChatGptBot**
"""

main_commands_text = """
**📋 Main Commands**

**/start** - Start the bot and see the welcome message
**/help** - Show help information
**/settings** - Configure bot settings
**/rate** - Rate your experience with the bot

**@AdvChatGptBot**
"""

admin_commands_text = """
**⚙️ Admin Commands**

These commands are restricted to bot administrators only.

**/restart** - Restart the bot (requires confirmation)
**/stats** - View bot statistics and usage data 
**/logs** - Get the most recent log entries
**/announce** - Send a message to all users
**/gleave** - Leave a group chat
**/invite** - Add the bot to a group
**/uinfo** - Get information about users

**Note:** These commands are only available to authorized administrators listed in the configuration.

**@AdvChatGptBot**
"""


async def command_inline(client, callback):
    user_id = callback.from_user.id
    
    # Translate the command text and buttons
    texts_to_translate = [command__text, "🧠 AI Response", "🖼️ Image Generation", "📋 Main Commands", "🔙 Back"]
    translated_texts = await batch_translate(texts_to_translate, user_id)
    
    # Extract translated results
    translated_command = translated_texts[0]
    ai_btn = translated_texts[1]
    img_btn = translated_texts[2]
    main_btn = translated_texts[3]
    back_btn = translated_texts[4]
    
    # Create base keyboard
    keyboard_buttons = [
        [InlineKeyboardButton(ai_btn, callback_data="cmd_ai")],
        [InlineKeyboardButton(img_btn, callback_data="cmd_img")],
        [InlineKeyboardButton(main_btn, callback_data="cmd_main")]
    ]
    
    # Add admin button if user is an admin
    if user_id in ADMINS:
        admin_btn = "⚙️ Admin Commands"
        keyboard_buttons.append([InlineKeyboardButton(admin_btn, callback_data="cmd_admin")])
    
    # Add back button
    keyboard_buttons.append([InlineKeyboardButton(back_btn, callback_data="help_help")])
    
    keyboard = InlineKeyboardMarkup(keyboard_buttons)

    await client.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.id,
        text=translated_command,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

    await callback.answer()
    return

async def handle_command_callbacks(client, callback):
    user_id = callback.from_user.id
    callback_data = callback.data
    
    if callback_data == "cmd_ai":
        # Show AI commands
        translated_text = await async_translate_to_lang(ai_commands_text, user_id)
        back_btn = await translate_ui_element("🔙 Back to Commands", user_id)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(back_btn, callback_data="commands")]
        ])
        
        await client.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            text=translated_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
    elif callback_data == "cmd_img":
        # Show Image commands
        translated_text = await async_translate_to_lang(image_commands_text, user_id)
        back_btn = await translate_ui_element("🔙 Back to Commands", user_id)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(back_btn, callback_data="commands")]
        ])
        
        await client.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            text=translated_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
    elif callback_data == "cmd_main":
        # Show main commands
        translated_text = await async_translate_to_lang(main_commands_text, user_id)
        back_btn = await translate_ui_element("🔙 Back to Commands", user_id)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(back_btn, callback_data="commands")]
        ])
        
        await client.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            text=translated_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    
    elif callback_data == "cmd_admin":
        # Show admin commands (only for admins)
        if user_id in ADMINS:
            back_btn = await translate_ui_element("🔙 Back to Commands", user_id)
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(back_btn, callback_data="commands")]
            ])
            
            await client.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=callback.message.id,
                text=admin_commands_text,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        else:
            # User is not an admin, show unauthorized message
            await callback.answer("You don't have permission to view admin commands", show_alert=True)
    
    await callback.answer()
    return

async def command_inline_start(client, callback):
    user_id = callback.from_user.id
    texts_to_translate = [command__text, "🧠 AI Response", "🖼️ Image Generation", "📋 Main Commands", "🔙 Back"]
    translated_texts = await batch_translate(texts_to_translate, user_id)
    translated_command = translated_texts[0]
    ai_btn = translated_texts[1]
    img_btn = translated_texts[2]
    main_btn = translated_texts[3]
    back_btn = translated_texts[4]
    keyboard_buttons = [
        [InlineKeyboardButton(ai_btn, callback_data="cmd_ai_start")],
        [InlineKeyboardButton(img_btn, callback_data="cmd_img_start")],
        [InlineKeyboardButton(main_btn, callback_data="cmd_main_start")],
    ]
    if user_id in ADMINS:
        admin_btn = "⚙️ Admin Commands"
        keyboard_buttons.append([InlineKeyboardButton(admin_btn, callback_data="cmd_admin_start")])
    keyboard_buttons.append([InlineKeyboardButton(back_btn, callback_data="back")])
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    await client.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.id,
        text=translated_command,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    await callback.answer()
    return

async def command_inline_help(client, callback):
    user_id = callback.from_user.id
    texts_to_translate = [command__text, "🧠 AI Response", "🖼️ Image Generation", "📋 Main Commands", "🔙 Back"]
    translated_texts = await batch_translate(texts_to_translate, user_id)
    translated_command = translated_texts[0]
    ai_btn = translated_texts[1]
    img_btn = translated_texts[2]
    main_btn = translated_texts[3]
    back_btn = translated_texts[4]
    keyboard_buttons = [
        [InlineKeyboardButton(ai_btn, callback_data="cmd_ai_help")],
        [InlineKeyboardButton(img_btn, callback_data="cmd_img_help")],
        [InlineKeyboardButton(main_btn, callback_data="cmd_main_help")],
    ]
    if user_id in ADMINS:
        admin_btn = "⚙️ Admin Commands"
        keyboard_buttons.append([InlineKeyboardButton(admin_btn, callback_data="cmd_admin_help")])
    keyboard_buttons.append([InlineKeyboardButton(back_btn, callback_data="help_help")])
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    await client.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.id,
        text=translated_command,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    await callback.answer()
    return

async def handle_command_callbacks_start(client, callback):
    user_id = callback.from_user.id
    callback_data = callback.data
    if callback_data == "cmd_ai_start":
        translated_text = await async_translate_to_lang(ai_commands_text, user_id)
        back_btn = await translate_ui_element("🔙 Back to Commands", user_id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(back_btn, callback_data="commands_start")]
        ])
        await client.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            text=translated_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    elif callback_data == "cmd_img_start":
        translated_text = await async_translate_to_lang(image_commands_text, user_id)
        back_btn = await translate_ui_element("🔙 Back to Commands", user_id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(back_btn, callback_data="commands_start")]
        ])
        await client.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            text=translated_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    elif callback_data == "cmd_main_start":
        translated_text = await async_translate_to_lang(main_commands_text, user_id)
        back_btn = await translate_ui_element("🔙 Back to Commands", user_id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(back_btn, callback_data="commands_start")]
        ])
        await client.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            text=translated_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    elif callback_data == "cmd_admin_start":
        if user_id in ADMINS:
            back_btn = await translate_ui_element("🔙 Back to Commands", user_id)
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(back_btn, callback_data="commands_start")]
            ])
            await client.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=callback.message.id,
                text=admin_commands_text,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        else:
            await callback.answer("You don't have permission to view admin commands", show_alert=True)
    await callback.answer()
    return

async def handle_command_callbacks_help(client, callback):
    user_id = callback.from_user.id
    callback_data = callback.data
    if callback_data == "cmd_ai_help":
        translated_text = await async_translate_to_lang(ai_commands_text, user_id)
        back_btn = await translate_ui_element("🔙 Back to Commands", user_id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(back_btn, callback_data="commands_help")]
        ])
        await client.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            text=translated_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    elif callback_data == "cmd_img_help":
        translated_text = await async_translate_to_lang(image_commands_text, user_id)
        back_btn = await translate_ui_element("🔙 Back to Commands", user_id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(back_btn, callback_data="commands_help")]
        ])
        await client.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            text=translated_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    elif callback_data == "cmd_main_help":
        translated_text = await async_translate_to_lang(main_commands_text, user_id)
        back_btn = await translate_ui_element("🔙 Back to Commands", user_id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(back_btn, callback_data="commands_help")]
        ])
        await client.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            text=translated_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    elif callback_data == "cmd_admin_help":
        if user_id in ADMINS:
            back_btn = await translate_ui_element("🔙 Back to Commands", user_id)
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(back_btn, callback_data="commands_help")]
            ])
            await client.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=callback.message.id,
                text=admin_commands_text,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        else:
            await callback.answer("You don't have permission to view admin commands", show_alert=True)
    await callback.answer()
    return


