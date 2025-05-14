import requests
import os
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import OCR_KEY, DATABASE_URL, LOG_CHANNEL
from pymongo import MongoClient
from modules.modles.ai_res import get_response, get_streaming_response
from modules.chatlogs import user_log


mongo_client = MongoClient(DATABASE_URL)

# Access or create the database and collection
db = mongo_client['aibotdb']
history_collection = db['history']

# OCR service with fallback options
async def extract_text_from_image(image_path, ocr_key=OCR_KEY):
    try:
        # Primary OCR service
        url = "https://api.ocr.space/parse/image"
        headers = {"apikey": ocr_key}
        with open(image_path, "rb") as image_file:
            response = requests.post(url, headers=headers, files={"image": image_file})
        
        response_data = response.json()
        if response_data["IsErroredOnProcessing"] == False:
            return response_data["ParsedResults"][0]["ParsedText"], None
        else:
            error_message = response_data["ErrorMessage"]
            return None, f"OCR Error: {error_message}"
            
    except Exception as e:
        return None, f"OCR processing error: {str(e)}"

async def extract_text_res(bot, update):
    # Show processing status with a modern UI
    processing_msg = await update.reply_text(
        "🔍 **Processing Image**\n\n"
        "Extracting and analyzing text content...\n"
        "This may take a moment."
    )
    
    # Extract caption if available
    caption_prompt = ""
    if update.caption:
        if update.caption.lower().startswith(("ai", "ask")):
            caption_prompt = update.caption.split(" ", 1)[1] if len(update.caption.split(" ")) > 1 else ""
        else:
            caption_prompt = update.caption
    
    # Get the largest available version of the image
    if isinstance(update.photo, list):
        photo = update.photo[-1]
    else:
        photo = update.photo

    # Download the image file
    file = await bot.download_media(photo.file_id)
    
    # Extract text from the image
    extracted_text, error = await extract_text_from_image(file)
    
    if error:
        await processing_msg.edit_text(
            f"❌ **Text Extraction Failed**\n\n{error}"
        )
        await bot.send_photo(chat_id=LOG_CHANNEL, photo=file, caption=f"#OCRFailed\nUser: {update.from_user.mention}\nError: {error}")
        os.remove(file)
        return
    
    # If no text was extracted
    if not extracted_text or extracted_text.strip() == "":
        await processing_msg.edit_text(
            "⚠️ **No Text Detected**\n\n"
            "I couldn't find any readable text in this image.\n"
            "Please try with a clearer image or one containing visible text."
        )
        await bot.send_photo(chat_id=LOG_CHANNEL, photo=file, caption=f"#NoTextDetected\nUser: {update.from_user.mention}")
        os.remove(file)
        return
    
    # Combine extracted text with caption if available
    if caption_prompt:
        full_prompt = f"{extracted_text}\n\n{caption_prompt}"
    else:
        full_prompt = extracted_text
    
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
            prompt = f"The following text was extracted from an image:\n\n{extracted_text}\n\nUser's question about this text: {caption_prompt}"
        else:
            prompt = f"The following text was extracted from an image. Please analyze it and provide relevant information or respond appropriately:\n\n{extracted_text}"
        
        # Add the new prompt to the history
        history.append({"role": "user", "content": prompt})
        
        # Get streaming response for better UX
        streaming_response = get_streaming_response(history)
        if streaming_response:
            complete_response = ""
            buffer = ""
            last_update_time = asyncio.get_event_loop().time()
            
            # Process streaming response
            await bot.send_chat_action(chat_id=update.chat.id, action=enums.ChatAction.TYPING)
            
            for chunk in streaming_response:
                if hasattr(chunk, 'choices') and chunk.choices:
                    choice = chunk.choices[0]
                    if hasattr(choice, 'delta') and choice.delta:
                        if hasattr(choice.delta, 'content') and choice.delta.content:
                            buffer += choice.delta.content
                            complete_response += choice.delta.content
                            
                            current_time = asyncio.get_event_loop().time()
                            if current_time - last_update_time >= 0.8 or len(buffer) >= 50:
                                try:
                                    await processing_msg.edit_text(
                                        f"📝 **Image Text Analysis**\n\n{complete_response}"
                                    )
                                    buffer = ""
                                    last_update_time = current_time
                                    await bot.send_chat_action(chat_id=update.chat.id, action=enums.ChatAction.TYPING)
                                except Exception as e:
                                    print(f"Edit error: {e}")
            
            # Final update
            if complete_response:
                await processing_msg.edit_text(
                    f"📝 **Image Text Analysis**\n\n{complete_response}"
                )
        else:
            # Fallback to non-streaming response
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
        await bot.send_photo(chat_id=LOG_CHANNEL, photo=file)
        await user_log(bot, update, f"#Image\nExtracted Text: {extracted_text}\n\nAI Response: {complete_response}")
        
    except Exception as e:
        await update.reply_text(f"An error occurred: {e}")
        print(f"Error in image text extraction: {e}")
    
    # Clean up
    os.remove(file)

# Handle the show extracted text callback
async def handle_show_text_callback(client, callback_query):
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

# Handle the follow-up question callback
async def handle_followup_callback(client, callback_query):
    await callback_query.answer("Please send your follow-up question")
    await callback_query.message.edit_text(
        "❓ **Ask a Follow-up Question**\n\n"
        "Please type your question about the image or the extracted text.",
        reply_markup=None
    )


