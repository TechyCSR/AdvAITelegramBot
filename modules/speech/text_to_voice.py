import os
import tempfile
from gtts import gTTS
import pydub
import asyncio
from pyrogram import Client, types
from config import LOG_CHANNEL
from modules.chatlogs import user_log


async def handle_text_message(client, message, text, language='en', voice_speed=False):    
    """
    Convert text to voice with enhanced quality and language support
    
    Parameters:
    - client: Pyrogram client
    - message: Message object
    - text: Text to convert to speech
    - language: Language code (default: 'en')
    - voice_speed: Whether to use slow voice (default: False)
    
    Returns:
    - Path to the generated audio file
    """
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate base audio file using gTTS with adjustable parameters
            temp_path = f"{temp_dir}/response_audio_raw.mp3"
            enhanced_path = f"{temp_dir}/response_audio_enhanced.mp3"
            
            # Generate speech using gTTS with specified language
            tts = gTTS(text=text, lang=language, tld='com', slow=voice_speed)
            tts.save(temp_path)
            
            # Enhance audio quality using pydub if available
            try:
                # Load audio and apply enhancements
                audio = pydub.AudioSegment.from_mp3(temp_path)
                
                # Normalize volume
                normalized_audio = audio.normalize()
                
                # Apply light compression to improve clarity
                compressed_audio = normalized_audio.compress_dynamic_range()
                
                # Export enhanced audio
                compressed_audio.export(enhanced_path, format="mp3", bitrate="192k")
                final_audio_path = enhanced_path
            except Exception as e:
                # If enhancement fails, use the original file
                print(f"Audio enhancement error (using original): {e}")
                final_audio_path = temp_path
            
            # Send audio file with informative caption
            caption = "🎙️ **Voice Response**"
            
            # Send the audio file
            await message.reply_audio(
                final_audio_path, 
                caption=caption,
                title="AI Voice Response",
                performer="Advanced AI Bot"
            )
            
            # Log the audio file
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
    
    






