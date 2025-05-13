from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from modules.lang import async_translate_to_lang

from config import ADMINS as admin_ids

support_text="""
About the bot:

**Suports Image to Text, Text to Image, Voice to Text, Text to Voice, Chatbot, and many more features.**

**Version:** V-2.O
**ChatGpt Model:** [Gpt-4o and Gpt-4o-mini (OpenAi)](https://chat.openai.com/)
**Image Generation Model:** [DALL-E-3 Model](https://openai.com/dall-e/)
**Voice Generation Model:** [Google Speech to Text](https://cloud.google.com/speech-to-text)
**Voice Recognition Model:** [Google Text to Speech](https://cloud.google.com/text-to-speech)
**Image to Text Model:** [OCR](https://ocr.space/ocrapi)
**Databse:** [MongoDB](https://www.mongodb.com)
**Hosting:** [Railway](https://railway.app)
**Source Code:** [GitHub](https://github.com/TechyCSR/AdvAITelegramBot)

**Support Options:**




"""



# print(admin_ids)
# Function to handle settings support callback
async def settings_support_callback(client, CallbackQuery):
    user_id = CallbackQuery.from_user.id
    
    # Translate support text
    translated_support_text = await async_translate_to_lang(support_text, user_id)
    
    # Translate button labels
    admins_btn = await async_translate_to_lang("👥 Admins", user_id)
    developers_btn = await async_translate_to_lang("💻 Developers", user_id)
    community_btn = await async_translate_to_lang("🌐 Community", user_id)
    source_code_btn = await async_translate_to_lang("⌨ Source Code", user_id)
    back_btn = await async_translate_to_lang("🔙 Back", user_id)

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(admins_btn, callback_data="support_admins"),
                InlineKeyboardButton(developers_btn, callback_data="support_developers")
            ],
            [
                InlineKeyboardButton(community_btn, url="https://t.me/AdvChatGpt"),
                InlineKeyboardButton(source_code_btn, url="https://github.com/TechyCSR/AdvAITelegramBot")
            ],
            [
                InlineKeyboardButton(back_btn, callback_data="back")
            ]
        ]
    )

    await CallbackQuery.message.edit(
        text=translated_support_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )






# Feature states (defaults)
feature_states = {
    "image_generation": "off",
    "voice_feature": "off",
    "premium_service": "off"
}

# Function to handle support_admins callback
async def support_admins_callback(client, callback: CallbackQuery):
    user_id = callback.from_user.id

    if user_id not in admin_ids:
        # Translate the alert message
        alert_message = await async_translate_to_lang("This section is for admins only.", user_id)
        await callback.answer(alert_message, show_alert=True)
        return

    # Translate admin panel title and labels
    admin_panel_title = await async_translate_to_lang("🔧 **Admin Panel** 🔧\n\nManage the features below:", user_id)
    image_generation_text = await async_translate_to_lang("🖼️ Image Generation", user_id)
    voice_feature_text = await async_translate_to_lang("🎙️ Voice Feature", user_id)
    premium_service_text = await async_translate_to_lang("💎 Premium Service", user_id)
    on_text = await async_translate_to_lang("🔊 On", user_id)
    off_text = await async_translate_to_lang("🔇 Off", user_id)
    back_btn = await async_translate_to_lang("🔙 Back", user_id)

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(f"{image_generation_text} ({feature_states['image_generation']})", callback_data="toggle_image_generation")
            ],
            [
                InlineKeyboardButton(on_text, callback_data="set_image_generation_on"),
                InlineKeyboardButton(off_text, callback_data="set_image_generation_off")
            ],
            [
                InlineKeyboardButton(f"{voice_feature_text} ({feature_states['voice_feature']})", callback_data="toggle_voice_feature")
            ],
            [
                InlineKeyboardButton(on_text, callback_data="set_voice_feature_on"),
                InlineKeyboardButton(off_text, callback_data="set_voice_feature_off")
            ],
            [
                InlineKeyboardButton(f"{premium_service_text} ({feature_states['premium_service']})", callback_data="toggle_premium_service")
            ],
            [
                InlineKeyboardButton(on_text, callback_data="set_premium_service_on"),
                InlineKeyboardButton(off_text, callback_data="set_premium_service_off")
            ],
            [
                InlineKeyboardButton(back_btn, callback_data="support")
            ]
        ]
    )

    await callback.message.edit(
        text=admin_panel_title,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

# # Function to handle feature state toggling
# async def toggle_feature(client, callback: CallbackQuery, feature: str, state: str):
#     feature_states[feature] = state

#     # Update the admin panel
#     await support_admins_callback(client, callback)

# # Callback query handlers for toggling features
# async def toggle_image_generation(client, callback: CallbackQuery):
#     await toggle_feature(client, callback, "image_generation", "on" if feature_states["image_generation"] == "off" else "off")

# async def toggle_voice_feature(client, callback: CallbackQuery):
#     await toggle_feature(client, callback, "voice_feature", "on" if feature_states["voice_feature"] == "off" else "off")

# async def toggle_premium_service(client, callback: CallbackQuery):
#     await toggle_feature(client, callback, "premium_service", "on" if feature_states["premium_service"] == "off" else "off")

# # Callback query handlers for setting features directly
# async def set_image_generation(client, callback: CallbackQuery):
#     state = callback.data.split('_')[-1]
#     await toggle_feature(client, callback, "image_generation", state)

# async def set_voice_feature(client, callback: CallbackQuery):
#     state = callback.data.split('_')[-1]
#     await toggle_feature(client, callback, "voice_feature", state)

# async def set_premium_service(client, callback: CallbackQuery):
#     state = callback.data.split('_')[-1]
#     await toggle_feature(client, callback, "premium_service", state)

# async def handle_support(client, callback: CallbackQuery):
#     await settings_support_callback(client, callback)

