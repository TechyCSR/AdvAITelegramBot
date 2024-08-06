
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from config import LOG_CHANNEL


async def rate_command(client: Client, message):
    user = message.from_user
    mention = user.mention(user.first_name)
    user_info = f"User: {mention}\nUsername: @{user.username}\nID: {user.id}"

    rate_message = "**ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ꜰᴇᴇᴅʙᴀᴄᴋ ꜰᴏʀᴍ\nᴘʟᴇᴀꜱᴇ ʀᴀᴛᴇ ʏᴏᴜʀ ᴇxᴘᴇʀɪᴇɴᴄᴇ ᴡɪᴛʜ ᴛʜᴇ ᴀɪ ʙᴏᴛ:\n\nɢɪᴠᴇ ᴍᴇ ꜱᴛᴀʀꜱ ⭐ :) **"
    reply_markup = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⭐️", callback_data="rate_1")],
            [InlineKeyboardButton("⭐️⭐️", callback_data="rate_2")],
            [InlineKeyboardButton("⭐️⭐️⭐️", callback_data="rate_3")],
            [InlineKeyboardButton("⭐️⭐️⭐️⭐️", callback_data="rate_4")],
            [InlineKeyboardButton("⭐️⭐️⭐️⭐️⭐️", callback_data="rate_5")],
        ]
    )

    await client.send_message(
        chat_id=message.chat.id,
        text=rate_message,
        reply_markup=reply_markup,
    )



async def handle_rate_callback(client: Client, callback_query: CallbackQuery):
    user = callback_query.from_user
    rating = callback_query.data.split("_")[1]
    mention = user.mention(user.first_name)
    user_info = f"User: {mention}\nUsername: @{user.username}\nID: {user.id}"
    rating_message = f"{user_info}\nRating: {'⭐️' * int(rating)}"

    await client.send_message(
        chat_id=LOG_CHANNEL,
        text=rating_message
    )

    await callback_query.answer(f"Thank you for your rating of {'⭐️' * int(rating)} stars!", show_alert=True)
