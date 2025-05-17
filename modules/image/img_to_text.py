import os
import requests
import json
import asyncio
import tempfile
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import OCR_KEY, DATABASE_URL, LOG_CHANNEL
from pymongo import MongoClient
from modules.models.ai_res import get_response, get_streaming_response
from modules.chatlogs import user_log

# Configure logging
logger = logging.getLogger(__name__)

mongo_client = MongoClient(DATABASE_URL)

# Access or create the database and collection
db = mongo_client['aibotdb']
history_collection = db['history']

# OCR using OCR.space API
async def extract_text_from_image(image_path, ocr_key=OCR_KEY):
    """
    Extract text from an image using OCR.space API
    
    Args:
        image_path: Path to the image file
        ocr_key: OCR.space API key
        
    Returns:
        Tuple of (extracted_text, error_message)
    """
    try:
        logger.info(f"Attempting OCR on image: {image_path}")
        
        # Primary OCR service
        url = "https://api.ocr.space/parse/image"
        payload = {"isOverlayRequired": True, "language": "eng"}
        headers = {"apikey": ocr_key}
        
        with open(image_path, "rb") as image_file:
            files = {"image": image_file}
            logger.info("Sending request to OCR API")
            
            # Use a timeout to avoid hanging
            response = requests.post(url, headers=headers, data=payload, files=files, timeout=15)
        
        # Check if response is valid JSON
        try:
            response_data = response.json()
            logger.info(f"OCR API response status: {response.status_code}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response: {response.text}")
            return None, "The OCR service returned an invalid response. Please try again later."
        
        # Check for successful processing
        if response_data.get("IsErroredOnProcessing") == False and "ParsedResults" in response_data and response_data["ParsedResults"]:
            extracted_text = response_data["ParsedResults"][0]["ParsedText"]
            logger.info(f"Text successfully extracted, length: {len(extracted_text)}")
            return extracted_text, None
        else:
            error_message = response_data.get("ErrorMessage", "Unknown OCR error")
            logger.error(f"OCR API Error: {error_message}")
            return None, f"The OCR service experienced an error. Please try again later."
            
    except requests.exceptions.Timeout:
        logger.error("OCR API request timed out")
        return None, "The OCR service is taking too long to respond. Please try again later."
    except requests.exceptions.ConnectionError:
        logger.error("OCR API connection error")
        return None, "Could not connect to the OCR service. Please try again later."
    except Exception as e:
        logger.exception(f"Exception during OCR API processing: {str(e)}")
        return None, f"An error occurred while processing the image. Please try again later."

