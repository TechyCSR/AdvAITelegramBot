import os
from pymongo import MongoClient
import soundfile as sf
import speech_recognition as sr
from pyrogram import Client, filters
from config import DATABASE_URL

# Initialize the MongoDB client
mongo_client = MongoClient(DATABASE_URL)

# Access or create the database and collection
db = mongo_client['aibotdb']
user_voice_collection = db['user_voice']

def ogg_to_wav(input_path, output_path):
    audio, sr = sf.read(input_path)
    sf.write(output_path, audio, sr, format="WAV")

async def handle_voice_message(client, message):
    try:
        file_id = message.voice.file_id 
    except Exception:
        file_id = message.audio.file_id

    voice_path = await client.download_media(file_id)
    
    # Convert the voice message to WAV format
    wav_path = voice_path + ".wav"
    ogg_to_wav(voice_path, wav_path)

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
    finally:
        os.remove(wav_path)
        os.remove(voice_path)

    # Save user interaction status in MongoDB
    user_id = message.from_user.id
    user_voice_collection.update_one(
        {"user_id": user_id},
        {"$set": {"voice": True}},
        upsert=True
    )

    # Send the recognized text back to the user
    print(res)
    await message.reply_text(res)
