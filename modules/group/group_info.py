import logging
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from config import ADMINS, OWNER_ID
from modules.maintenance import maintenance_check, maintenance_message, is_feature_enabled
from modules.user.global_setting import user_lang_collection, user_voice_collection, ai_mode_collection, languages, modes

logger = logging.getLogger(__name__)

#user info
async def info_command(client: Client, message: Message) -> None:
    """
    Improved admin /uinfo panel with interactive buttons for user settings and history.
    """
    if await maintenance_check(message.from_user.id) and message.from_user.id not in ADMINS:
        maint_msg = await maintenance_message(message.from_user.id)
        await message.reply(maint_msg)
        return
    user_id = message.from_user.id
    if user_id in ADMINS or user_id == OWNER_ID:
        try:
            # Get target user ID from command or replied message
            target_user_id = None
            if message.reply_to_message and message.reply_to_message.from_user:
                target_user_id = message.reply_to_message.from_user.id
                target_user = message.reply_to_message.from_user
            else:
                parts = message.text.split()
                if len(parts) > 1:
                    try:
                        target_user_id = int(parts[1])
                        target_user = await client.get_users(target_user_id)
                    except ValueError:
                        username = parts[1].strip('@')
                        try:
                            target_user = await client.get_users(username)
                            target_user_id = target_user.id
                        except Exception:
                            await message.reply_text("Could not find user with that username.")
                            return
                    except Exception as e:
                        await message.reply_text(f"Error finding user: {e}")
                        return
                else:
                    await message.reply_text(
                        "Please specify a user ID or username, or reply to a message from the user."
                    )
                    return
            if not target_user_id:
                await message.reply_text("Could not determine target user.")
                return
            # Format user information
            user_info = f"👤 <b>User Information</b>\n\n"
            user_info += f"<b>User ID:</b> <code>{target_user_id}</code>\n"
            user_info += f"<b>First Name:</b> {target_user.first_name}\n"
            if target_user.last_name:
                user_info += f"<b>Last Name:</b> {target_user.last_name}\n"
            if target_user.username:
                user_info += f"<b>Username:</b> @{target_user.username}\n"
            user_info += f"<b>Is Bot:</b> {'Yes' if target_user.is_bot else 'No'}\n"
            user_info += f"<b>Is Premium:</b> {'Yes' if getattr(target_user, 'is_premium', False) else 'No'}\n"
            user_info += f"<b>Can be contacted:</b> {'Yes' if not target_user.is_bot and not getattr(target_user, 'is_deleted', False) else 'No'}\n"
            # Add both direct contact and public profile links if available
            user_info += f"\n<a href='tg://user?id={target_user_id}'>Direct Contact</a>"
            if target_user.username:
                user_info += f" | <a href='https://t.me/{target_user.username}'>Public Profile</a>"
            # Interactive buttons
            buttons = []
            if not target_user.is_bot and not getattr(target_user, 'is_deleted', False):
                buttons.append([
                    InlineKeyboardButton("⚙️ User Settings", callback_data=f"uinfo_settings_{target_user_id}"),
                    InlineKeyboardButton("🕓 User History", callback_data=f"uinfo_history_{target_user_id}")
                ])
            await message.reply_text(
                user_info,
                reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
                disable_web_page_preview=True,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            await message.reply_text(f"Error processing command: {e}")
            logger.error(f"Error in info command: {e}")
    else:
        await message.reply_text("Only admins can use this command.")

# Callback: Show user settings
async def uinfo_settings_callback(client: Client, callback_query: CallbackQuery):
    try:
        user_id = int(callback_query.data.split("_")[-1])
        lang_doc = user_lang_collection.find_one({"user_id": user_id})
        voice_doc = user_voice_collection.find_one({"user_id": user_id})
        mode_doc = ai_mode_collection.find_one({"user_id": user_id})
        lang = languages.get(lang_doc["language"], lang_doc["language"]) if lang_doc else "Unknown"
        voice = voice_doc.get("voice", "text") if voice_doc else "text"
        mode = modes.get(mode_doc.get("mode", "chatbot"), "chatbot") if mode_doc else "chatbot"
        text = f"<b>User Settings</b>\n\n<b>Language:</b> {lang}\n<b>Voice:</b> {voice}\n<b>Mode:</b> {mode}"
        await callback_query.answer()
        await callback_query.message.edit_text(text, disable_web_page_preview=True)
    except Exception as e:
        await callback_query.answer("Error loading user settings", show_alert=True)

# Callback: Show user history (last 5 messages)
async def uinfo_history_callback(client: Client, callback_query: CallbackQuery):
    try:
        from modules.models.ai_res import get_history_collection
        user_id = int(callback_query.data.split("_")[-1])
        history_collection = get_history_collection()
        user_history = history_collection.find_one({"user_id": user_id})
        if user_history and "history" in user_history:
            history = user_history["history"][-5:]
            text = "<b>Recent User History</b>\n\n"
            for entry in history:
                role = entry.get("role", "user").capitalize()
                content = entry.get("content", "")
                text += f"<b>{role}:</b> {content}\n\n"
        else:
            text = "No history found for this user."
        await callback_query.answer()
        await callback_query.message.edit_text(text, disable_web_page_preview=True)
    except Exception as e:
        await callback_query.answer("Error loading user history", show_alert=True)