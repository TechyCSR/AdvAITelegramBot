import os
import asyncio
import tempfile
import logging
import imghdr
from pyrogram import enums
from pyrogram.types import InputMediaPhoto
from pyrogram.errors import MediaCaptionTooLong
from config import LOG_CHANNEL
from modules.models.ai_res import get_history_collection
from modules.chatlogs import user_log
from modules.core.request_queue import (
    can_start_image_request, 
    start_image_request, 
    finish_image_request
)
import g4f
import g4f.Provider
import base64

logger = logging.getLogger(__name__)

# Helper to manage image context in user session/history
IMAGE_CONTEXT_KEY = "vision_image_context"
MAX_IMAGE_USES = 3
SUPPORTED_IMAGE_EXTENSIONS = [
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff", ".tif", ".jfif", ".pjpeg", ".pjp"
]
SUPPORTED_IMAGE_TYPES = [
    "jpeg", "png", "webp", "bmp", "gif", "tiff"
]

# Helper to split long text into Telegram message-sized chunks
TELEGRAM_MESSAGE_LIMIT = 4096

# Add at the top, after logger definition
image_cleanup_tasks = {}
IMAGE_EXPIRY_SECONDS = 15 * 60  # 15 minutes

def split_message(text, limit=TELEGRAM_MESSAGE_LIMIT):
    """Split text into chunks no longer than Telegram's message limit."""
    return [text[i:i+limit] for i in range(0, len(text), limit)]

async def schedule_image_cleanup(bot, user_id, chat_id, file_path):
    # Cancel any previous cleanup for this user
    if user_id in image_cleanup_tasks:
        image_cleanup_tasks[user_id]["task"].cancel()
    async def cleanup():
        try:
            await asyncio.sleep(IMAGE_EXPIRY_SECONDS)
            # Remove image context from DB
            history_collection = get_history_collection()
            user_history = history_collection.find_one({"user_id": user_id})
            image_context = user_history.get(IMAGE_CONTEXT_KEY) if user_history else None
            if image_context and image_context.get("file_path") == file_path:
                history_collection.update_one(
                    {"user_id": user_id},
                    {"$unset": {IMAGE_CONTEXT_KEY: ""}},
                    upsert=True
                )
                # Delete the file
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass
                # Inform the user
                try:
                    await bot.send_message(chat_id, "🗑️ Your last image query has been cleared after 15 minutes for privacy and storage safety.")
                except Exception:
                    pass
        except asyncio.CancelledError:
            pass
    task = asyncio.create_task(cleanup())
    image_cleanup_tasks[user_id] = {"task": task, "file_path": file_path}

async def clear_previous_image_context(bot, user_id, chat_id):
    # Cancel and cleanup any previous image context for this user
    informed = False
    history_collection = get_history_collection()
    user_history = history_collection.find_one({"user_id": user_id})
    image_context = user_history.get(IMAGE_CONTEXT_KEY) if user_history else None
    if user_id in image_cleanup_tasks:
        image_cleanup_tasks[user_id]["task"].cancel()
        file_path = image_cleanup_tasks[user_id]["file_path"]
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        del image_cleanup_tasks[user_id]
        if image_context:
            # Only inform if there was a previous image context
            try:
                await bot.send_message(chat_id, "🗑️ Your previous image query has been cleared as you uploaded a new image.")
                informed = True
            except Exception:
                pass
    # Remove from DB
    if image_context:
        history_collection.update_one(
            {"user_id": user_id},
            {"$unset": {IMAGE_CONTEXT_KEY: ""}},
            upsert=True
        )
    return informed

