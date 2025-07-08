import os
import asyncio
import tempfile
import soundfile as sf
import speech_recognition as sr
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import LOG_CHANNEL

from modules.speech.text_to_voice import handle_text_message 
from modules.models.ai_res import get_response, get_streaming_response
from modules.chatlogs import user_log
from modules.core.database import db_service
from modules.core.request_queue import (
    can_start_text_request, 
    start_text_request, 
    finish_text_request
)

# Get collections from the database service
user_voice_setting_collection = db_service.get_collection('user_voice_setting')
history_collection = db_service.get_collection('history')

# Enhanced audio processing to support multiple formats and languages
async def process_audio_file(input_path, output_path=None, language="en-US"):
    """Process audio file to extract text with enhanced language support"""
    try:
        if not output_path:
            output_path = f"{input_path}.wav"
        
        # Convert to WAV format if not already
        audio, sample_rate = sf.read(input_path)
        sf.write(output_path, audio, sample_rate, format="WAV")
        
        # Create recognizer instance with noise reduction
        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = True
        recognizer.energy_threshold = 300  # Adjust based on environment
        
        # Extract text from audio
        with sr.AudioFile(output_path) as source:
            audio_data = recognizer.record(source)
            
        # Try to recognize with Google's service
        try:
            text = recognizer.recognize_google(audio_data, language=language)
            return text, None
        except sr.UnknownValueError:
            return None, "Could not understand the audio. Please try speaking clearly."
        except sr.RequestError as e:
            return None, f"Speech recognition service unavailable: {e}"
            
    except Exception as e:
        return None, f"Audio processing error: {str(e)}"

async def handle_voice_message(client, message):
    processing_msg = await message.reply_text(
        "🎙️ <b>Processing your voice message...</b>\nPlease wait...")
    try:
        file_id = message.voice.file_id if message.voice else message.audio.file_id
    except Exception:
        await processing_msg.edit_text("❌ <b>Unsupported media type.</b>")
        return
    with tempfile.TemporaryDirectory() as temp_dir:
        voice_path = await client.download_media(file_id, file_name=f"{temp_dir}/audio_file")
        recognized_text, error = await process_audio_file(voice_path)
        if error:
            await processing_msg.edit_text(f"❌ <b>Voice Recognition Failed</b>\n{error}")
            return
        if not recognized_text or recognized_text.strip() == "":
            await processing_msg.edit_text(
                "⚠️ <b>No speech detected.</b>\nPlease try again.")
            return
        user_id = message.from_user.id
        
        # Check if user can start a new text request
        can_start, queue_message = await can_start_text_request(user_id)
        if not can_start:
            await processing_msg.edit_text(
                f"📝 <b>Recognized:</b> <i>{recognized_text}</i>\n\n{queue_message}"
            )
            return
        
        try:
            # Start the text request in queue system
            start_text_request(user_id, f"Voice message: {recognized_text[:30]}...")
            
            user_settings = user_voice_setting_collection.find_one({"user_id": user_id})
            response_mode = user_settings.get("voice", "text") if user_settings else "text"
            user_history = history_collection.find_one({"user_id": user_id})
            history = user_history['history'] if user_history else [{"role": "assistant", "content": "I'm your AI assistant."}]
            history.append({"role": "user", "content": recognized_text})
            ai_response = get_response(history)
            history.append({"role": "assistant", "content": ai_response})
            history_collection.update_one({"user_id": user_id}, {"$set": {"history": history}}, upsert=True)
            log_text = f"[Voice2Text] User: {user_id}\nRecognized: {recognized_text}\nAI: {ai_response}"
            await client.send_message(LOG_CHANNEL, log_text)
            clean_response = ai_response.replace("*", "").replace("_", "").replace("`", "").replace("\n", " ").strip()
            if response_mode == "voice":
                await processing_msg.delete()
                await handle_text_message(client, message, clean_response)
            else:
                await processing_msg.edit_text(
                    f"📝 <b>Recognized:</b> <i>{recognized_text}</i>\n\n<b>AI:</b> {ai_response}")
        finally:
            # Always finish the text request in queue system
            finish_text_request(user_id)

# Handle voice preference toggle callback
async def handle_voice_toggle(client, callback_query):
    user_id = int(callback_query.data.split("_")[-1])
    user_settings = user_voice_setting_collection.find_one({"user_id": user_id})
    current_setting = user_settings.get("voice", "text") if user_settings else "text"
    new_setting = "voice" if current_setting == "text" else "text"
    user_voice_setting_collection.update_one({"user_id": user_id}, {"$set": {"voice": new_setting}}, upsert=True)
    await callback_query.answer(f"Changed to {new_setting.title()} mode", show_alert=True)

