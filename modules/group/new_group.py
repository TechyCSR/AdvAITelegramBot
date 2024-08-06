
# Importing required libraries
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import LOG_CHANNEL as STCLOG



async def new_chat_members(client, message):
    user = message.from_user
    added_members = message.new_chat_members
    chat = message.chat
    bot = await client.get_me()
    bot_id = bot.id
    # group_list= load_group_users()

    # if chat.id not in group_list:
    #     group_list.append(chat.id)
    #     save_groups_user(group_list)
    #     await client.send_message(chat_id=STCLOG , text=f"Group ID {chat.id} has been added to group list.")
    

    for member in added_members:
        if member.id == bot_id:
            nam=user.mention(user.first_name)
            user_info = f"User: {user.mention(user.first_name)}\nUsername: @{user.username}\nID: {user.id}"
            group_info = f"Group ID: `{chat.id}`"
            # Get the member count
            try:
                members_count = await client.get_chat_members_count(chat.id)
                group_info += f"\nMembers: {members_count}"
            except Exception as e:
                print(f"Failed to get members count: {e}")

            await client.send_message(
                chat_id=STCLOG,
                text=f"**🎉#New_group! 🎉\nAdded by \n{user_info}\nGroup info\n{group_info}**",
            )
            message_text =f"🎉 **ᴛʜᴀɴᴋ ʏᴏᴜ {nam} ꜰᴏʀ ᴀᴅᴅɪɴɢ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ!** 🎉\n"

            message_text += """
🤖 ɴᴏᴡ, ᴋɪɴᴅʟʏ ɢʀᴀɴᴛ ᴍᴇ ᴀᴅᴍɪɴ ʀɪɢʜᴛꜱ ꜱᴏ ᴛʜᴀᴛ ɪ ᴄᴀɴ ᴡᴏʀᴋ ᴇꜰꜰᴇᴄᴛɪᴠᴇʟʏ.
ɪ ʀᴇQᴜɪʀᴇ ᴛʜᴇ ꜰᴏʟʟᴏᴡɪɴɢ ʀɪɢʜᴛꜱ:

✅ ᴅᴇʟᴇᴛᴇ ᴍᴇꜱꜱᴀɢᴇꜱ- ᴛʜɪꜱ ᴡɪʟʟ ʜᴇʟᴘ ᴍᴇ ᴋᴇᴇᴘ ᴛʜᴇ ᴄʜᴀᴛ ᴄʟᴇᴀɴ ᴀɴᴅ ᴏʀɢᴀɴɪᴢᴇᴅ.
✅ ɪɴᴠɪᴛᴇ ᴜꜱᴇʀꜱ - ɪ ᴄᴀɴ ᴀꜱꜱɪꜱᴛ ɪɴ ʙʀɪɴɢɪɴɢ ᴍᴏʀᴇ ᴍᴇᴍʙᴇʀꜱ ᴛᴏ ᴛʜᴇ ɢʀᴏᴜᴘ.


ʟᴇᴛ'ꜱ ᴍᴀᴋᴇ ᴛʜɪꜱ ɢʀᴏᴜᴘ ᴀᴡᴇꜱᴏᴍᴇ ᴛᴏɢᴇᴛʜᴇʀ!🚀
"""
            
            
            reply_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("ꜰʀᴇᴇ  ɪᴍᴀɢᴇ ɢᴇɴᴇʀᴀᴛɪᴏɴ", url="https://t.me/AdvChatGptBot"),
                ],
                [
                    InlineKeyboardButton("ᴀᴅᴠ ᴀɪ ᴄᴏᴍᴍᴜɴɪᴛʏ 🔗", url="https://t.me/AdvAIworld"),
                ]
            ]
        )
            await client.send_message(
                chat_id= chat.id,text=message_text,reply_markup=reply_markup,disable_web_page_preview=True)
   