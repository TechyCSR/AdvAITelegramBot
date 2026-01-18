import os
import asyncio
import tempfile
import logging
import imghdr
from pyrogram import enums
from pyrogram.types import InputMediaPhoto
from pyrogram.errors import MediaCaptionTooLong
from config import LOG_CHANNEL
from modules.models.ai_res import get_history_collection, check_and_update_system_prompt, DEFAULT_SYSTEM_MESSAGE
from modules.chatlogs import user_log
from modules.core.request_queue import (
    can_start_image_request, 
    start_image_request, 
    finish_image_request
)
import g4f
import g4f.Provider
from g4f.client import Client as G4FClient
import base64

logger = logging.getLogger(__name__)

# ============================================================================
# VISION PROVIDER CONFIGURATIONS - All Auth-Free
# ============================================================================
VISION_PROVIDERS = [
    {
        "name": "DeepInfra",
        "provider": g4f.Provider.DeepInfra,
        "model": "meta-llama/Llama-3.2-90B-Vision-Instruct",
        "timeout": 60,
    },
    {
        "name": "Qwen",
        "provider": g4f.Provider.Qwen,
        "model": "qwen2.5-vl-32b-instruct",
        "timeout": 60,
    },
    {
        "name": "HuggingFace",
        "provider": g4f.Provider.HuggingFace,
        "model": "meta-llama/Llama-3.2-11B-Vision-Instruct",
        "timeout": 90,
    },
    {
        "name": "DeepseekAI_JanusPro7b",
        "provider": g4f.Provider.DeepseekAI_JanusPro7b,
        "model": "janus-pro-7b",
        "timeout": 90,
    },
    {
        "name": "PollinationsAI",
        "provider": g4f.Provider.PollinationsAI,
        "model": "openai",
        "timeout": 60,
    },
]

async def analyze_image_with_providers(images: list, user_question: str) -> tuple:
    """
    Try multiple vision providers until one succeeds.
    Returns (response_text, provider_name) or (None, error_message)
    """
    last_error = None
    
    for provider_config in VISION_PROVIDERS:
        provider_name = provider_config["name"]
        provider = provider_config["provider"]
        model = provider_config["model"]
        timeout = provider_config["timeout"]
        
        try:
            logger.info(f"Trying vision provider: {provider_name} with model: {model}")
            
            loop = asyncio.get_event_loop()
            
            def sync_vision():
                g4f_client = G4FClient(provider=provider)
                response = g4f_client.chat.completions.create(
                    messages=[{"content": user_question, "role": "user"}],
                    images=images,
                    model=model
                )
                return response.choices[0].message.content
            
            # Run with timeout
            response = await asyncio.wait_for(
                loop.run_in_executor(None, sync_vision),
                timeout=timeout
            )
            
            if response and len(response) > 10:
                logger.info(f"Vision provider {provider_name} succeeded")
                return response, provider_name
            else:
                logger.warning(f"Vision provider {provider_name} returned empty/short response")
                continue
                
        except asyncio.TimeoutError:
            logger.warning(f"Vision provider {provider_name} timed out")
            last_error = f"{provider_name} timed out"
            continue
        except Exception as e:
            logger.error(f"Vision provider {provider_name} failed: {str(e)}")
            last_error = f"{provider_name}: {str(e)}"
            continue
    
    return None, f"All vision providers failed. Last error: {last_error}"

# ============================================================================
# IMAGE EDITING PROVIDER CONFIGURATIONS - For image-to-image modifications
# ============================================================================
IMAGE_EDIT_PROVIDERS = [
    {
        "name": "BlackForestLabs_Flux1KontextDev",
        "provider": g4f.Provider.BlackForestLabs_Flux1KontextDev,
        "model": "flux-kontext-dev",
        "timeout": 120,
    },
    {
        "name": "HuggingFaceInference",
        "provider": g4f.Provider.HuggingFaceInference,
        "model": "black-forest-labs/FLUX.1-dev",
        "timeout": 120,
    },
    {
        "name": "DeepseekAI_JanusPro7b",
        "provider": g4f.Provider.DeepseekAI_JanusPro7b,
        "model": "janus-pro-7b-image",
        "timeout": 120,
    },
]

