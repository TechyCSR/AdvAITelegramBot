from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from modules.lang import async_translate_to_lang
from modules.maintenance import maintenance_settings, is_admin_user

from config import ADMINS as admin_ids, OWNER_ID

support_text="""
🤖 **Advanced AI Bot Information**

This versatile AI assistant supports a wide range of capabilities:

• 🖼️ Image Generation 
• 🎙️ Voice Interactions
• 📝 Image-to-Text Analysis
• 💬 Advanced Conversational AI
• 🌐 Multi-language Support

**Developed by:** [Chandan Singh](https://techycsr.dev)
**Technology:** Gpt-4, Qwen-3, DeepSeek-R1, Dall-E3, Flux, Flux-Pro
**Version:** 2.1

**Need assistance?** Choose an option below.
"""



# Function to handle settings support callback
async def settings_support_callback(client, callback_query):
    user_id = callback_query.from_user.id
    
    # Translate support text
    translated_support_text = await async_translate_to_lang(support_text, user_id)
    
    # Translate button labels
    admins_btn = await async_translate_to_lang("👥 Contact Admin", user_id)
    developers_btn = await async_translate_to_lang("💻 Developer Info", user_id)
    community_btn = await async_translate_to_lang("🌐 Community", user_id)
    source_code_btn = await async_translate_to_lang("⌨️ Source Code", user_id)
    system_status_btn = await async_translate_to_lang("📊 System Status", user_id)
    back_btn = await async_translate_to_lang("🔙 Back", user_id)

    # Determine which button to show based on admin status
    is_admin = await is_admin_user(user_id)
    admin_button_text = await async_translate_to_lang("⚙️ Admin Panel", user_id) if is_admin else admins_btn
    admin_button_callback = "admin_panel" if is_admin else "support_admins"
    
    # Add a subtle "Admin Mode" indicator for admins
    admin_indicator = "\n\n🔑 **Admin Access Granted**" if is_admin else ""

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(admin_button_text, callback_data=admin_button_callback),
                InlineKeyboardButton(developers_btn, callback_data="support_developers")
            ],
            [
                InlineKeyboardButton(community_btn, url="https://t.me/AdvChatGpt"),
                InlineKeyboardButton(source_code_btn, url="https://github.com/TechyCSR/AdvAITelegramBot")
            ],
            [
                InlineKeyboardButton(system_status_btn, callback_data="settings_others")
            ],
            [
                InlineKeyboardButton(back_btn, callback_data="back")
            ]
        ]
    )

    await callback_query.message.edit(
        text=translated_support_text + admin_indicator,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

# Function to handle support_admins callback
async def support_admins_callback(client, callback: CallbackQuery):
    user_id = callback.from_user.id

    # Get admin contact information
    admin_contact_info = """
👤 **Developer & Admin Contact**

**Chandan Singh** (@techycsr)
Tech Enthusiast & Student Developer

• **Portfolio:** [techycsr.dev](https://techycsr.dev)
• **GitHub:** [TechyCSR](https://github.com/TechyCSR)
• **Email:** csr.info.in@gmail.com

**About Me:**
I'm a tech enthusiast with a strong passion for Python, AI/ML, and open-source development. I specialize in building Telegram bots using Pyrogram and MongoDB, developing AI-powered applications, and managing web development projects.

**Support Channels:**
• Community: @AdvChatGpt
• Issues: [GitHub Repository](https://github.com/TechyCSR/AdvAITelegramBot/issues)

Feel free to reach out for assistance, feature requests, or to report issues.
    """
    
    # Translate the admin info and button
    translated_admin_info = await async_translate_to_lang(admin_contact_info, user_id)
    back_btn = await async_translate_to_lang("🔙 Back", user_id)
    contact_btn = await async_translate_to_lang("💬 Message Developer", user_id)
    website_btn = await async_translate_to_lang("🌐 Visit Website", user_id)
    
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(contact_btn, url="https://t.me/techycsr"),
                InlineKeyboardButton(website_btn, url="https://techycsr.dev")
            ],
            [
                InlineKeyboardButton(back_btn, callback_data="support")
            ]
        ]
    )
    
    await callback.message.edit(
        text=translated_admin_info,
        reply_markup=keyboard,
        disable_web_page_preview=False  # Enable preview to show website card
    )

# Function to redirect to admin panel
async def admin_panel_callback(client, callback: CallbackQuery):
    """Redirect to the admin panel via maintenance settings"""
    user_id = callback.from_user.id
    
    # Verify user is admin before proceeding
    if not await is_admin_user(user_id):
        alert_message = await async_translate_to_lang(
            "⚠️ Unauthorized access attempt. This action has been logged.", 
            user_id
        )
        await callback.answer(alert_message, show_alert=True)
        return
        
    await maintenance_settings(client, callback)

# Feature states (defaults)
feature_states = {
    "image_generation": "off",
    "voice_feature": "off",
    "premium_service": "off"
}

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

