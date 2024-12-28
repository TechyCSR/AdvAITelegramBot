from pyrogram import Client, filters
import pyrogram.errors
import asyncio
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import LOG_CHANNEL as STCLOG



async def leave_group(client: Client, message):
    chat_id = message.chat.id
    bot_username = (await client.get_me()).username
    group_id = int(message.command[1])
    
    try:
        await client.leave_chat(group_id)
        await message.reply("Left the group successfully.")
        await client.send_message(STCLOG, f"#Leave\n Admin-SudoUsers {chat_id} \nReason- Admin Knows\nTask - @{bot_username} left the group {group_id}.")
    except pyrogram.errors.FloodWait as e:
        await message.reply(f"Failed to leave the group. Please try again later. Error: {e}")
    except pyrogram.errors.exceptions.ChatAdminRequired as e:
        await message.reply(f"I don't have the necessary permissions to leave the group. Please make sure I have the permission to leave. Error: {e}")
    except Exception as e:
        await message.reply(f"Failed to leave the group. Error: {e}")

async def invite_command(client, message):
    if len(message.command) != 2:
        await message.reply("Invalid command! Please provide a group ID.")
        return
    chat_id = message.text.split(" ")[1]

    try:
        chat_invite_link = await client.export_chat_invite_link(int(chat_id))
        await message.reply_text(f"Invite link for group {chat_id}:\n{chat_invite_link}")
    except Exception as e:
        await message.reply_text(f"Failed to get invite link for group {chat_id}.\nError: {e}")