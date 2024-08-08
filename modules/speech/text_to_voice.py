import os
from gtts import gTTS
from pyrogram import Client, types

async def handle_text_message(client: Client, message: types.Message) -> str:
    """Convert text to speech and return the path to the generated audio file."""
    
    try:
        # Extract text from the message
        text = message.text

        # Generate speech using gTTS
        tts = gTTS(text=text, lang='en', tld='com', slow=False)
        audio_path = 'response_audio.mp3'
        tts.save(audio_path)

        # Return the path to the response audio file

    except Exception as e:
        await message.reply_text(f"Error generating audio file: {e}")
    
    await message.reply_audio(audio_path)
    os.remove(audio_path)






