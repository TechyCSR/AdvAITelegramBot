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
    # Show processing message with modern UI
    processing_msg = await message.reply_text(
        "🎙️ **Processing Voice Message**\n\n"
        "Converting your audio to text...\n"
        "Please wait a moment."
    )
    
    # Determine the file type (voice or audio)
    try:
        if message.voice:
            file_id = message.voice.file_id
        elif message.audio:
            file_id = message.audio.file_id
        else:
            await processing_msg.edit_text("❌ Unsupported media type")
            return
    except Exception as e:
        await processing_msg.edit_text(f"❌ Error processing media: {e}")
        return

    # Create temporary directory for audio processing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Download the voice message
        voice_path = await client.download_media(file_id, file_name=f"{temp_dir}/audio_file")
        
        # Process audio to extract text
        recognized_text, error = await process_audio_file(voice_path)
        
        # Handle recognition errors
        if error:
            await processing_msg.edit_text(
                f"❌ **Voice Recognition Failed**\n\n{error}\n\n"
                "Please try recording again with clearer audio."
            )
            return
        
        # Handle empty recognition
        if not recognized_text or recognized_text.strip() == "":
            await processing_msg.edit_text(
                "⚠️ **No Speech Detected**\n\n"
                "I couldn't detect any speech in your audio.\n"
                "Please try recording again with clearer speech."
            )
            return
        
        # Update processing message
        await processing_msg.edit_text(
            "✅ **Voice Recognized**\n\n"
            f"I heard: *{recognized_text}*\n\n"
            "Generating response..."
        )
        
        # Get user preferences for voice responses
        user_id = message.from_user.id
        user_settings = user_voice_setting_collection.find_one({"user_id": user_id})
        response_mode = user_settings.get("voice", "voice") if user_settings else "voice"
        
        try:
            # Fetch user conversation history
            user_history = history_collection.find_one({"user_id": user_id})
            if user_history:
                history = user_history['history']
            else:
                history = [{
                    "role": "assistant",
                    "content": (
                        "I'm your advanced AI assistant. I can respond to your voice messages and help with various tasks."
                    )
                }]

            # Add the recognized text to history
            history.append({"role": "user", "content": recognized_text})
            
            # Determine appropriate chat action based on response mode
            chat_action = enums.ChatAction.RECORD_AUDIO if response_mode == "voice" else enums.ChatAction.TYPING
            await client.send_chat_action(chat_id=message.chat.id, action=chat_action)
            
            # Use streaming for better user experience
            streaming_response = get_streaming_response(history)
            
            if streaming_response:
                complete_response = ""
                buffer = ""
                last_update_time = asyncio.get_event_loop().time()
                
                for chunk in streaming_response:
                    if hasattr(chunk, 'choices') and chunk.choices:
                        choice = chunk.choices[0]
                        if hasattr(choice, 'delta') and choice.delta:
                            if hasattr(choice.delta, 'content') and choice.delta.content:
                                buffer += choice.delta.content
                                complete_response += choice.delta.content
                                
                                # Update periodically if response_mode is text
                                if response_mode != "voice":
                                    current_time = asyncio.get_event_loop().time()
                                    if current_time - last_update_time >= 0.8 or len(buffer) >= 50:
                                        try:
                                            await processing_msg.edit_text(
                                                f"🔊 **Voice Message**\n\n"
                                                f"You said: *{recognized_text}*\n\n"
                                                f"**Response:**\n{complete_response}"
                                            )
                                            buffer = ""
                                            last_update_time = current_time
                                            await client.send_chat_action(chat_id=message.chat.id, action=chat_action)
                                        except Exception as e:
                                            print(f"Edit error: {e}")
                
                # Add response to history
                history.append({"role": "assistant", "content": complete_response})
                
                # Update MongoDB with new history
                history_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"history": history}},
                    upsert=True
                )
                
                # Handle different response modes
                if response_mode == "voice":
                    # Convert text response to voice
                    await processing_msg.edit_text(
                        f"🔊 **Voice Message**\n\n"
                        f"You said: *{recognized_text}*\n\n"
                        "Creating audio response..."
                    )
                    
                    audio_path = await handle_text_message(client, message, complete_response)
                    
                    # Update final text message with transcript
                    await processing_msg.edit_text(
                        f"🔊 **Voice Conversation**\n\n"
                        f"You said: *{recognized_text}*\n\n"
                        f"**Response:** {complete_response}"
                    )
                else:
                    # Final text response update
                    await processing_msg.edit_text(
                        f"🔊 **Voice Message**\n\n"
                        f"You said: *{recognized_text}*\n\n"
                        f"**Response:**\n{complete_response}"
                    )
            else:
                # Fallback to non-streaming response
                ai_response = get_response(history)
                
                # Add response to history
                history.append({"role": "assistant", "content": ai_response})
                
                # Update MongoDB with new history
                history_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"history": history}},
                    upsert=True
                )
                
                if response_mode == "voice":
                    # Convert text response to voice
                    audio_path = await handle_text_message(client, message, ai_response)
                    
                    # Update final text message with transcript
                    await processing_msg.edit_text(
                        f"🔊 **Voice Conversation**\n\n"
                        f"You said: *{recognized_text}*\n\n"
                        f"**Response:** {ai_response}"
                    )
                else:
                    # Text-only response
                    await processing_msg.edit_text(
                        f"🔊 **Voice Message**\n\n"
                        f"You said: *{recognized_text}*\n\n"
                        f"**Response:**\n{ai_response}"
                    )
                
                complete_response = ai_response
            
            # Add response option buttons
            response_markup = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔊 Voice Responses" if response_mode != "voice" else "📝 Text Responses", 
                        callback_data=f"toggle_voice_{user_id}"
                    )
                ],
                [
                    InlineKeyboardButton("🎙️ New Voice Message", callback_data=f"new_voice_{user_id}")
                ]
            ])
            
            await message.reply_text(
                "**Response Preferences**",
                reply_markup=response_markup
            )
            
            # Log the voice interaction
            await client.send_audio(LOG_CHANNEL, f"{voice_path}.wav")
            await user_log(client, message, f"\nVoice: {recognized_text}\n\nAI: {complete_response}")
            
        except Exception as e:
            await message.reply_text(f"An error occurred: {e}")
            print(f"Error in speech Voice2Text function: {e}")

# Handle voice preference toggle callback
async def handle_voice_toggle(client, callback_query):
    user_id = int(callback_query.data.split("_")[2])
    
    # Get current setting
    user_settings = user_voice_setting_collection.find_one({"user_id": user_id})
    current_setting = user_settings.get("voice", "voice") if user_settings else "voice"
    
    # Toggle setting
    new_setting = "text" if current_setting == "voice" else "voice"
    
    # Update database
    user_voice_setting_collection.update_one(
        {"user_id": user_id},
        {"$set": {"voice": new_setting}},
        upsert=True
    )
    
    # Notify user
    setting_text = "voice" if new_setting == "voice" else "text"
    await callback_query.answer(f"Changed to {setting_text} responses")
    
    # Update button
    button_text = "📝 Text Responses" if new_setting == "voice" else "🔊 Voice Responses"
    
    # Get existing keyboard
    current_markup = callback_query.message.reply_markup
    if current_markup and current_markup.inline_keyboard:
        # Update first button text but keep the same callback data
        current_markup.inline_keyboard[0][0] = InlineKeyboardButton(
            button_text, 
            callback_data=callback_query.data
        )
        
        # Update message with new keyboard
        await callback_query.message.edit_reply_markup(reply_markup=current_markup)

