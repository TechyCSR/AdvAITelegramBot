from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import ADMINS as admin_ids



# print(admin_ids)
# Function to handle settings support callback
async def settings_support_callback(client, CallbackQuery):
    message_text = "🔧 **Support Options** 🔧\n\nSelect an option to get help or support."

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("👥 Admins", callback_data="support_admins"),
                InlineKeyboardButton("💻 Developers", callback_data="support_developers")
            ],
            [
                InlineKeyboardButton("🌐 Community", url="https://community.link"),
                InlineKeyboardButton("💰 Donate", callback_data="support_donate")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="back")
            ]
        ]
    )

    await CallbackQuery.message.edit(
        text=message_text,
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
        await callback.answer("This section is for admins only.", show_alert=True)
        return

    message_text = "🔧 **Admin Panel** 🔧\n\nManage the features below:"

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(f"🖼️ Image Generation ({feature_states['image_generation']})", callback_data="toggle_image_generation")
            ],
            [
                InlineKeyboardButton("🔊 On", callback_data="set_image_generation_on"),
                InlineKeyboardButton("🔇 Off", callback_data="set_image_generation_off")
            ],
            [
                InlineKeyboardButton(f"🎙️ Voice Feature ({feature_states['voice_feature']})", callback_data="toggle_voice_feature")
            ],
            [
                InlineKeyboardButton("🔊 On", callback_data="set_voice_feature_on"),
                InlineKeyboardButton("🔇 Off", callback_data="set_voice_feature_off")
            ],
            [
                InlineKeyboardButton(f"💎 Premium Service ({feature_states['premium_service']})", callback_data="toggle_premium_service")
            ],
            [
                InlineKeyboardButton("🔊 On", callback_data="set_premium_service_on"),
                InlineKeyboardButton("🔇 Off", callback_data="set_premium_service_off")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="support")
            ]
        ]
    )

    await callback.message.edit(
        text=message_text,
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