# ============================================================================
# AI-DRIVEN INTENT DETECTION - Let AI decide if image editing is needed
# ============================================================================

INTENT_DETECTION_PROMPT = """You are an AI assistant that analyzes user requests about images.
Analyze the user's message and the image to determine what they want:

1. IMAGE_EDIT - User wants to MODIFY/EDIT/TRANSFORM the image (e.g., "make it cartoon", "add sunglasses", "change background to beach", "remove the person", "make it look vintage")
2. TEXT_RESPONSE - User wants INFORMATION/ANALYSIS about the image (e.g., "what is this?", "describe this", "solve this question", "read the text", "how many people are there?")

IMPORTANT RULES:
- If user wants ANY visual change to the image → IMAGE_EDIT
- If user asks questions, wants descriptions, or needs text extraction → TEXT_RESPONSE
- If unclear, default to TEXT_RESPONSE

Respond in this EXACT format (no extra text):
INTENT: [IMAGE_EDIT or TEXT_RESPONSE]
EDIT_PROMPT: [If IMAGE_EDIT, provide a clear, detailed prompt for image generation describing the desired result. If TEXT_RESPONSE, write "N/A"]
TEXT_RESPONSE: [If TEXT_RESPONSE, provide your helpful response to the user. If IMAGE_EDIT, write "N/A"]
"""

async def detect_intent_with_ai(images: list, user_message: str) -> dict:
    """
    Use AI to analyze the image and user's message to determine intent.
    
    Returns:
        dict with keys:
        - intent: "IMAGE_EDIT" or "TEXT_RESPONSE"
        - edit_prompt: Optimized prompt for image editing (if IMAGE_EDIT)
        - text_response: Text response (if TEXT_RESPONSE)
        - provider: Which provider succeeded
    """
    combined_prompt = f"{INTENT_DETECTION_PROMPT}\n\nUser's message: {user_message}"
    
    # Try vision providers to analyze intent
    for provider_config in VISION_PROVIDERS:
        provider_name = provider_config["name"]
        provider = provider_config["provider"]
        model = provider_config["model"]
        timeout = provider_config["timeout"]
        
        try:
            logger.info(f"Trying intent detection with provider: {provider_name}")
            
            loop = asyncio.get_event_loop()
            
            def sync_intent():
                g4f_client = G4FClient(provider=provider)
                response = g4f_client.chat.completions.create(
                    messages=[{"content": combined_prompt, "role": "user"}],
                    images=images,
                    model=model
                )
                return response.choices[0].message.content
            
            response = await asyncio.wait_for(
                loop.run_in_executor(None, sync_intent),
                timeout=timeout
            )
            
            if response and len(response) > 10:
                # Parse the response
                result = parse_intent_response(response, user_message)
                result["provider"] = provider_name
                logger.info(f"Intent detected: {result['intent']} by {provider_name}")
                return result
                
        except asyncio.TimeoutError:
            logger.warning(f"Intent detection timeout with {provider_name}")
            continue
        except Exception as e:
            logger.error(f"Intent detection failed with {provider_name}: {str(e)}")
            continue
    
    # Fallback to TEXT_RESPONSE if all providers fail
    logger.warning("All intent detection providers failed, defaulting to TEXT_RESPONSE")
    return {
        "intent": "TEXT_RESPONSE",
        "edit_prompt": None,
        "text_response": None,
        "provider": None,
        "error": "Could not detect intent, please try again"
    }