async def extract_text_res(bot, update):
    try:
        user_id = update.from_user.id
        
        # Check if user can start a new image request (rate limiting)
        can_start, queue_message = await can_start_image_request(user_id)
        if not can_start:
            await update.reply_text(queue_message)
            return
        
        is_group_chat = update.chat.type in ["group", "supergroup"]
        # For group chats, require caption with AI or /ai
        if is_group_chat:
            if not update.caption:
                await update.reply_text("❌ Please add a caption with your image for AI analysis (e.g. 'AI: What is this?')")
                return
            caption_lower = update.caption.lower()
            if not ("ai" in caption_lower or "/ai" in caption_lower):
                await update.reply_text("❌ Please include 'AI' or '/ai' in your caption to trigger vision analysis.")
                return

        # --- Clear previous image context if any ---
        previous_cleared = await clear_previous_image_context(bot, update.from_user.id, update.chat.id)
        # Inform about expiry policy before processing
        # expiry_info = "⏳ Note: Your image will be automatically cleared after 15 minutes for privacy and storage safety."
        # if previous_cleared:
        #     await update.reply_text(expiry_info)
        # else:
        #     # Only show expiry info if not already shown in previous_cleared message
        #     await update.reply_text(expiry_info)

        # Start the image request in queue system
        start_image_request(user_id, f"Image-to-text analysis: {update.caption[:30] if update.caption else 'Image uploaded'}...")
        
        processing_msg = await update.reply_text(
            "🖼️ **Image received!**\n\n⏳ Analyzing with AI Vision..."
        )

        # Accept both photo and document (file) uploads for images
        image_file = None
        if hasattr(update, 'photo') and update.photo:
            # Get the largest available version of the image
            if isinstance(update.photo, list):
                photo = update.photo[-1]
            else:
                photo = update.photo
            image_file = await bot.download_media(photo.file_id)
        elif hasattr(update, 'document') and update.document:
            # Accept image sent as document if extension/type is supported
            doc = update.document
            ext = os.path.splitext(doc.file_name)[1].lower()
            if ext not in SUPPORTED_IMAGE_EXTENSIONS:
                await update.reply_text(f"❌ Unsupported file type: {ext}\n\nPlease send a valid image file (jpg, png, webp, bmp, gif, tiff, etc).")
                return
            image_file = await bot.download_media(doc.file_id)
        else:
            await update.reply_text("❌ No image found. Please send a photo or an image file.")
            return

        # Save image in generated_images folder
        generated_dir = "generated_images"
        if not os.path.exists(generated_dir):
            os.makedirs(generated_dir)
        # Use a unique name
        file_path = os.path.join(generated_dir, f"image_{update.from_user.id}_{int(asyncio.get_event_loop().time())}")
        os.rename(image_file, file_path)
        file = file_path

        # Ensure file has a valid image extension for Telegram
        detected_type = imghdr.what(file)
        ext_map = {
            "jpeg": ".jpg",
            "png": ".png",
            "webp": ".webp",
            "bmp": ".bmp",
            "gif": ".gif",
            "tiff": ".tiff"
        }
        ext = ext_map.get(detected_type, ".jpg")
        if not file.endswith(ext):
            new_file = file + ext
            os.rename(file, new_file)
            file = new_file

        # Check file extension/type (for g4f)
        ext = os.path.splitext(file)[1].lower()
        if (ext not in SUPPORTED_IMAGE_EXTENSIONS and not detected_type) or \
           (detected_type and detected_type not in SUPPORTED_IMAGE_TYPES):
            await processing_msg.edit_text(
                f"❌ Unsupported image type.\n\nPlease send a valid image file (jpg, png, webp, bmp, gif, tiff, etc)."
            )
            try:
                os.remove(file)
            except Exception:
                pass
            return

        # Smart caption parsing
        if update.caption:
            prompt = update.caption
            user_question = prompt
        else:
            user_question = (
                "System: You are @AdvChatGptBot (https://t.me/AdvChatGptBot) , an expert at reading and understanding images. "
                "If the image contains a question (including MCQs), answer it directly and help the user to understand the question and answer it. "
                "If it is a multiple choice question (MCQ), answer with the correct option (e.g., 'The correct answer is: B'). "
                "If there is no question, describe and explain the image in detail. "
                "If there is text, read it and use it to help answer or explain the image."
            )

        await processing_msg.edit_text(
            "🧠 **Analyzing Image with AI...**\n\nThis may take a few seconds."
        )

        # Prepare image for g4f: read as bytes, encode as base64, and create data URI
        with open(file, "rb") as img_f:
            img_bytes = img_f.read()
            detected_type = imghdr.what(file)
            if not detected_type:
                detected_type = "jpeg"  # fallback
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            data_uri = f"data:image/{detected_type};base64,{img_b64}"
        images = [[data_uri, os.path.basename(file)]]

        # Send image to g4f vision
        try:
            g4f_client = g4f.Client(provider=g4f.Provider.PollinationsAI)
            response = g4f_client.chat.completions.create(
                [{"content": user_question, "role": "user"}], images=images, model="gpt-4o"
            )
            ai_response = response.choices[0].message.content
        except Exception as e:
            logger.exception(f"Error in g4f vision: {str(e)}")
            await processing_msg.edit_text(f"❌ **AI Vision Error**\n\n{str(e)}")
            return

        # Save image context for next MAX_IMAGE_USES responses
        user_id = update.from_user.id
        history_collection = get_history_collection()
        user_history = history_collection.find_one({"user_id": user_id})
        if user_history and 'history' in user_history:
            history = user_history['history']
            if not isinstance(history, list):
                history = [history]
        else:
            from modules.models.ai_res import DEFAULT_SYSTEM_MESSAGE
            history = DEFAULT_SYSTEM_MESSAGE.copy()
        image_context = {
            "file_path": file,
            "uses_left": MAX_IMAGE_USES,
            "prompt": user_question,
            "message_id": update.id if hasattr(update, 'id') else None
        }
        history_collection.update_one(
            {"user_id": user_id},
            {"$set": {"history": history, IMAGE_CONTEXT_KEY: image_context}},
            upsert=True
        )
        # Add to history
        history.append({"role": "user", "content": f"[Image sent: {os.path.basename(file)}] {user_question}"})
        history.append({"role": "assistant", "content": ai_response})
        history_collection.update_one(
            {"user_id": user_id},
            {"$set": {"history": history}},
            upsert=True
        )
        # --- Schedule cleanup for this image ---
        await schedule_image_cleanup(bot, user_id, update.chat.id, file)
        # Send image preview with response
        TELEGRAM_CAPTION_LIMIT = 1024  # Telegram's Markdown caption limit for photos
        caption = f"📝 **AI Vision Response**\n\n{ai_response}\n\n__You can ask up to {MAX_IMAGE_USES} follow-up questions about this image, or type /endimage to clear the context.__"
        try:
            await bot.send_photo(
                chat_id=update.chat.id,
                photo=file,
                caption=caption,
                parse_mode=enums.ParseMode.MARKDOWN
            )
        except MediaCaptionTooLong as e:
            logger.exception(f"Error in send_photo: {str(e)}")
            # If error is due to caption too long, send image without caption and text as new message
            await bot.send_photo(
                chat_id=update.chat.id,
                photo=file
            )
            # Send the full caption in multiple messages if needed
            for chunk in split_message(caption):
                await bot.send_message(
                    chat_id=update.chat.id,
                    text=chunk,
                    parse_mode=enums.ParseMode.MARKDOWN
                )
            
        await processing_msg.delete()
        # Log to channel
        try:
            await bot.send_photo(chat_id=LOG_CHANNEL, photo=file, caption=f"#VisionAI\nUser: {update.from_user.mention}\nPrompt: {user_question}\nAI: {ai_response[:300]}...")
            await user_log(bot, update, f"#VisionAI\nPrompt: {user_question}", ai_response)
        except Exception as e:
            logger.error(f"Error logging activity: {str(e)}")
        
        # Finish the image request in queue system
        finish_image_request(user_id)
        # Do NOT delete the temp file here; only delete after 3 follow-ups or /endimage
    except Exception as e:
        logger.exception(f"Error in extract_text_res: {str(e)}")
        # Finish the image request in queue system even on error
        finish_image_request(user_id)
        await update.reply_text(f"please try again later , we are facing some issues use /endimage to clear the context")

