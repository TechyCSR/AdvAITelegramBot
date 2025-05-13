from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from modules.lang import async_translate_to_lang

global maintenance_text

maintenance_text = """
🚧 This section is under development.
Please check back later.
~@AdvChatGptBot
"""
    

# Function to handle settings_others callback
async def settings_others_callback(client, callback: CallbackQuery):
    global maintenance_text
    user_id = callback.from_user.id
    
    # Translate the maintenance message
    translated_maintenance = await async_translate_to_lang(maintenance_text, user_id)
    await callback.answer(translated_maintenance, show_alert=True)