def parse_intent_response(response: str, original_message: str) -> dict:
    """
    Parse the AI's intent detection response.
    
    Args:
        response: Raw AI response
        original_message: Original user message (fallback for edit prompt)
        
    Returns:
        Parsed intent dict
    """
    result = {
        "intent": "TEXT_RESPONSE",
        "edit_prompt": None,
        "text_response": None
    }
    
    lines = response.strip().split('\n')
    current_field = None
    current_value = []
    
    for line in lines:
        line = line.strip()
        
        if line.startswith("INTENT:"):
            if current_field and current_value:
                result[current_field] = '\n'.join(current_value).strip()
            current_field = None
            intent_value = line.replace("INTENT:", "").strip().upper()
            if "IMAGE_EDIT" in intent_value or "EDIT" in intent_value:
                result["intent"] = "IMAGE_EDIT"
            else:
                result["intent"] = "TEXT_RESPONSE"
                
        elif line.startswith("EDIT_PROMPT:"):
            if current_field and current_value:
                result[current_field] = '\n'.join(current_value).strip()
            current_field = "edit_prompt"
            value = line.replace("EDIT_PROMPT:", "").strip()
            if value and value.upper() != "N/A":
                current_value = [value]
            else:
                current_value = []
                
        elif line.startswith("TEXT_RESPONSE:"):
            if current_field and current_value:
                result[current_field] = '\n'.join(current_value).strip()
            current_field = "text_response"
            value = line.replace("TEXT_RESPONSE:", "").strip()
            if value and value.upper() != "N/A":
                current_value = [value]
            else:
                current_value = []
        else:
            if current_field:
                current_value.append(line)
    
    # Don't forget the last field
    if current_field and current_value:
        result[current_field] = '\n'.join(current_value).strip()
    
    # If IMAGE_EDIT but no edit_prompt, use original message
    if result["intent"] == "IMAGE_EDIT" and not result["edit_prompt"]:
        result["edit_prompt"] = original_message
    
    # Clean up N/A values
    if result["edit_prompt"] and result["edit_prompt"].upper() == "N/A":
        result["edit_prompt"] = None
    if result["text_response"] and result["text_response"].upper() == "N/A":
        result["text_response"] = None
    
    return result