async def handle_vision_followup(client, message):
    user_id = message.from_user.id
    
    # Check if user can start a new image request (rate limiting for follow-ups)
    can_start, queue_message = await can_start_image_request(user_id)
    if not can_start:
        await message.reply_text(queue_message)
        return True  # Return True to indicate this was handled as a vision followup
    
    history_collection = get_history_collection()
    user_history = history_collection.find_one({"user_id": user_id})
    image_context = user_history.get(IMAGE_CONTEXT_KEY) if user_history else None
    history = user_history['history'] if user_history and 'history' in user_history else None
    if not image_context or not history:
        return False  # Not a vision followup
    # Only use image for next MAX_IMAGE_USES responses
    if image_context['uses_left'] <= 0:
        # Remove image context
        if user_id in image_cleanup_tasks:
            image_cleanup_tasks[user_id]["task"].cancel()
            file_path = image_cleanup_tasks[user_id]["file_path"]
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
            del image_cleanup_tasks[user_id]
        history_collection.update_one(
            {"user_id": user_id},
            {"$unset": {IMAGE_CONTEXT_KEY: ""}},
            upsert=True
        )
        # Try to delete the file if it exists
        try:
            if os.path.exists(image_context['file_path']):
                os.remove(image_context['file_path'])
        except Exception:
            pass
        await message.reply_text("🗑️ The last image context has been cleared. If you want to analyze another image, please send a new one.")
        return True
    # Check for /endimage command
    if message.text and message.text.strip().lower() == "/endimage":
        if user_id in image_cleanup_tasks:
            image_cleanup_tasks[user_id]["task"].cancel()
            file_path = image_cleanup_tasks[user_id]["file_path"]
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
            del image_cleanup_tasks[user_id]
        history_collection.update_one(
            {"user_id": user_id},
            {"$unset": {IMAGE_CONTEXT_KEY: ""}},
            upsert=True
        )
        try:
            if os.path.exists(image_context['file_path']):
                os.remove(image_context['file_path'])
        except Exception:
            pass
        await message.reply_text("🗑️ The last image context has been cleared. If you want to analyze another image, please send a new one.")
        return True
    # Use image in this response
    prompt = message.text
    # Check if file exists before using
    if not os.path.exists(image_context['file_path']):
        if user_id in image_cleanup_tasks:
            image_cleanup_tasks[user_id]["task"].cancel()
            del image_cleanup_tasks[user_id]
        history_collection.update_one(
            {"user_id": user_id},
            {"$unset": {IMAGE_CONTEXT_KEY: ""}},
            upsert=True
        )
        await message.reply_text("⚠️ The image file for your last context is no longer available. Please send a new image to continue vision analysis.")
        return True
    # Start the image request in queue system for followup
    start_image_request(user_id, f"Image follow-up analysis: {prompt[:30]}...")
    
    # Add the latest user prompt to history before sending to g4f
    wat = await message.reply_text(f"🔍 **Analyzing Image with AI...**\n\nThis may take a few seconds.")
    history.append({"role": "user", "content": prompt})
    try:
        with open(image_context['file_path'], "rb") as img_f:
            img_bytes = img_f.read()
            detected_type = imghdr.what(image_context['file_path'])
            if not detected_type:
                detected_type = "jpeg"
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            data_uri = f"data:image/{detected_type};base64,{img_b64}"
        images = [[data_uri, os.path.basename(image_context['file_path'])]]
        g4f_client = g4f.Client(provider=g4f.Provider.PollinationsAI)
        response = g4f_client.chat.completions.create(
            history, images=images, model="gpt-4o"
        )
        ai_response = response.choices[0].message.content
    except Exception as e:
        logger.exception(f"Error in g4f vision followup: {str(e)}")
        # Finish the image request in queue system even on error
        finish_image_request(user_id)
        await message.reply_text(f"❌ **AI Vision Error**\n\n{str(e)}")
        return True
    # Update uses_left
    image_context['uses_left'] -= 1
    uses_left = image_context['uses_left']
    # Remove image if done
    if image_context['uses_left'] <= 0:
        if user_id in image_cleanup_tasks:
            image_cleanup_tasks[user_id]["task"].cancel()
            file_path = image_cleanup_tasks[user_id]["file_path"]
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
            del image_cleanup_tasks[user_id]
        try:
            if os.path.exists(image_context['file_path']):
                os.remove(image_context['file_path'])
        except Exception:
            pass
        history_collection.update_one(
            {"user_id": user_id},
            {"$unset": {IMAGE_CONTEXT_KEY: ""}},
            upsert=True
        )
        await message.reply_text("🗑️ The last image context has been cleared. If you want to analyze another image, please send a new one.")
    else:
        history_collection.update_one(
            {"user_id": user_id},
            {"$set": {IMAGE_CONTEXT_KEY: image_context}},
            upsert=True
        )
    # Add to history
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": ai_response})
    history_collection.update_one(
        {"user_id": user_id},
        {"$set": {"history": history}},
        upsert=True
    )
    await message.reply_text(
        f"📝 **AI Vision Response**\n\n{ai_response}\n\n__You can ask {uses_left} more follow-up question(s) about the last image, or type /endimage to clear the context.__",
        parse_mode=enums.ParseMode.MARKDOWN
    )
    await wat.delete()
    # Log to channel
    try:
        await user_log(client, message, f"#VisionAI-Followup\nPrompt: {prompt}", ai_response)
    except Exception as e:
        logger.error(f"Error logging followup: {str(e)}")
    
    # Finish the image request in queue system
    finish_image_request(user_id)
    return True


