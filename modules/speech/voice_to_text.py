import os
import speech_recognition as sr 
import soundfile as sf
import os
import speech_recognition as sr
from gtts import gTTS

from pyrogram import Client, filters

def ogg_to_wav(input_path, output_path):
    audio, sr = sf.read(input_path)
    sf.write(output_path, audio, sr, format="WAV")


async def handle_voice_message(client, message):
    try:
        file_id =  message.voice.file_id 
    except Exception:
        file_id= message.audio.file_id


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
        return
    except sr.RequestError as e:
        print("Could not request results from Google Speech Recognition service; {0}".format(e))
        return
    os.remove(wav_path)
    os.remove(voice_path)
    await message.reply_text(res)

    