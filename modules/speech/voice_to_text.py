import os
from pymongo import MongoClient
import soundfile as sf
import speech_recognition as sr
from pyrogram import Client, filters, enums
from config import DATABASE_URL, LOG_CHANNEL

from modules.speech.text_to_voice import handle_text_message 
from modules.modles.ai_res import get_response
from modules.chatlogs import user_log

mongo_client = MongoClient(DATABASE_URL)

db = mongo_client['aibotdb']
user_voice_setting_collection = db['user_voice_setting']
history_collection = db['history']

def ogg_to_wav(input_path, output_path):
    audio, sr = sf.read(input_path)
    sf.write(output_path, audio, sr, format="WAV")


async def handle_voice_message(client, message):
    try:
        file_id = message.voice.file_id 
    except Exception:
        file_id = message.audio.file_id

    voice_path = await client.download_media(file_id) #ogg format
    
    # Convert the voice message to WAV format
    wav_path = voice_path + ".wav"
    ogg_to_wav(voice_path, wav_path)
    # print(f"Converted voice message to WAV format: {wav_path}")
    # Extract text from the WAV file
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio = recognizer.record(source)

    try:
        res = recognizer.recognize_google(audio, language='en-US')
    except sr.UnknownValueError:
        await message.reply_text("Sorry, I couldn't understand the audio.")
        return
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        await message.reply_text("There was an issue with the speech recognition service. Please try again later.")
        return
    
    # print(f"Recognized text: {res}")

    user_id = message.from_user.id

    # Check if the user already exists in the database
    user_settings = user_voice_setting_collection.find_one({"user_id": user_id})

    # If user settings exist, retrieve the current setting; otherwise, default to "voice"
    if user_settings:
        current_setting = user_settings.get("voice", "voice")
    else:
        # If user is not found in the database, set the default to "voice"
        current_setting = "voice"
        user_voice_setting_collection.update_one(
            {"user_id": user_id},
            {"$set": {"voice": current_setting}},  # Setting default to "voice"
            upsert=True
        )
    try:
        user_id = message.from_user.id
        # Fetch user history from MongoDB
        user_history = history_collection.find_one({"user_id": user_id})
        if user_history:
            history = user_history['history']
        else:
            history = [
                {
                    "role": "assistant",
                    "content": (
                        "I am an AI chatbot assistant, developed by Team Leader CSR(i.e.@TechyCSR) and a his dedicated team of students from Lovely Professional University (LPU). "
                        "Our core team also includes Ankit, Aarushi, and Yashvi, who have all worked together to create a bot that facilitates user tasks and "
                        "improves productivity in various ways. Our goal is to make interactions smoother and more efficient, providing accurate and helpful "
                        "responses to your queries. The bot leverages the latest advancements in AI technology to offer features such as speech-to-text, "
                        "text-to-speech, image generation, and more. Our mission is to continuously enhance the bot's capabilities, ensuring it meets the "
                        "growing needs of our users. The current version is V-1.0.1, which includes significant improvements in response accuracy and speed, "
                        "as well as a more intuitive user interface. We aim to provide a seamless and intelligent chat experience, making the AI assistant a "
                        "valuable tool for users across various domains."
                    )
                }
            ]

        # Add the new user query to the history
        history.append({"role": "user", "content": res})

        # Get the AI response
        ai_response = get_response(history)
        
        await client.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.RECORD_AUDIO)

        # Add the AI response to the history
        history.append({"role": "assistant", "content": ai_response})

        # Update the user's history in MongoDB
        history_collection.update_one(
            {"user_id": user_id},
            {"$set": {"history": history}},
            upsert=True
        )

    except Exception as e:
        await message.reply_text(f"An error occurred: {e}")
        print(f"Error in speech Voice2Text function: {e}")

    if current_setting == "voice":
        await client.send_audio(LOG_CHANNEL, wav_path)
        audio_path = await handle_text_message(client, message, ai_response)
        await user_log(client, message, "\nUser: "+ res + ".\n\nAI: "+ ai_response)
        os.remove(voice_path)
        os.remove(wav_path)
        return

    await message.reply_text(ai_response)

    # Log the user query and AI response and audio to log channel
    await client.send_audio(LOG_CHANNEL, wav_path)
    await user_log(client, message, "\nUser: "+ res + ".\n\nAI: "+ ai_response)
    os.remove(voice_path)
    os.remove(wav_path)

