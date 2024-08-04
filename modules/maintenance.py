from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

global maintenance_text

maintenance_text = """
🚧 This section is under development.
Please check back later.
Team  @AdvanceAIBot
"""
    

# Function to handle settings_others callback
async def settings_others_callback(client, callback: CallbackQuery):
    global maintenance_text
    await callback.answer(maintenance_text, show_alert=True)

