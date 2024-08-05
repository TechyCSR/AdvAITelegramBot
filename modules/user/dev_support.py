


from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import OWNER_ID


# Developer user IDs
developer_ids = {
    "CSR": OWNER_ID,      
    "Ankit": 987654321,    
    "Aarushi": 192837465,  
    "YS": 564738291,       
    "Shreyasnh": 837465192 
}

# Function to handle support_developers callback
async def support_developers_callback(client,  CallbackQuery):
    message_text = "💻 **Developer Contact Options** 💻\n\nSelect a developer to contact them directly."

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("CSR", url=f"tg://user?id={developer_ids['CSR']}")
            ],
            [
                InlineKeyboardButton("Ankit", url=f"tg://user?id={developer_ids['Ankit']}"),
                InlineKeyboardButton("Aarushi", url=f"tg://user?id={developer_ids['Aarushi']}")
            ],
            [
                InlineKeyboardButton("YS", url=f"tg://user?id={developer_ids['YS']}"),
                InlineKeyboardButton("Shreyasnh", url=f"tg://user?id={developer_ids['Shreyasnh']}")
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