async def edit_image_with_providers(image_bytes: bytes, image_name: str, prompt: str) -> tuple:
    """
    Try multiple image editing providers until one succeeds.
    Returns (edited_image_bytes, provider_name) or (None, error_message)
    
    Args:
        image_bytes: The original image as bytes
        image_name: Name/filename of the image
        prompt: The edit instruction from user
        
    Returns:
        Tuple of (image_bytes, provider_name) on success, or (None, error_message) on failure
    """
    last_error = None
    
    for provider_config in IMAGE_EDIT_PROVIDERS:
        provider_name = provider_config["name"]
        provider = provider_config["provider"]
        model = provider_config["model"]
        timeout = provider_config["timeout"]
        
        try:
            logger.info(f"Trying image edit provider: {provider_name} with model: {model}")
            
            loop = asyncio.get_event_loop()
            
            def sync_edit():
                g4f_client = G4FClient(provider=provider)
                response = g4f_client.images.create_variation(
                    image=image_bytes,
                    image_name=image_name,
                    prompt=prompt,
                    model=model,
                    response_format="b64_json"
                )
                # Response should contain the edited image
                if hasattr(response, 'data') and response.data:
                    # Get base64 image data
                    img_data = response.data[0]
                    if hasattr(img_data, 'b64_json') and img_data.b64_json:
                        return base64.b64decode(img_data.b64_json)
                    elif hasattr(img_data, 'url') and img_data.url:
                        # If URL is returned, download it
                        import urllib.request
                        with urllib.request.urlopen(img_data.url, timeout=30) as resp:
                            return resp.read()
                return None
            
            # Run with timeout
            result = await asyncio.wait_for(
                loop.run_in_executor(None, sync_edit),
                timeout=timeout
            )
            
            if result and len(result) > 1000:  # Valid image should be > 1KB
                logger.info(f"Image edit provider {provider_name} succeeded")
                return result, provider_name
            else:
                logger.warning(f"Image edit provider {provider_name} returned empty/invalid result")
                continue
                
        except asyncio.TimeoutError:
            logger.warning(f"Image edit provider {provider_name} timed out")
            last_error = f"{provider_name} timed out"
            continue
        except Exception as e:
            logger.error(f"Image edit provider {provider_name} failed: {str(e)}")
            last_error = f"{provider_name}: {str(e)}"
            continue
    
    return None, f"All image edit providers failed. Last error: {last_error}"

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
            user_question = update.caption
        else:
            user_question = "Describe this image in detail. If there's text or a question in the image, read and answer it."

        await processing_msg.edit_text(
            "🧠 **Analyzing your request...**\n\nAI is understanding what you want..."
        )

        # Prepare image for AI analysis
        with open(file, "rb") as img_f:
            img_bytes = img_f.read()
            detected_type = imghdr.what(file)
            if not detected_type:
                detected_type = "jpeg"
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            data_uri = f"data:image/{detected_type};base64,{img_b64}"
        images = [[data_uri, os.path.basename(file)]]

        # Use AI to detect intent - should we edit the image or respond with text?
        intent_result = await detect_intent_with_ai(images, user_question)
        
        if intent_result.get("error"):
            # If intent detection failed, try direct analysis as fallback
            logger.warning(f"Intent detection failed: {intent_result.get('error')}, falling back to vision analysis")
            intent_result["intent"] = "TEXT_RESPONSE"
        
        logger.info(f"AI Intent: {intent_result['intent']} (detected by {intent_result.get('provider', 'unknown')})")

        if intent_result["intent"] == "IMAGE_EDIT":
            # ============== IMAGE EDITING MODE ==============
            edit_prompt = intent_result.get("edit_prompt") or user_question
            
            await processing_msg.edit_text(
                f"🎨 **Editing your image...**\n\n📝 Edit: _{edit_prompt[:80]}{'...' if len(edit_prompt) > 80 else ''}_\n\nTrying multiple AI providers..."
            )
            
            # Try to edit the image with multiple providers
            edited_image_bytes, provider_info = await edit_image_with_providers(
                img_bytes, 
                os.path.basename(file), 
                edit_prompt
            )
            
            if edited_image_bytes is None:
                logger.error(f"All image edit providers failed: {provider_info}")
                await processing_msg.edit_text(
                    f"❌ **Image Editing Failed**\n\n{provider_info}\n\n"
                    "💡 Tip: Try describing the change differently or ask a question about the image instead."
                )
                try:
                    os.remove(file)
                except Exception:
                    pass
                finish_image_request(user_id)
                return
            
            logger.info(f"Image editing successful using provider: {provider_info}")
            
            # Save edited image
            edited_file = file.replace(".", "_edited.")
            with open(edited_file, "wb") as f:
                f.write(edited_image_bytes)
            
            try:
                await processing_msg.delete()
            except Exception:
                pass
            
            # Build caption with bot username, show prompt only if not too long
            if len(user_question) <= 120:
                caption = f"✨ **Edited Image**\n\n🎨 Request: `{user_question}`\n\n🤖 **@AdvChatGptbot**"
            else:
                caption = f"✨ **Edited Image**\n\n🤖 **@AdvChatGptbot**"
            
            try:
                await bot.send_photo(
                    chat_id=update.chat.id,
                    photo=edited_file,
                    caption=caption,
                    reply_to_message_id=update.id if hasattr(update, 'id') else None
                )
            except Exception as e:
                logger.error(f"Failed to send edited image: {e}")
                await update.reply_text(f"❌ Failed to send edited image: {str(e)}")
            
            # Save to history
            history_collection = get_history_collection()
            user_history = history_collection.find_one({"user_id": user_id})
            if user_history and 'history' in user_history:
                history = user_history['history']
                if not isinstance(history, list):
                    history = [history]
                history = check_and_update_system_prompt(history, user_id)
            else:
                history = DEFAULT_SYSTEM_MESSAGE.copy()
            
            # Store image context for follow-up edits
            image_context = {
                "file_path": edited_file,
                "uses_left": MAX_IMAGE_USES,
                "prompt": user_question,
                "message_id": update.id if hasattr(update, 'id') else None
            }
            
            history.append({"role": "user", "content": f"[Image edit request] {user_question}"})
            history.append({"role": "assistant", "content": f"[Edited image generated: {edit_prompt}]"})
            history_collection.update_one(
                {"user_id": user_id},
                {"$set": {"history": history, IMAGE_CONTEXT_KEY: image_context}},
                upsert=True
            )
            
            # Log to channel
            try:
                await user_log(bot, update, f"#ImageEdit\nPrompt: {user_question}\nEdit: {edit_prompt}", f"Edited with {provider_info}")
            except Exception as e:
                logger.error(f"Error logging image edit: {str(e)}")
            
            # Cleanup original file
            try:
                os.remove(file)
            except Exception:
                pass
            
            # Schedule cleanup for edited image
            await schedule_image_cleanup(bot, user_id, update.chat.id, edited_file)
            finish_image_request(user_id)
            return
        
        # ============== TEXT RESPONSE MODE ==============
        await processing_msg.edit_text(
            "📝 **Generating response...**\n\nAI is analyzing your image..."
        )
        
        # Use the text response from intent detection if available, otherwise analyze again
        if intent_result.get("text_response"):
            ai_response = intent_result["text_response"]
            provider_info = intent_result.get("provider", "unknown")
        else:
            # Analyze image with vision providers
            ai_response, provider_info = await analyze_image_with_providers(images, user_question)
        
        if ai_response is None:
            logger.error(f"All vision providers failed: {provider_info}")
            await processing_msg.edit_text(f"❌ **AI Vision Error**\n\n{provider_info}")
            finish_image_request(user_id)
            return
        
        logger.info(f"Vision analysis successful using provider: {provider_info}")

        # Save image context for follow-up questions
        history_collection = get_history_collection()
        user_history = history_collection.find_one({"user_id": user_id})
        if user_history and 'history' in user_history:
            history = user_history['history']
            if not isinstance(history, list):
                history = [history]
            history = check_and_update_system_prompt(history, user_id)
        else:
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
    
    # Start the request
    start_image_request(user_id, f"Image follow-up: {prompt[:30]}...")
    
    wat = await message.reply_text(f"🧠 <b>Analyzing your request...</b>\n\nAI is understanding what you want...", parse_mode=enums.ParseMode.HTML)
    
    try:
        # Prepare image for AI
        with open(image_context['file_path'], "rb") as img_f:
            img_bytes = img_f.read()
            detected_type = imghdr.what(image_context['file_path'])
            if not detected_type:
                detected_type = "jpeg"
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            data_uri = f"data:image/{detected_type};base64,{img_b64}"
        images = [[data_uri, os.path.basename(image_context['file_path'])]]
        
        # Use AI to detect intent - should we edit the image or respond with text?
        intent_result = await detect_intent_with_ai(images, prompt)
        
        if intent_result.get("error"):
            logger.warning(f"Intent detection failed in follow-up: {intent_result.get('error')}")
            intent_result["intent"] = "TEXT_RESPONSE"
        
        logger.info(f"Follow-up AI Intent: {intent_result['intent']} (detected by {intent_result.get('provider', 'unknown')})")
        
        if intent_result["intent"] == "IMAGE_EDIT":
            # ============== IMAGE EDITING MODE FOR FOLLOW-UP ==============
            edit_prompt = intent_result.get("edit_prompt") or prompt
            
            await wat.edit_text(f"🎨 <b>Editing your image...</b>\n\n📝 _{edit_prompt[:60]}{'...' if len(edit_prompt) > 60 else ''}_", parse_mode=enums.ParseMode.HTML)
            
            # Try to edit the image with multiple providers
            edited_image_bytes, provider_info = await edit_image_with_providers(
                img_bytes, 
                os.path.basename(image_context['file_path']), 
                edit_prompt
            )
            
            if edited_image_bytes is None:
                raise Exception(f"All image edit providers failed: {provider_info}")
            
            logger.info(f"Image editing follow-up succeeded with provider: {provider_info}")
            
            # Save edited image
            edited_file = image_context['file_path'].replace(".", "_edited_followup.")
            with open(edited_file, "wb") as f:
                f.write(edited_image_bytes)
            
            await wat.delete()
            
            # Build caption with bot username, show prompt only if not too long
            if len(prompt) <= 150:
                caption = f"✨ **Edited Image**\n\n🎨 Request: `{prompt}`\n\n🤖 **@AdvChatGptbot**"
            else:
                caption = f"✨ **Edited Image**\n\n🤖 **@AdvChatGptbot**"
            
            await client.send_photo(
                chat_id=message.chat.id,
                photo=edited_file,
                caption=caption,
                reply_to_message_id=message.id if hasattr(message, 'id') else None
            )
            
            # Update uses_left and context to point to edited image
            image_context['uses_left'] -= 1
            image_context['file_path'] = edited_file
            uses_left = image_context['uses_left']
            
            history.append({"role": "user", "content": f"[Image edit request] {prompt}"})
            history.append({"role": "assistant", "content": f"[Edited image: {edit_prompt}]"})
            
            if uses_left <= 0:
                if user_id in image_cleanup_tasks:
                    image_cleanup_tasks[user_id]["task"].cancel()
                    del image_cleanup_tasks[user_id]
                history_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"history": history}, "$unset": {IMAGE_CONTEXT_KEY: ""}},
                    upsert=True
                )
                await message.reply_text("🗑️ Image context cleared. Send a new image for more edits or questions.")
            else:
                history_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"history": history, IMAGE_CONTEXT_KEY: image_context}},
                    upsert=True
                )
                await message.reply_text(f"✅ You have {uses_left} more follow-up(s) left. You can ask questions or request more edits!")
            
            try:
                await user_log(client, message, f"#ImageEdit-Followup\nPrompt: {prompt}", f"Edited with {provider_info}")
            except Exception as e:
                logger.error(f"Error logging: {str(e)}")
            
            finish_image_request(user_id)
            return True
        
        # ============== TEXT RESPONSE MODE FOR FOLLOW-UP ==============
        await wat.edit_text(f"📝 <b>Generating response...</b>", parse_mode=enums.ParseMode.HTML)
        
        # Use text response from intent detection if available
        if intent_result.get("text_response"):
            ai_response = intent_result["text_response"]
            provider_name = intent_result.get("provider", "unknown")
        else:
            # Analyze with vision providers
            ai_response, provider_name = await analyze_image_with_providers(images, prompt)
        
        if not ai_response:
            raise Exception(f"All vision providers failed: {provider_name}")
        
        logger.info(f"Vision follow-up succeeded with provider: {provider_name}")
        
        # Update uses_left
        image_context['uses_left'] -= 1
        uses_left = image_context['uses_left']
        
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": ai_response})
        
        if uses_left <= 0:
            if user_id in image_cleanup_tasks:
                image_cleanup_tasks[user_id]["task"].cancel()
                del image_cleanup_tasks[user_id]
            try:
                os.remove(image_context['file_path'])
            except Exception:
                pass
            history_collection.update_one(
                {"user_id": user_id},
                {"$set": {"history": history}, "$unset": {IMAGE_CONTEXT_KEY: ""}},
                upsert=True
            )
        else:
            history_collection.update_one(
                {"user_id": user_id},
                {"$set": {"history": history, IMAGE_CONTEXT_KEY: image_context}},
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
        
        finish_image_request(user_id)
        return True
        
    except Exception as e:
        logger.exception(f"Error in vision followup: {str(e)}")
        finish_image_request(user_id)
        try:
            await wat.delete()
        except:
            pass
        await message.reply_text(f"❌ <b>AI Vision Error</b>\n\n{str(e)}", parse_mode=enums.ParseMode.HTML)
        return True


