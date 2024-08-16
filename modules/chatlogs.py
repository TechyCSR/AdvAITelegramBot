


from datetime import datetime

import config



async def channel_log(client, message,command):
    logs = config.LOG_CHANNEL
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

async def user_log(client, message,prompt):
    logs = config.LOG_CHANNEL
    await client.send_message(
        chat_id=logs,
        text=
f"""
**User:** [{message.from_user.first_name}](tg://user?id={message.from_user.id})

**Prompt:** `{prompt}`

**Date:** `{datetime.now()}`
**Chat ID:** `{message.chat.id}`
"""
    )

