from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from modules.lang import async_translate_to_lang

from config import OWNER_ID


# Developer user IDs
developer_ids = {
    "CSR": OWNER_ID,      
    "Ankit": 987654321,    
    "Aarushi": 192837465,  
}

# Function to handle support_developers callback
async def support_developers_callback(client, CallbackQuery):
    user_id = CallbackQuery.from_user.id
    
    # Translate the developer contact title and button labels
    dev_title = await async_translate_to_lang("💻 **Developer Contact Options** 💻\n\nSelect a developer to contact them directly.", user_id)
    back_btn = await async_translate_to_lang("🔙 Back", user_id)
    
    # Note: Developer names typically don't need translation as they are proper nouns
    
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("CHANDAN SINGH", url='https://techycsr.me')
            ],
            [
                InlineKeyboardButton("Ankit", url=f"https://t.me/ankxMe"),
                InlineKeyboardButton("Aarushi", url=f"https://t.me/skylark776")
            ],
            [
                InlineKeyboardButton(back_btn, callback_data="support")
            ]
        ]
    )

    await CallbackQuery.message.edit(
        text=dev_title,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
