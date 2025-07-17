import asyncio
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from modules.video.video_generation import (
    get_user_tokens, add_user_tokens, remove_user_tokens, generate_video_for_user, TOKENS_PER_VIDEO
)
from modules.video.video_progress import update_video_progress
from config import LOG_CHANNEL, ADMINS
import time
import os

# Config for GCS output
OUTPUT_GCS_URI = "gs://techycsr/test_vdo_output"

# --- PLANS ---
PLANS = [
    {"label": "💎 Rs 11 for 10 Tokens", "price": 11, "tokens": 10, "id": "plan1"},
    {"label": "✨ Rs 100 for 105 Tokens", "price": 100, "tokens": 105, "id": "plan2"},
    {"label": "🚀 Rs 600 for 560 Tokens", "price": 600, "tokens": 560, "id": "plan3"},
]

# --- Modern Video Generation Handler ---
async def video_command_handler(client, message: Message):
    user_id = message.from_user.id
    prompt = message.text.split(" ", 1)[1] if len(message.text.split(" ", 1)) > 1 else None
    
    if not prompt:
        tokens = await get_user_tokens(user_id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Show Plans", callback_data="show_plans")]
        ])
        help_text = (
            "<b>🎥 Video Generation Help</b>\n\n"
            "<b>Current Balance:</b> <code>{} tokens</code>\n"
            "<b>Cost per Video:</b> <code>{} tokens</code>\n\n"
            "<b>How to use:</b>\n"
            "<code>/video your creative prompt here</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/video A serene lake at sunset with mountains in the background</code>\n"
            "• <code>/video Timelapse of a blooming flower in a garden</code>\n"
            "• <code>/video Aerial view of a bustling city at night</code>\n\n"
            "<i>💡 Tip: Be descriptive and specific in your prompt for better results!</i>"
        ).format(tokens, TOKENS_PER_VIDEO)
        
        await message.reply_text(
            help_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        return

    is_admin = user_id in ADMINS
    tokens = await get_user_tokens(user_id) if not is_admin else TOKENS_PER_VIDEO
    if not is_admin and tokens < TOKENS_PER_VIDEO:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Check Tokens", callback_data=f"check_tokens_{user_id}"),
             InlineKeyboardButton("💳 Show Plans", callback_data="show_plans")]
        ])
        await message.reply(
            f"<b>🚫 Not enough tokens!</b>\n\nYou need <b>{TOKENS_PER_VIDEO}</b> tokens to generate a video.\n<code>You currently have: {tokens} tokens</code>",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        return

    wait_msg = await message.reply(
        "<b>🎬 Generating your video...</b>",
        parse_mode=ParseMode.HTML
    )

    progress_task = asyncio.create_task(update_video_progress(client, wait_msg, prompt))
    
    local_path, result = await generate_video_for_user(user_id, prompt, OUTPUT_GCS_URI)

    progress_task.cancel()

    if local_path:
        await wait_msg.edit_text(
            f"<b>✅ Video generated successfully!</b>",
            parse_mode=ParseMode.HTML
        )
        try:
            # Truncate caption if too long (Telegram limit is 1024 chars)
            caption = f"<b>🎬 Prompt:</b> <code>{prompt}</code>"
            if len(caption) > 500:  # Leave some room for HTML tags
                caption = caption[:497] + "..."
            
            await message.reply_video(local_path, caption=caption, parse_mode=ParseMode.HTML)
        except Exception as e:
            await message.reply_text(f"❌ Failed to send video: {e}")
        # Log to channel
        try:
            user = message.from_user
            user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>" if user else f"User {user_id}"
            log_caption = (
                f"#VideoGen\n"
                f"<b>User:</b> {user_mention} (ID: <code>{user_id}</code>)\n"
                f"<b>Prompt:</b> <code>{prompt[:200]}{'...' if len(prompt) > 200 else ''}</code>\n"
                f"<b>Time:</b> <code>{time.strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
                f"<b>Tokens Used:</b> 10\n"
            )
            await client.send_video(
                chat_id=LOG_CHANNEL,
                video=local_path,
                caption=log_caption,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            print(f"[VideoGenLog] Failed to log to channel: {e}")
        # Remove the local video file
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
        except Exception as e:
            print(f"[VideoGenCleanup] Failed to remove video file: {e}")
    else:
        await wait_msg.edit_text(
            f"<b>❌ Video generation failed.</b>\n\n<code>{result}</code>\n\n<b>Please try with a different prompt.</b>",
            parse_mode=ParseMode.HTML
        )

# /addt <userid> <tokens>
async def addt_command_handler(client, message: Message):
    parts = message.text.split()
    if len(parts) != 3:
        await message.reply_text("Usage: /addt <userid> <tokens>")
        return
    try:
        user_id = int(parts[1])
        tokens = int(parts[2])
    except ValueError:
        await message.reply_text("User ID and tokens must be integers.")
        return
    await add_user_tokens(user_id, tokens)
    await message.reply_text(f"✅ Added {tokens} tokens to user {user_id}.")
    # Notify the user
    try:
        await client.send_message(
            chat_id=user_id,
            text=(
                f"<b>🎉 Congratulations!</b>\n\n"
                f"<b>{tokens} new tokens</b> have been added to your account.\n"
                f"You can now generate more amazing Veo 3 videos!\n\n"
                f"<i>Use /video &lt;your prompt&gt; to get started.</i>"
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.reply_text(f"ℹ️ Could not notify user (maybe they haven't started the bot): {e}")

# /removet <userid> <tokens>
async def removet_command_handler(client, message: Message):
    parts = message.text.split()
    if len(parts) != 3:
        await message.reply_text("Usage: /removet <userid> <tokens>")
        return
    try:
        user_id = int(parts[1])
        tokens = int(parts[2])
    except ValueError:
        await message.reply_text("User ID and tokens must be integers.")
        return
    success = await remove_user_tokens(user_id, tokens)
    if success:
        await message.reply_text(f"✅ Removed {tokens} tokens from user {user_id}.")
    else:
        await message.reply_text(f"❌ Could not remove tokens. User may not have enough tokens.")

async def token_command_handler(client, message: Message):
    user_id = message.from_user.id
    tokens = await get_user_tokens(user_id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Show Plans", callback_data="show_plans")]
    ])
    await message.reply(
        f"<b>Your current tokens:</b> <code>{tokens}</code>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

# /vtoken <userid> (admin only)
async def vtoken_command_handler(client, message: Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply_text("Usage: /vtoken <userid>")
        return
    try:
        user_id = int(parts[1])
    except ValueError:
        await message.reply_text("User ID must be an integer.")
        return
    tokens = await get_user_tokens(user_id)
    await message.reply_text(
        f"<b>👤 User ID:</b> <code>{user_id}</code>\n<b>🎟️ Tokens:</b> <code>{tokens}</code>",
        parse_mode=ParseMode.HTML
    )

# Callback handler for Check Tokens, Show Plans, Retry, and Share
async def video_callback_handler(client, callback_query: CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id

    if data.startswith("check_tokens_"):
        tokens = await get_user_tokens(user_id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Show Plans", callback_data="show_plans")]
        ])
        await callback_query.answer()
        await callback_query.message.reply(
            f"<b>Your current tokens:</b> <code>{tokens}</code>",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    elif data == "show_plans":
        plans_text = """
<b>🎬 Why Choose Veo 3 Video Generation?</b>

✅ <b>Stunning HD Video</b> (up to 8 seconds)
✅ <b>Crystal Clear Audio</b> (AI-generated, immersive sound)
✅ <b>Creative Visuals</b> (powered by Google's latest Veo 3.0)
✅ <b>Fast Delivery</b> (ready in 1-2 minutes)
✅ <b>Share Anywhere</b> (MP4 format, easy to use)

<b>Why Buy Tokens?</b>
• Unlock premium video creation for your ideas
• Perfect for reels, stories, business, and fun
• <b>Discounted rates</b> for bulk purchases!

<b>🎁 Special Plans & Discounts</b>

<code>💎 Rs 11 for 10 Tokens</code>  <b>(First 3 purchases only!)</b>
<code>✨ Rs 100 for 105 Tokens</code>  <b>(5% extra!)</b>
<code>🚀 Rs 600 for 560 Tokens</code>  <b>(~15% extra!)</b>

<b>1 Video = 10 Tokens</b>

<b>Ready to buy?</b> Tap below to contact the admin directly for payment and instant activation!
"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💸 Pay & Contact Admin", url="https://t.me/techycsr")]
        ])
        await callback_query.answer()
        await callback_query.message.reply(
            plans_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    elif data.startswith("retry_video_"):
        prompt = data[len("retry_video_"):]
        fake_message = callback_query.message
        fake_message.text = f"/video {prompt}"
        await video_command_handler(client, fake_message) 