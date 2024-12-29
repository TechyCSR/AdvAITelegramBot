


from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import OWNER_ID


# Developer user IDs
developer_ids = {
    "CSR": OWNER_ID,      
    "Ankit": 987654321,    
    "Aarushi": 192837465,  
}

# Function to handle support_developers callback
async def support_developers_callback(client,  CallbackQuery):
    message_text = "💻 **Developer Contact Options** 💻\n\nSelect a developer to contact them directly."

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("CHANDAN SINGH", url='https://t.me/TechyCSR')
            ],
            [
                InlineKeyboardButton("Ankit", url=f"https://t.me/@me0w_v"),
                InlineKeyboardButton("Aarushi", url=f"https://t.me/skylark776")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="support")
            ]
        ]
    )

    await CallbackQuery.message.edit(
        text=message_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )