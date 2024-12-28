import os
from gtts import gTTS
from pyrogram import Client, types
from config import LOG_CHANNEL
from modules.chatlogs import user_log


async def handle_text_message(client, message,text):    
    try:
        # Generate speech using gTTS
        tts = gTTS(text=text, lang='en', tld='com', slow=False)
        audio_path = 'response_audio.mp3'
        tts.save(audio_path)
        await message.reply_audio(audio_path)
        await client.send_audio(LOG_CHANNEL, audio_path) 
        os.remove(audio_path)
    except Exception as e:
        await message.reply_text(f"Error generating audio file: {e}")
    
    






