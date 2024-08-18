


from datetime import datetime
from jwt_ import verify_jwt
import config
def authenticate_user(user_id, token):
    # Verifies JWT and checks the user in the database
    user = verify_jwt(token)
    if user and user['user_id'] == user_id:
        return True
    return False

async def channel_log(client, message,command):
    logs = config.LOG_CHANNEL

    # Authenticate user
    token = message.from_user.auth_token  # Assuming token is passed with message (Modify accordingly)
    if not authenticate_user(message.from_user.id, token):
        await message.reply("Authentication failed.")
        return

    await client.send_message(
        chat_id=logs,
        text=f"""
**User:** [{message.from_user.first_name}](tg://user?id={message.from_user.id})
**Command:** `{command}`
**Date:** `{datetime.now()}`
**Chat ID:** `{message.chat.id}`
**Message ID:** `{message.id}`
**Text:** `{message.text}`
"""
    )

async def user_log(client, message, prompt):
    logs = config.LOG_CHANNEL

    # Authenticate user
    token = message.from_user.auth_token  # Assuming token is passed with message (Modify accordingly)
    if not authenticate_user(message.from_user.id, token):
        await message.reply("Authentication failed.")
        return

    await client.send_message(
        chat_id=logs,
        text=f"""
**User:** [{message.from_user.first_name}](tg://user?id={message.from_user.id})

**Prompt:** `{prompt}`

**Date:** `{datetime.now()}`
**Chat ID:** `{message.chat.id}`
"""
    )
