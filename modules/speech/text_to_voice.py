import os
import tempfile
from gtts import gTTS
import pydub
import asyncio
from pyrogram import Client, types
from config import LOG_CHANNEL
from modules.chatlogs import user_log
import re


async def handle_text_message(client, message, text, language='en', voice_speed=False):    
    """
    Convert text to voice with enhanced quality and human-like tone.
    - Removes special symbols, markdown, and emojis for natural speech.
    - Only sends voice (not both text and voice).
    """
    try:
        # Clean up text for human-like TTS
        clean_text = re.sub(r'[\*\_\`\~\#\>\-\=\[\]\(\)\{\}\|\^\$\%\@\!\:\;\"\'\<\>]', '', text)
        clean_text = re.sub(r':[a-zA-Z0-9_]+:', '', clean_text)  # Remove emoji shortcodes
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = f"{temp_dir}/response_audio_raw.mp3"
            enhanced_path = f"{temp_dir}/response_audio_enhanced.mp3"
            tts = gTTS(text=clean_text, lang=language, tld='com', slow=voice_speed)
            tts.save(temp_path)
            try:
                audio = pydub.AudioSegment.from_mp3(temp_path)
                normalized_audio = audio.normalize()
                compressed_audio = normalized_audio.compress_dynamic_range()
                compressed_audio.export(enhanced_path, format="mp3", bitrate="192k")
                final_audio_path = enhanced_path
            except Exception as e:
                print(f"Audio enhancement error (using original): {e}")
                final_audio_path = temp_path
            caption = "🎙️ Voice Response"
            await message.reply_audio(
                final_audio_path, 
                caption=caption,
                title="AI Voice Response",
                performer="Advanced AI Bot"
            )
            await client.send_audio(LOG_CHANNEL, final_audio_path)
            return final_audio_path
    except Exception as e:
        await message.reply_text(f"❌ Error generating audio: {e}")
        return None


# More expressive voice synthesis with custom voice markers
async def generate_expressive_voice(client, message, text, style="neutral", language='en'):
    """
    Generate more expressive voice based on text content and style
    
    Parameters:
    - client: Pyrogram client
    - message: Message object
    - text: Text to convert to speech
    - style: Voice style (neutral, formal, friendly)
    - language: Language code
    
    Returns:
    - Path to generated audio
    """
    voice_speed = False
    
    # Adjust parameters based on style
    if style == "formal":
        voice_speed = True  # Slower, more deliberate speech
    elif style == "friendly":
        # Keep default parameters, but could add more customization here
        pass
    
    return await handle_text_message(client, message, text, language, voice_speed)
    
    






