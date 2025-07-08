import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from pyrogram.types import CallbackQuery
from modules.lang import async_translate_to_lang, translate_ui_element, batch_translate, format_with_mention
from modules.chatlogs import channel_log
from config import DATABASE_URL, ADMINS
from modules.user.premium_management import is_user_premium
from modules.user.ai_model import get_user_ai_models

from pymongo import MongoClient

# Replace with your MongoDB connection string
client = MongoClient(DATABASE_URL)

# Access your database and collection
db = client["aibotdb"]
user_voice_collection = db["user_voice_setting"]

# Access or create the database and collection
user_lang_collection = db['user_lang']
ai_mode_collection = db['ai_mode']
user_image_gen_settings_collection = db['user_image_gen_settings']

modes = {
    "chatbot": "Chatbot",
    "coder": "Coder/Developer",
    "professional": "Professional",
    "teacher": "Teacher",
    "therapist": "Therapist",
    "assistant": "Personal Assistant",
    "gamer": "Gamer",
    "translator": "Translator"
}

languages = {
    "en": "🇬🇧 English",
    "hi": "🇮🇳 Hindi",
    "zh": "🇨🇳 Chinese",
    "ar": "🇸🇦 Arabic",
    "fr": "🇫🇷 French",
    "ru": "🇷🇺 Russian"
}

settings_text_template = """
**Setting Menu for User {mention}**

**User ID**: {user_id}
**Account Status**: {premium_status}
**User Language:** {language}
**User Voice**: {voice_setting}
**User Mode**: {mode}
**AI Text Model**: {ai_text_model}
**AI Image Model**: {ai_image_model}

You can change your settings from below options.

**@AdvChatGptBot**
"""

async def settings_inline(client_obj, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
    current_language = user_lang_doc['language'] if user_lang_doc else "en"
    if not user_lang_doc:
        user_lang_collection.insert_one({"user_id": user_id, "language": current_language})
    
    user_settings = user_voice_collection.find_one({"user_id": user_id})
    voice_setting = user_settings.get("voice", "voice") if user_settings else "voice"
    if not user_settings:
        user_voice_collection.insert_one({"user_id": user_id, "voice": voice_setting})
    
    user_mode_doc = ai_mode_collection.find_one({"user_id": user_id})
    current_mode = user_mode_doc['mode'] if user_mode_doc else "chatbot"
    if not user_mode_doc:
        ai_mode_collection.insert_one({"user_id": user_id, "mode": current_mode})

    # Get premium status
    is_premium, remaining_days, _ = await is_user_premium(user_id)
    if is_premium:
        premium_status_text_key = "✨ Premium User ({days} days left)"
        premium_status_val = await async_translate_to_lang(premium_status_text_key.format(days=remaining_days), current_language)
    else:
        premium_status_text_key = "👤 Standard User"
        premium_status_val = await async_translate_to_lang(premium_status_text_key, current_language)
    
    current_mode_label = await async_translate_to_lang(modes.get(current_mode, current_mode), current_language)
    current_language_label = await async_translate_to_lang(languages.get(current_language, current_language), current_language)
    mention = callback.from_user.mention
    
    # Fetch user AI models
    ai_text_model, ai_image_model = await get_user_ai_models(user_id)

    translated_template = await async_translate_to_lang(settings_text_template, current_language)
    formatted_text = translated_template.format(
        mention=mention,
        user_id=user_id,
        premium_status=premium_status_val,
        language=current_language_label,
        voice_setting=await async_translate_to_lang(voice_setting.capitalize(), current_language),
        mode=current_mode_label,
        ai_text_model=ai_text_model,
        ai_image_model=ai_image_model,
    )

    button_labels = ["🌐 Language", "🎙️ Voice", "🤖 Assistant", "🖼️ Image Count", "🔙 Back"]
    translated_labels = await batch_translate(button_labels, user_id)
    
    # Add the new AI Models button
    ai_models_button_label = await async_translate_to_lang("🧠 AI Models", current_language)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(ai_models_button_label, callback_data="settings_ai_models")],  # New button
        [InlineKeyboardButton(translated_labels[0], callback_data="settings_lans"),
         InlineKeyboardButton(translated_labels[1], callback_data="settings_v")],
        [InlineKeyboardButton(translated_labels[2], callback_data="settings_assistant"),
         InlineKeyboardButton(translated_labels[3], callback_data="settings_image_count")],
        [InlineKeyboardButton(translated_labels[4], callback_data="back")]
    ])

    await callback.message.edit_text(
        text=formatted_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )


