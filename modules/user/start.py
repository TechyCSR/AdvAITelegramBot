import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery, InputMediaPhoto, InputMediaAnimation
from pyrogram.types import InlineQuery
from typing import Union
from modules.lang import async_translate_to_lang, batch_translate, format_with_mention
from modules.chatlogs import channel_log
import database.user_db as user_db
from pyrogram.enums import ParseMode
from config import ADMIN_CONTACT_MENTION, OWNER_ID
from modules.user.premium_management import get_premium_benefits_message, get_premium_status_message
from modules.user.ai_model import TEXT_MODELS, IMAGE_MODELS

# Helper function to get bot username consistently
async def get_bot_username(client):
    """Get bot username from cache or API call with fallback"""
    if hasattr(client, '_bot_cache') and client._bot_cache.get('username'):
        return client._bot_cache['username']
    try:
        bot_me = await client.get_me()
        return bot_me.username
    except Exception as e:
        print(f"Error getting bot username: {e}")
        return "AdvChatGptBot"  # Fallback

# Import for benefits display
# Define button texts with emojis - NO premium button here
button_list = [
    "➕ Add to Group",
    "🛠️ Commands",
    "❓ Help",
    "⚙️ Settings",
    "📞 Support",
    "💎 Get Premium Subscription"
]

welcome_text = """
**Hey there, {user_mention}!** 

Welcome to your new AI companion! 🤖✨

I'm here to make your life easier and more creative. Here's what we can do together ✨

💬 **Chat & Brainstorm** 
   Talk to me about anything! I'm powered by multiple AI models (Just type/write anything to chat)

🎨 **Create Amazing Images** 
   Just describe what you want with `/img`, and I'll bring it to life

🗣️ **Voice Magic** 
   Send voice messages or convert text to speech

👁️ **Image Analysis** 
   Upload any image and I'll describe it or answer questions

━━━━━━━━━━━━━━━━━━━━━
🔥 **What makes me special?**

🧠 **Multiple AI Brains:** """ + ", ".join(TEXT_MODELS.values()) + """

🎨 **Creative Models:** """ + ", ".join(IMAGE_MODELS.values()) + """

⚙️ **Your Choice:** Switch between models anytime in Settings!

━━━━━━━━━━━━━━━━━━━━━
**Built with ❤️ by [Chandan Singh](https://techycsr.me) (@techycsr)**

**Ready to explore? Pick an option below!**
"""

tip_text = "💡 **Pro Tip:** Type any message to start chatting with me **OR**\nuse `/img` with your prompt to generate images!\n**For more commands use /help.**"

# Mini app promotion message
mini_app_text = "🎨 **Want a Better Image Generation Experience?**\n\nTry our **Advanced Image Generator Mini App** for enhanced features, better interface, and more creative control!\n\n✨ **Features:**\n• Interactive image generation\n• Real-time previews\n• Advanced options\n• Better user experience"

LOGO = "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExdnp4MnR0YXk3ZGNjenR6NGRoaDNkc2h2NDgxa285NnExaGM1MTZmYyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/S60CrN9iMxFlyp7uM8/giphy.gif"
UPI_QR_CODE_PATH = "assets/upi_qr.png" # Placeholder - replace with actual path or URL

async def start(client, message: Message):
    await user_db.check_and_add_user(message.from_user.id)
    if message.from_user.username:
        await user_db.check_and_add_username(message.from_user.id, message.from_user.username)

    user_id = message.from_user.id
    mention = message.from_user.mention
    user_lang = user_db.get_user_language(user_id)
    translated_welcome = await format_with_mention(welcome_text.replace("{user_mention}", "{mention}"), mention, user_id, user_lang)
    translated_texts = await batch_translate([tip_text, mini_app_text] + button_list, user_id)
    translated_tip = translated_texts[0]
    translated_mini_app = translated_texts[1]
    translated_buttons = translated_texts[2:]

    # Get bot username from cache (for multi-bot support) or fallback to API call
    bot_username = await get_bot_username(client)

    keyboard_layout = [
        [InlineKeyboardButton(translated_buttons[0], url=f"https://t.me/{bot_username}?startgroup=true")],
        [InlineKeyboardButton(translated_buttons[1], callback_data="commands_start"),
         InlineKeyboardButton(translated_buttons[2], callback_data="help_start")],
        [InlineKeyboardButton(translated_buttons[3], callback_data="settings"),
         InlineKeyboardButton(translated_buttons[4], callback_data="support")],
        [InlineKeyboardButton(translated_buttons[5], callback_data="premium_info")]
    ]
    keyboard = InlineKeyboardMarkup(keyboard_layout)

    await client.send_animation(chat_id=message.chat.id, animation=LOGO, caption=translated_welcome, reply_markup=keyboard)
    
    # premium_message = await get_premium_status_message(user_id)
    # if not premium_message:
    #     await message.reply_text(translated_tip)
    
    # Send mini app promotion message with inline button
    mini_app_button_text = await async_translate_to_lang("🚀 Try Mini App", user_id)
    mini_app_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(mini_app_button_text, url="https://t.me/AdvChatGptbot/ImageGenerator")]
    ])
    await message.reply_text(translated_mini_app, reply_markup=mini_app_keyboard)

