import asyncio
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from modules.user.global_setting import user_lang_collection, user_voice_collection, ai_mode_collection, languages, modes
from modules.models.ai_res import get_history_collection, DEFAULT_SYSTEM_MESSAGE
from modules.lang import batch_translate, format_with_mention, async_translate_to_lang
from modules.user.settings import settings_language_callback, change_voice_setting, settings_inline
from modules.user.assistant import settings_assistant_callback
from modules.user.user_support import settings_support_callback
from modules.maintenance import get_feature_states
from modules.admin.statistics import get_bot_statistics

settings_text = """
**Setting Menu for User {mention}**

**User ID**: {user_id}
**User Language:** {language}
**User Voice**: {voice_setting}
**User Mode**: {mode}

You can manage your settings from the start panel below.

**@AdvChatGptBot**
"""

async def user_settings_panel_command(client, message, edit=False):
    user_id = message.from_user.id
    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
    if user_lang_doc:
        current_language = user_lang_doc['language']
    else:
        current_language = "en"
        user_lang_collection.insert_one({"user_id": user_id, "language": current_language})
    user_settings = user_voice_collection.find_one({"user_id": user_id})
    if user_settings:
        voice_setting = user_settings.get("voice", "voice")
    else:
        voice_setting = "voice"
        user_voice_collection.insert_one({"user_id": user_id, "voice": "voice"})
    user_mode_doc = ai_mode_collection.find_one({"user_id": user_id})
    if user_mode_doc:
        current_mode = user_mode_doc['mode']
    else:
        current_mode = "chatbot"
        ai_mode_collection.insert_one({"user_id": user_id, "mode": current_mode})
    current_mode_label = modes[current_mode]
    current_language_label = languages[current_language]
    mention = message.from_user.mention if hasattr(message.from_user, 'mention') else f"<a href='tg://user?id={user_id}'>User</a>"
    formatted_text = await format_with_mention(settings_text, mention, user_id, current_language)
    formatted_text = formatted_text.format(
        mention=mention,
        user_id=user_id,
        language=current_language_label,
        voice_setting=voice_setting,
        mode=current_mode_label,
    )
    bot_username = (await client.get_me()).username
    button_labels = ["⚙️ Open Start Panel", "🔄 Reset Conversation", "📊 System Status", "❌ Close"]
    translated_labels = await batch_translate(button_labels, user_id)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(translated_labels[0], url=f"https://t.me/{bot_username}?start=settings")
        ],
        [
            InlineKeyboardButton(translated_labels[1], callback_data="user_settings_reset")
        ],
        [
            InlineKeyboardButton(translated_labels[2], callback_data="user_settings_status")
        ],
        [
            InlineKeyboardButton(translated_labels[3], callback_data="user_settings_close")
        ]
    ])
    if edit:
        await message.edit_text(
            formatted_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    else:
        temp = await message.reply_text("**Loading your settings...**")
        await message.reply(
            formatted_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        await temp.delete()

async def handle_user_settings_callback(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id
    if data == "user_settings_reset":
        # Reset conversation logic (like /new), only show alert
        history_collection = get_history_collection()
        history_collection.delete_one({"user_id": user_id})
        history_collection.insert_one({
            "user_id": user_id,
            "history": DEFAULT_SYSTEM_MESSAGE
        })
        await callback_query.answer("🔄 Conversation reset! Your chat history has been cleared.", show_alert=True)
        return
    elif data == "user_settings_status":
        # Show a modern system status page using full stats and translations
        user_id = callback_query.from_user.id
        stats = await get_bot_statistics()
        # Translate headers
        sysinfo_title = await async_translate_to_lang("⚙️ System Information", user_id)
        uptime_text = await async_translate_to_lang("Uptime", user_id)
        cpu_text = await async_translate_to_lang("CPU", user_id)
        mem_text = await async_translate_to_lang("Memory", user_id)
        feature_status_text = await async_translate_to_lang("Current Feature Status", user_id)
        enabled_text = await async_translate_to_lang("✅ Enabled", user_id)
        disabled_text = await async_translate_to_lang("❌ Disabled", user_id)
        back_text = await async_translate_to_lang("🔙 Back", user_id)
        ai_text = await async_translate_to_lang("AI Response", user_id)
        img_text = await async_translate_to_lang("Image Generation", user_id)
        voice_text = await async_translate_to_lang("Voice Features", user_id)
        # Build status message
        status_message = f"<b>{sysinfo_title}</b>\n\n"
        status_message += f"• {uptime_text}: <b>{stats.get('uptime','-')}</b>\n"
        status_message += f"• {cpu_text}: <b>{stats.get('cpu_usage','-')}%</b>\n"
        status_message += f"• {mem_text}: <b>{stats.get('memory_usage','-')}%</b>\n\n"
        status_message += f"<b>{feature_status_text}:</b>\n"
        status_message += f"• {ai_text}: {enabled_text if stats.get('ai_response_enabled', True) else disabled_text}\n"
        status_message += f"• {img_text}: {enabled_text if stats.get('image_generation_enabled', True) else disabled_text}\n"
        status_message += f"• {voice_text}: {enabled_text if stats.get('voice_features_enabled', True) else disabled_text}\n"
        if stats.get('maintenance_mode', False):
            maintenance_info = await async_translate_to_lang(
                "\n⚠️ <b>The bot is currently in maintenance mode.</b>\nSome features may be unavailable.",
                user_id
            )
            status_message += maintenance_info
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(back_text, callback_data="user_settings_back")]
        ])
        await callback_query.message.edit_text(
            status_message,
            reply_markup=keyboard,
        )
        await callback_query.answer()
        return
    elif data == "user_settings_back":
        await user_settings_panel_command(client, callback_query.message, edit=True)
        await callback_query.answer()
        return
    elif data == "user_settings_close":
        await callback_query.message.delete()
        return
    await callback_query.answer("Feature coming soon!", show_alert=True) 