async def settings_language_callback(client, callback):
    user_id = callback.from_user.id
    
    # Fetch user voice settings from MongoDB
    user_settings = user_voice_collection.find_one({"user_id": user_id})
    
    if user_settings:
        voice_setting = user_settings.get("voice", "voice")
    else:
        voice_setting = "voice"
        # If user doesn't exist, add them with default setting "voice"
        user_voice_collection.insert_one({"user_id": user_id, "voice": "voice"})

    print(f"Voice setting for {user_id}: {voice_setting}")
    
    # Efficiently translate all text at once
    texts_to_translate = ["Voice", "Text", "Current setting: Answering in", "queries only.", "🔙 Back"]
    translated_texts = await batch_translate(texts_to_translate, user_id)
    
    voice_text = translated_texts[0]
    text_option = translated_texts[1]
    current_setting = translated_texts[2]
    queries_only = translated_texts[3]
    back_btn = translated_texts[4]
    
    # Update the button texts based on the user's current setting
    voice_button_text = f"🎙️ {voice_text} ✅" if voice_setting == "voice" else f"🎙️ {voice_text}"
    text_button_text = f"💬 {text_option} ✅" if voice_setting == "text" else f"💬 {text_option}"

    # Create the message text with translated components
    message_text = f"{current_setting} {voice_text if voice_setting == 'voice' else text_option} {queries_only}"

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(voice_button_text, callback_data="settings_voice"),
                InlineKeyboardButton(text_button_text, callback_data="settings_text")
            ],
            [
                InlineKeyboardButton(back_btn, callback_data="settings_back")
            ]
        ]
    )

    await callback.message.edit(
        text=message_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

async def change_voice_setting(client, callback):
    user_id = callback.from_user.id
    
    # Determine the new voice setting based on the callback data
    new_voice_setting = "voice" if callback.data == "settings_voice" else "text"

    # Update the voice setting in MongoDB
    user_voice_collection.update_one(
        {"user_id": user_id},
        {"$set": {"voice": new_voice_setting}},
        upsert=True
    )

    # Efficiently translate all text at once
    texts_to_translate = ["Voice", "Text", "Current setting: Answering in", "queries only.", "🔙 Back"]
    translated_texts = await batch_translate(texts_to_translate, user_id)
    
    voice_text = translated_texts[0]
    text_option = translated_texts[1]
    current_setting = translated_texts[2]
    queries_only = translated_texts[3]
    back_btn = translated_texts[4]

    # Create the message text with translated components
    message_text = f"{current_setting} {voice_text if new_voice_setting == 'voice' else text_option} {queries_only}"

    # Update the button texts with checkmarks
    voice_button_text = f"🎙️ {voice_text} ✅" if new_voice_setting == "voice" else f"🎙️ {voice_text}"
    text_button_text = f"💬 {text_option} ✅" if new_voice_setting == "text" else f"💬 {text_option}"

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(voice_button_text, callback_data="settings_voice"),
                InlineKeyboardButton(text_button_text, callback_data="settings_text")
            ],
            [
                InlineKeyboardButton(back_btn, callback_data="settings_back")
            ]
        ]
    )

    # Edit the message to reflect the new settings
    await callback.message.edit(
        text=message_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

# Function to handle settings inline
async def settings_voice_inlines(client, callback):
    settings_text = """
**Setting Menu for User {mention}**

**User ID**: {user_id}
**User Language:** {language}
**User Voice**: {voice_setting}
**User Mode**: {mode}

You can change your settings from below options.

**@AdvChatGptBot**
"""

    user_id = callback.from_user.id
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
        # If user doesn't exist, add them with default setting "voice"
        user_voice_collection.insert_one({"user_id": user_id, "voice": "voice"})
    
    user_mode_doc = ai_mode_collection.find_one({"user_id": user_id})

    if user_mode_doc:
        current_mode = user_mode_doc['mode']
    else:
        current_mode = "chatbot"
        ai_mode_collection.insert_one({"user_id": user_id, "mode": current_mode})
    
    current_mode_label = modes[current_mode]
    current_language_label = languages[current_language]

    # Get user mention
    mention = callback.from_user.mention
    
    # Safely translate the template with mention preservation
    translated_text = await format_with_mention(settings_text, mention, user_id, current_language)
    
    # Format with the remaining variables
    formatted_text = translated_text.format(
        mention=mention,
        user_id=callback.from_user.id,
        language=current_language_label,
        voice_setting=voice_setting,
        mode=current_mode_label,
    )
    
    # Efficiently translate all button labels at once
    button_labels = ["🌐 Language", "🎙️ Voice", "🤖 Assistant", "🖼️ Image Count", "🔙 Back"]
    translated_labels = await batch_translate(button_labels, user_id)

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(translated_labels[0], callback_data="settings_lans"),
                InlineKeyboardButton(translated_labels[1], callback_data="settings_v")
            ],
            [
                InlineKeyboardButton(translated_labels[2], callback_data="settings_assistant"),
                InlineKeyboardButton(translated_labels[3], callback_data="settings_image_count")
            ],
            [
                InlineKeyboardButton(translated_labels[4], callback_data="back")
            ]
        ]
    )

    await callback.message.edit(
        text=formatted_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

async def settings_image_count_callback(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    current_lang = user_lang_collection.find_one({"user_id": user_id}).get("language", "en")

    user_gen_settings = user_image_gen_settings_collection.find_one({"user_id": user_id})
    current_count = user_gen_settings.get("generation_count", 1) if user_gen_settings else 1

    is_premium_user, _, _ = await is_user_premium(user_id)
    is_admin_user = user_id in ADMINS

    title_text = await async_translate_to_lang("🖼️ Image Generation Count", current_lang)
    desc_text_template = await async_translate_to_lang("Select how many images you want to generate at once. Current: {count}", current_lang)
    desc_text = desc_text_template.format(count=current_count)
    premium_needed_alert = await async_translate_to_lang("Standard users can only generate 1 image. Upgrade to Premium for more!", current_lang)
    back_button_text = await async_translate_to_lang("🔙 Back", current_lang)
    time_warning_text = await async_translate_to_lang("⚠️ Generating 3 or 4 images will take significantly longer.", current_lang)

    buttons = []
    for i in range(1, 5): # 1, 2, 3, 4
        text = f"{i} ✅" if i == current_count else str(i)
        buttons.append(InlineKeyboardButton(text, callback_data=f"img_count_{i}"))
    
    keyboard_layout = [buttons, [InlineKeyboardButton(back_button_text, callback_data="settings")]]
    keyboard = InlineKeyboardMarkup(keyboard_layout)

    final_text = f"<b>{title_text}</b>\n\n{desc_text}"
    if not is_premium_user and not is_admin_user and current_count > 1:
        # This case should ideally not be reached if logic is correct, but as a safeguard:
        final_text += f"\n\n<small><i>{premium_needed_alert}</i></small>"
    
    # Add time warning if user is premium/admin and considering 3 or 4 images
    if is_premium_user or is_admin_user:
        final_text += f"\n\n<small><i>{time_warning_text}</i></small>"

    await callback.message.edit_text(
        text=final_text,
        reply_markup=keyboard,
        parse_mode=pyrogram.enums.ParseMode.HTML # For bold and small tags
    )
    await callback.answer()

async def change_image_count_callback(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    current_lang = user_lang_collection.find_one({"user_id": user_id}).get("language", "en")
    
    try:
        chosen_count = int(callback.data.split("_")[-1])
    except (IndexError, ValueError):
        await callback.answer("Invalid selection.", show_alert=True)
        return

    # Get current image count setting
    user_gen_settings = user_image_gen_settings_collection.find_one({"user_id": user_id})
    current_count = user_gen_settings.get("generation_count", 1) if user_gen_settings else 1

    # Check if user clicked on already selected number
    if chosen_count == current_count:
        already_selected_alert = await async_translate_to_lang("This number is already selected", current_lang)
        await callback.answer(already_selected_alert, show_alert=True)
        return

    is_premium_user, _, _ = await is_user_premium(user_id)
    is_admin_user = user_id in ADMINS

    if not is_premium_user and not is_admin_user and chosen_count > 1:
        premium_needed_alert = await async_translate_to_lang("Standard users can only generate 1 image. Upgrade to Premium for more!", current_lang)
        await callback.answer(premium_needed_alert, show_alert=True)
        # Don't change setting, just re-display the panel (or do nothing to keep them on the same panel)
        # Calling settings_image_count_callback again will refresh it.
        await settings_image_count_callback(client, callback) 
        return

    user_image_gen_settings_collection.update_one(
        {"user_id": user_id},
        {"$set": {"generation_count": chosen_count}},
        upsert=True
    )
    
    update_success_alert_template = await async_translate_to_lang("Image count set to {count}!", current_lang)
    await callback.answer(update_success_alert_template.format(count=chosen_count), show_alert=False)
    # Refresh the panel to show the new selection
    await settings_image_count_callback(client, callback)

async def send_settings_menu_as_message(client_obj, message):
    user_id = message.from_user.id
    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
    current_language = user_lang_doc['language'] if user_lang_doc else "en"
    if not user_lang_doc:
        user_lang_collection.insert_one({"user_id": user_id, "language": current_language})
    user_settings = user_voice_collection.find_one({"user_id": user_id})
    voice_setting = user_settings.get("voice", "voice") if user_settings else "voice"
    if not user_settings:
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
    mention = message.from_user.mention
    ai_text_model, ai_image_model = await get_user_ai_models(user_id)
    translated_template = await async_translate_to_lang(settings_text_template, current_language)
    formatted_text = translated_template.format(
        mention=mention,
        user_id=user_id,
        premium_status=premium_status_val,
        language=current_language_label,
        voice_setting=await async_translate_to_lang(voice_setting.capitalize(), current_language),
        mode=current_mode_label,
        ai_text_model=ai_text_model,
        ai_image_model=ai_image_model,
    )
    button_labels = ["🌐 Language", "🎙️ Voice", "🤖 Assistant", "🖼️ Image Count", "🔙 Back"]
    translated_labels = await batch_translate(button_labels, user_id)
    ai_models_button_label = await async_translate_to_lang("🧠 AI Models", current_language)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(ai_models_button_label, callback_data="settings_ai_models")],
        [InlineKeyboardButton(translated_labels[0], callback_data="settings_lans"),
         InlineKeyboardButton(translated_labels[1], callback_data="settings_v")],
        [InlineKeyboardButton(translated_labels[2], callback_data="settings_assistant"),
         InlineKeyboardButton(translated_labels[3], callback_data="settings_image_count")],
    ])
    await message.reply(
        text=formatted_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )



