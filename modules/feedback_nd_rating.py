from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from config import DATABASE_URL, LOG_CHANNEL

mongo_client = MongoClient(DATABASE_URL)

# Access or create the database and collection
db = mongo_client['aibotdb']
user_ratings_collection = db['user_ratings']

voted = []

async def rate_command(client: Client, message):
    user_id = message.from_user.id

    # Check if the user has already voted by querying the database
    if user_ratings_collection.find_one({"user_id": user_id}):
        await message.reply("You have already rated.")
        return

    user = message.from_user
    mention = user.mention(user.first_name)
    
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
    user_id = callback_query.from_user.id
    rating = int(callback_query.data.split("_")[1])
    
    # Store the user ID and rating in the database
    user_ratings_collection.insert_one({"user_id": user_id, "rating": rating})

    mention = callback_query.from_user.mention(callback_query.from_user.first_name)
    rating_message = f"User: {mention}\nID: {user_id}\nRating: {'⭐️' * rating}"

    # Send the rating to the log channel
    await client.send_message(
        chat_id=LOG_CHANNEL,
        text=rating_message
    )

    # Acknowledge the rating to the user
    await callback_query.edit_message_text(f"Thank you for your rating of {'⭐️' * rating} stars!")
