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
from modules.user.premium_management import is_user_premium
from modules.user.ai_model import get_user_ai_models, TEXT_MODELS, IMAGE_MODELS

settings_text = """
**Setting Menu for User {mention}**

**User ID**: {user_id}
**Account Status**: {premium_status}
**User Language:** {language}
**User Voice**: {voice_setting}
**User Mode**: {mode}
**AI Text Model**: {ai_text_model}
**AI Image Model**: {ai_image_model}

You can manage your settings from the start panel below.

**@AdvChatGptBot**
"""

async def user_settings_panel_command(client, message, edit=False, callback_query=None):
    actual_message = callback_query.message if callback_query else message
    user = callback_query.from_user if callback_query else message.from_user
    user_id = user.id

    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
    current_language = user_lang_doc['language'] if user_lang_doc else "en"
    if not user_lang_doc:
        user_lang_collection.insert_one({"user_id": user_id, "language": current_language})

    user_settings_doc = user_voice_collection.find_one({"user_id": user_id})
    voice_setting = user_settings_doc.get("voice", "voice") if user_settings_doc else "voice"
    if not user_settings_doc:
        user_voice_collection.insert_one({"user_id": user_id, "voice": voice_setting})

    user_mode_doc = ai_mode_collection.find_one({"user_id": user_id})
    current_mode = user_mode_doc['mode'] if user_mode_doc else "chatbot"
    if not user_mode_doc:
        ai_mode_collection.insert_one({"user_id": user_id, "mode": current_mode})

    is_premium, remaining_days, _ = await is_user_premium(user_id)
    if is_premium:
        premium_status_text_key = "✨ Premium User ({days} days left)"
        premium_status_val = await async_translate_to_lang(premium_status_text_key.format(days=remaining_days), current_language)
    else:
        premium_status_text_key = "👤 Standard User"
        premium_status_val = await async_translate_to_lang(premium_status_text_key, current_language)

    current_mode_label = await async_translate_to_lang(modes.get(current_mode, current_mode), current_language)
    current_language_label = await async_translate_to_lang(languages.get(current_language, current_language), current_language)
    
    mention = user.mention if hasattr(user, 'mention') else f"<a href='tg://user?id={user_id}'>User {user_id}</a>"
    
    # Get user AI models (already restricted for standard users)
    ai_text_model_key, ai_image_model_key = await get_user_ai_models(user_id)
    # Translate model display names
    ai_text_model_name = await async_translate_to_lang(TEXT_MODELS.get(ai_text_model_key, ai_text_model_key), current_language)
    ai_image_model_name = await async_translate_to_lang(IMAGE_MODELS.get(ai_image_model_key, ai_image_model_key), current_language)

    translated_settings_template = await async_translate_to_lang(settings_text, current_language)

    formatted_text = translated_settings_template.format(
        mention=mention,
        user_id=user_id,
        premium_status=premium_status_val,
        language=current_language_label,
        voice_setting=await async_translate_to_lang(voice_setting.capitalize(), current_language),
        mode=current_mode_label,
        ai_text_model=ai_text_model_name,
        ai_image_model=ai_image_model_name,
    )

    bot_username = (await client.get_me()).username
    button_labels = ["⚙️ Open Start Panel", "🔄 Reset Conversation", "📊 System Status", "❌ Close"]
    translated_labels = await batch_translate(button_labels, user_id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(translated_labels[0], url=f"https://t.me/{bot_username}?start=settings")],
        [InlineKeyboardButton(translated_labels[1], callback_data="user_settings_reset")],
        [InlineKeyboardButton(translated_labels[2], callback_data="user_settings_status")],
        [InlineKeyboardButton(translated_labels[3], callback_data="user_settings_close")]
    ])

    if edit or callback_query:
        await actual_message.edit_text(
            formatted_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    else:
        await message.reply(
            formatted_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

async def handle_user_settings_callback(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id
    current_language = user_lang_collection.find_one({"user_id": user_id}).get('language', 'en')

    if data == "user_settings_reset":
        history_collection = get_history_collection()
        history_collection.delete_one({"user_id": user_id})
        history_collection.insert_one({"user_id": user_id, "history": DEFAULT_SYSTEM_MESSAGE})
        reset_msg = await async_translate_to_lang("🔄 Conversation reset! Your chat history has been cleared.", current_language)
        await callback_query.answer(reset_msg, show_alert=True)
        return
    elif data == "user_settings_status":
        stats = await get_bot_statistics()
        sysinfo_title = await async_translate_to_lang("⚙️ System Information", current_language)
        uptime_text = await async_translate_to_lang("Uptime", current_language)
        cpu_text = await async_translate_to_lang("CPU", current_language)
        mem_text = await async_translate_to_lang("Memory", current_language)
        feature_status_text = await async_translate_to_lang("Current Feature Status", current_language)
        enabled_text = await async_translate_to_lang("✅ Enabled", current_language)
        disabled_text = await async_translate_to_lang("❌ Disabled", current_language)
        back_text = await async_translate_to_lang("🔙 Back", current_language)
        ai_text = await async_translate_to_lang("AI Response", current_language)
        img_text = await async_translate_to_lang("Image Generation", current_language)
        voice_text = await async_translate_to_lang("Voice Features", current_language)
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
                current_language
            )
            status_message += maintenance_info
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(back_text, callback_data="user_settings_back")]
        ])
        await callback_query.message.edit_text(status_message, reply_markup=keyboard)
        await callback_query.answer()
        return
    elif data == "user_settings_back":
        await user_settings_panel_command(client, None, edit=True, callback_query=callback_query)
        await callback_query.answer()
        return
    elif data == "user_settings_close":
        await callback_query.message.delete()
        await callback_query.answer()
        return
    
    default_answer = await async_translate_to_lang("Feature coming soon!", current_language)
    await callback_query.answer(default_answer, show_alert=True) 