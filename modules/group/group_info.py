
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import LOG_CHANNEL


#user info
async def info_command(client, message):
    user_id = message.text.split(" ")[1]

    try:
        user = await client.get_users(int(user_id))
        first_name = user.first_name
        last_name = user.last_name if user.last_name else ""
        username = user.username if user.username else ""
        mention = user.mention(first_name)
        info_message = f"User Info:\n\nFirst Name: {first_name}\nLast Name: {last_name}\nUsername: @{username}\nMention: {mention}\nUser ID: {user_id}"
        info_message += f"\n\nAdditional Info:"
        info_message += f"\nStatus: {user.status}"
        info_message += f"\nIs Bot: {user.is_bot}"
        info_message += f"\nIs Verified: {user.is_verified}"
        info_message += f"\nIs Support: {user.is_support}"
        info_message += f"\nData Center ID: {user.dc_id}"
        info_message += f"\nLanguage Code: {user.language_code}"
        
        await message.reply_text(info_message)

    except Exception as e:
        await message.reply_text(f"Failed to get user info for ID {user_id}.\nError: {e}")