async def start_inline(bot, callback: CallbackQuery):
    user_id = callback.from_user.id
    mention = callback.from_user.mention
    user_lang = user_db.get_user_language(user_id)
    translated_welcome = await format_with_mention(welcome_text.replace("{user_mention}", "{mention}"), mention, user_id, user_lang)
    translated_buttons = await batch_translate(button_list, user_id)

    # Get bot username from cache (for multi-bot support) or fallback to API call
    bot_username = await get_bot_username(bot)

    keyboard_layout = [
        [InlineKeyboardButton(translated_buttons[0], url=f"https://t.me/{bot_username}?startgroup=true")],
        [InlineKeyboardButton(translated_buttons[1], callback_data="commands_start"),
         InlineKeyboardButton(translated_buttons[2], callback_data="help_start")],
        [InlineKeyboardButton(translated_buttons[3], callback_data="settings"),
         InlineKeyboardButton(translated_buttons[4], callback_data="support")],
        [InlineKeyboardButton(translated_buttons[5], callback_data="premium_info")]
    ]
    keyboard = InlineKeyboardMarkup(keyboard_layout)

    await bot.edit_message_caption(chat_id=callback.message.chat.id, message_id=callback.message.id, caption=translated_welcome, reply_markup=keyboard)

async def premium_info_page(client_or_bot, update_obj: Union[Message, CallbackQuery], is_callback: bool = False):
    """Sends or edits message to show premium benefits. Can be called by command or callback."""
    user_id = update_obj.from_user.id
    benefits_text = await get_premium_benefits_message(user_id)
    btn_get_sub_text = await async_translate_to_lang("💳 Get Subscription", user_id)
    btn_back_text = await async_translate_to_lang("🔙 Back to Start", user_id)

    keyboard_buttons = [
        [InlineKeyboardButton(btn_get_sub_text, callback_data="premium_plans")],
        # This button takes user back to the main start panel from the benefits page
        [InlineKeyboardButton(btn_back_text, callback_data="back")] 
    ]
    keyboard = InlineKeyboardMarkup(keyboard_buttons)

    if is_callback:
        callback_query = update_obj
        # If current message has a photo (e.g. QR code), change it to LOGO animation
        if callback_query.message.photo:
            try:
                await client_or_bot.edit_message_media(
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.id,
                    media=InputMediaAnimation(LOGO),
                )
                # Edit caption separately after media is changed
                await client_or_bot.edit_message_caption(
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.id,
                    caption=benefits_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                print(f"Error editing media/caption for premium_info_page (photo to animation): {e}")
                # Fallback to sending a new message if edit fails catastrophically
                await client_or_bot.send_animation(
                    chat_id=callback_query.message.chat.id,
                    animation=LOGO,
                    caption=benefits_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
                await callback_query.message.delete() # Delete old message if we sent a new one
        else: # If current message is text or animation (already LOGO), just edit caption/text
            try:
                if callback_query.message.animation or callback_query.message.caption: # If it has caption (animation or text with media)
                    await client_or_bot.edit_message_caption(
                        chat_id=callback_query.message.chat.id,
                        message_id=callback_query.message.id,
                        caption=benefits_text,
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
                else: # Plain text message
                    await client_or_bot.edit_message_text(
                        chat_id=callback_query.message.chat.id,
                        message_id=callback_query.message.id,
                        text=benefits_text,
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True
                    )
            except Exception as e:
                print(f"Error editing message for premium_info_page (text/animation): {e}")
                # Fallback: send new message if edit fails
                await client_or_bot.send_animation(
                    chat_id=callback_query.message.chat.id, animation=LOGO, caption=benefits_text, 
                    reply_markup=keyboard, parse_mode=ParseMode.HTML
                )
                # Try to delete the old message if sending new one
                try: await callback_query.message.delete() 
                except: pass
        await callback_query.answer()
    else: # Called from /premiumsubscribe command (Message object)
        message = update_obj
        # Send a new message with the LOGO animation and benefits text
        await client_or_bot.send_animation(
            chat_id=message.chat.id,
            animation=LOGO,
            caption=benefits_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )

async def premium_plans_callback(client: pyrogram.Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    plans_title = await async_translate_to_lang("💎 **Premium Subscription Plans** 💎", user_id)
    plan1_text = await async_translate_to_lang("₹249 - Weekly Access(~2.9 USD)", user_id)
    plan2_text = await async_translate_to_lang("₹899 - Monthly Access(~10.5 USD) (Best Value!)", user_id)
    plan3_text = await async_translate_to_lang("₹9499 - Yearly Access(~111.7 USD) (Ultimate Savings!)", user_id)
    payment_instructions_upi = await async_translate_to_lang("Scan the **Above QR** or use UPI ID: `csr.info.in@oksbi`", user_id)
    payment_instructions_usdt = await async_translate_to_lang("For **USDT (TRC20)** payment, use the address: `TUUWniGShkxb8Bg5tj6ZiA9UzHzxxbwi6i`", user_id)
    paid_button_text = await async_translate_to_lang("✅ I've Paid (Notify Admin)", user_id)
    back_button_text = await async_translate_to_lang("🔙 Back to Benefits", user_id)

    text = f"{plans_title}\n\n"
    text += f"🔹 {plan1_text}\n"
    text += f"🔹 {plan2_text}\n"
    text += f"🔹 {plan3_text}\n\n"
    text += f"{payment_instructions_upi}\n\n"
    text += f"{payment_instructions_usdt}\n\n"
    text += await async_translate_to_lang("After payment, click below to notify admin and **send a screenshot of your payment to {admin_contact} **for faster verification.\n\n".replace("{admin_contact}", ADMIN_CONTACT_MENTION if ADMIN_CONTACT_MENTION else f"the bot owner (ID: {OWNER_ID})"), user_id)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(paid_button_text, callback_data="premium_paid_notify")],
        [InlineKeyboardButton(back_button_text, callback_data="premium_info")]
    ])

    try:
        # Edit the existing message: change media to QR code and update caption
        await client.edit_message_media(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.id,
            media=InputMediaPhoto(UPI_QR_CODE_PATH) # UPI_QR_CODE_PATH must be accessible
        )
        # Edit caption separately after media is changed
        await client.edit_message_caption(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.id,
            caption=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN 
        )
    except Exception as e:
        print(f"Error editing message for premium_plans_callback: {e}. Fallback: Deleting old and sending new photo message.")
        # Fallback: If editing media fails (e.g. original message was text-only, or other issue)
        # delete the old message and send a new one with the photo.
        try: await callback_query.message.delete() 
        except: pass # Ignore if deletion fails
        await client.send_photo(
            chat_id=callback_query.message.chat.id, 
            photo=UPI_QR_CODE_PATH, 
            caption=text, 
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    await callback_query.answer()

async def premium_paid_notify_callback(client: pyrogram.Client, callback_query: CallbackQuery):
    user = callback_query.from_user
    
    user_mention = user.mention if hasattr(user, 'mention') else f"<a href='tg://user?id={user.id}'>User {user.id}</a>"
    username_str = f"@{user.username}" if user.username else "N/A"

    admin_notification_text = (
        f"🔔 **Premium Payment Notification** 🔔\n\n"
        f"👤 **User Details:**\n"
        f"    Mention: {user_mention}\n"
        f"    Username: {username_str}\n"
        f"    User ID: `{user.id}`\n\n"
        f"💰 User claims to have paid for a premium subscription.\n\n"
        f"👉 **Action Required:**\n"
        f"    Please verify the payment. If confirmed, grant premium access using:\n"
        f"    `/premium {user.id} <days>`\n\n"
        f"Thank you! ✨"
    )
    
    admin_to_notify = OWNER_ID 
    try:
        # Ensure Markdown is parsed for the admin notification
        await client.send_message(admin_to_notify, admin_notification_text)
    except Exception as e:
        print(f"Error sending premium paid notification to admin {admin_to_notify}: {e}")

    user_reply_base = "✅ Your payment notification has been sent to the admin. **Please remember to send a screenshot of your payment to {admin_contact} for faster verification.** They will contact you if there are issues or once your premium is active."
    admin_contact_text = ADMIN_CONTACT_MENTION if ADMIN_CONTACT_MENTION else f"the bot owner (ID: {OWNER_ID})"
    user_reply_text_formatted = user_reply_base.replace("{admin_contact}", admin_contact_text)
    user_reply_text_translated = await async_translate_to_lang(user_reply_text_formatted, user.id)
    
    btn_back_to_plans_text = await async_translate_to_lang("💳 View Plans Again", user.id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(btn_back_to_plans_text, callback_data="premium_plans")]
    ])

    try:
        await client.edit_message_caption(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.id, 
            caption=user_reply_text_translated, 
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error editing message caption for paid notify: {e}. Trying to send new message.")
        await client.send_message(
             chat_id=callback_query.message.chat.id,
             text=user_reply_text_translated,
             reply_markup=keyboard
        )
        try: await callback_query.message.delete() 
        except: pass
    await callback_query.answer("Notification sent to admin! Please also send them a screenshot.", show_alert=True)