async def extract_text_res(bot, update):
    """
    Extract text from an image and generate an AI response
    
    Args:
        bot: The Pyrogram client
        update: The message containing the image
    """
    try:
        # Check if this is a group chat and if so, check caption requirement
        is_group_chat = update.chat.type in ["group", "supergroup"]
        
        # For group chats, require caption with AI or /ai
        if is_group_chat:
            # Ensure the image has a caption
            if not update.caption:
                logger.info(f"Image in group {update.chat.id} ignored - no caption")
                return
                
            # Ensure the caption contains AI or /ai
            caption_lower = update.caption.lower()
            if not ("ai" in caption_lower or "/ai" in caption_lower):
                logger.info(f"Image in group {update.chat.id} ignored - caption doesn't contain AI trigger: {update.caption}")
                return
            
            logger.info(f"Processing image in group {update.chat.id} with AI trigger in caption: {update.caption}")
        
        # Show processing status with a modern UI
        processing_msg = await update.reply_text(
            "🔍 **Processing Image**\n\n"
            "Extracting and analyzing text content...\n"
            "This may take a moment."
        )
        
        # Extract caption if available
        caption_prompt = ""
        if update.caption:
            # Remove the AI trigger word from the caption for processing
            caption_lower = update.caption.lower()
            if "ai" in caption_lower or "/ai" in caption_lower:
                # Extract the text after the trigger
                parts = update.caption.split(" ", 1)
                caption_prompt = parts[1] if len(parts) > 1 else ""
            else:
                caption_prompt = update.caption
        
        # Get the largest available version of the image
        if isinstance(update.photo, list):
            photo = update.photo[-1]
        elif update.photo:
            photo = update.photo
        else:
            await processing_msg.edit_text(
                "❌ **No Image Found**\n\n"
                "Please make sure you're sending an image."
            )
            return
        
        # Create temp directory for image processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download the image file with a unique name
            file_path = os.path.join(temp_dir, f"image_{update.from_user.id}_{int(asyncio.get_event_loop().time())}.jpg")
            
            logger.info(f"Downloading image to {file_path}")
            try:
                file = await bot.download_media(photo.file_id, file_name=file_path)
                logger.info(f"Image downloaded to {file}")
            except Exception as e:
                logger.exception(f"Error downloading image: {str(e)}")
                await processing_msg.edit_text(
                    f"❌ **Download Failed**\n\nCould not download the image: {str(e)}"
                )
                return
            
            # Extract text from the image
            await processing_msg.edit_text(
                "🔍 **Processing Image**\n\n"
                "Extracting text... (This might take up to 30 seconds)"
            )
            
            extracted_text, error = await extract_text_from_image(file)
            
            if error:
                await processing_msg.edit_text(
                    f"❌ **Text Extraction Failed**\n\n{error}\n\n"
                    "Try these alternatives:\n"
                    "• Send a clearer image with better lighting\n"
                    "• Ensure text is well-focused and not blurry\n"
                    "• Type the text manually with your question\n"
                    "• Try again in a few minutes"
                )
                try:
                    await bot.send_photo(chat_id=LOG_CHANNEL, photo=file, caption=f"#OCRFailed\nUser: {update.from_user.mention}\nError: {error}")
                except Exception as e:
                    logger.error(f"Error sending log: {str(e)}")
                return
            
            # If no text was extracted
            if not extracted_text or extracted_text.strip() == "":
                await processing_msg.edit_text(
                    "⚠️ **No Text Detected**\n\n"
                    "I couldn't find any readable text in this image.\n"
                    "Please try with a clearer image or one containing visible text."
                )
                try:
                    await bot.send_photo(chat_id=LOG_CHANNEL, photo=file, caption=f"#NoTextDetected\nUser: {update.from_user.mention}")
                except Exception as e:
                    logger.error(f"Error sending log: {str(e)}")
                return
            
            # If text extraction is successful, append the caption to the extracted text
            if caption_prompt:
                # Append the caption to the extracted text
                extracted_text = f"{extracted_text}\n\n[User's question: {caption_prompt}]"
            
            # Update processing message
            await processing_msg.edit_text(
                "✅ **Text Extracted**\n\n"
                "Generating AI response based on the image content..."
            )

            try:
                user_id = update.from_user.id
                
                # Fetch user history from MongoDB
                user_history = history_collection.find_one({"user_id": user_id})
                if user_history:
                    history = user_history['history']
                else: 
                    history = [{
                        "role": "assistant",
                        "content": (
                            "I'm your advanced AI assistant. I can help analyze text from images and provide helpful responses."
                        )
                    }]

                # Create context-aware prompt
                if caption_prompt:
                    prompt = f"The following text was extracted from an image:\n\n{extracted_text}"
                else:
                    prompt = f"The following text was extracted from an image. Please analyze it and provide relevant information or respond appropriately:\n\n{extracted_text}"
                
                # Add the new prompt to the history
                history.append({"role": "user", "content": prompt})
                
                # Show typing indicator
                await bot.send_chat_action(chat_id=update.chat.id, action=enums.ChatAction.TYPING)
                
                # Use non-streaming response for all image processing (both private and group chats)
                ai_response = get_response(history)
                await processing_msg.edit_text(
                    f"📝 **Image Text Analysis**\n\n{ai_response}"
                )
                complete_response = ai_response
                
                # Create action buttons
                action_markup = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("📋 Show Extracted Text", callback_data=f"show_text_{user_id}")
                    ],
                    [
                        InlineKeyboardButton("❓ Ask Follow-up", callback_data=f"followup_{user_id}")
                    ]
                ])
                
                # Send a follow-up message with action buttons
                await update.reply_text(
                    "**Need anything else with this image?**",
                    reply_markup=action_markup
                )
                
                # Add the AI response to the history
                history.append({"role": "assistant", "content": complete_response})

                # Update the user's history in MongoDB
                history_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "history": history,
                        "last_extracted_text": extracted_text  # Store for potential follow-up
                    }},
                    upsert=True
                )

                # Log activity
                try:
                    await bot.send_photo(chat_id=LOG_CHANNEL, photo=file)
                    await user_log(bot, update, f"#Image\nExtracted Text: {extracted_text[:300]}...\n\nAI Response: {complete_response[:300]}...")
                except Exception as e:
                    logger.error(f"Error logging activity: {str(e)}")
                
            except Exception as e:
                logger.exception(f"Error in image analysis: {str(e)}")
                await update.reply_text(f"An error occurred during analysis: {str(e)}")
    except Exception as e:
        logger.exception(f"Error in extract_text_res: {str(e)}")
        await update.reply_text(f"An error occurred: {str(e)}")

# Handle the show extracted text callback
async def handle_show_text_callback(client, callback_query):
    try:
        user_id = int(callback_query.data.split("_")[2])
        
        # Get the stored extracted text
        user_data = history_collection.find_one({"user_id": user_id})
        if user_data and "last_extracted_text" in user_data:
            extracted_text = user_data["last_extracted_text"]
            
            # Show the extracted text
            await callback_query.answer("Showing extracted text")
            await callback_query.message.edit_text(
                f"📋 **Extracted Text**\n\n```\n{extracted_text}\n```\n\n"
                "This is the raw text that was extracted from your image.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back", callback_data=f"back_to_image_{user_id}")]
                ])
            )
        else:
            await callback_query.answer("Extracted text no longer available")
    except Exception as e:
        logger.exception(f"Error in handle_show_text_callback: {str(e)}")
        await callback_query.answer("An error occurred")

# Handle the follow-up question callback
async def handle_followup_callback(client, callback_query):
    try:
        await callback_query.answer("Please send your follow-up question")
        await callback_query.message.edit_text(
            "❓ **Ask a Follow-up Question**\n\n"
            "Please type your question about the image or the extracted text.",
            reply_markup=None
        )
    except Exception as e:
        logger.exception(f"Error in handle_followup_callback: {str(e)}")
        await callback_query.answer("An error occurred")


