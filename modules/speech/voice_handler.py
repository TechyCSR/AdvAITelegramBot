from typing import Optional, Dict, Any, Union
from pyrogram import Client
from pyrogram.types import Message
import asyncio
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from modules.response_handler import response_manager
from modules.lang import translate_text_async, get_user_language
import aiohttp
import json
import wave
import contextlib
import numpy as np
from pydub import AudioSegment
import speech_recognition as sr
from gtts import gTTS

logger = logging.getLogger(__name__)

class VoiceProcessor:
    _instance = None
    _executor = ThreadPoolExecutor(max_workers=10)
    _cache: Dict[str, str] = {}
    _max_cache_size = 100
    _max_retries = 3
    _retry_delay = 1.0
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.output_dir = "voice_files"
        os.makedirs(self.output_dir, exist_ok=True)
        self.recognizer = sr.Recognizer()
    
    def _get_cache_key(self, content: str, lang: str) -> str:
        return f"{content}:{lang}"
    
    def _update_cache(self, key: str, value: str):
        if len(self._cache) >= self._max_cache_size:
            self._cache.clear()
        self._cache[key] = value
    
    async def _download_voice(self, client: Client, message: Message) -> Optional[str]:
        try:
            voice = message.voice
            file_path = await client.download_media(voice)
            return file_path
        except Exception as e:
            logger.error(f"Error downloading voice: {e}")
            return None
    
    def _get_audio_duration(self, file_path: str) -> int:
        try:
            with contextlib.closing(wave.open(file_path, 'r')) as f:
                frames = f.getnframes()
                rate = f.getframerate()
                duration = frames / float(rate)
                return int(duration)
        except Exception as e:
            logger.error(f"Error getting audio duration: {e}")
            return 0
    
    async def voice_to_text(self, file_path: str, lang: str = "en") -> Optional[str]:
        try:
            audio = AudioSegment.from_file(file_path)
            audio.export("temp.wav", format="wav")
            
            with sr.AudioFile("temp.wav") as source:
                audio_data = self.recognizer.record(source)
                text = await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    lambda: self.recognizer.recognize_google(audio_data, language=lang)
                )
            
            os.remove("temp.wav")
            return text
        except Exception as e:
            logger.error(f"Error in voice_to_text: {e}")
            return None
    
    async def text_to_voice(self, text: str, lang: str = "en") -> Optional[str]:
        try:
            cache_key = self._get_cache_key(text, lang)
            if cache_key in self._cache:
                return self._cache[cache_key]
            
            timestamp = int(time.time())
            output_path = f"{self.output_dir}/voice_{timestamp}.mp3"
            
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(output_path)
            
            self._update_cache(cache_key, output_path)
            return output_path
        except Exception as e:
            logger.error(f"Error in text_to_voice: {e}")
            return None

class VoiceHandler:
    def __init__(self):
        self.processor = VoiceProcessor.get_instance()
    
    async def handle_voice_message(
        self,
        client: Client,
        message: Message
    ) -> None:
        try:
            user_id = message.from_user.id
            user_lang = await get_user_language(user_id)
            
            status_message = await message.reply_text(
                await translate_text_async("Processing voice message...", user_lang)
            )
            
            file_path = await self.processor._download_voice(client, message)
            if not file_path:
                await response_manager.handle_error_response(
                    client,
                    message,
                    await translate_text_async(
                        "Failed to process voice message. Please try again.",
                        user_lang
                    )
                )
                return
            
            text = await self.processor.voice_to_text(file_path, user_lang)
            if not text:
                await response_manager.handle_error_response(
                    client,
                    message,
                    await translate_text_async(
                        "Could not recognize speech. Please try again.",
                        user_lang
                    )
                )
                return
            
            await status_message.delete()
            await response_manager.handle_text_response(
                client,
                message,
                f"Transcribed text: {text}"
            )
            
            os.remove(file_path)
        except Exception as e:
            logger.error(f"Error in handle_voice_message: {e}")
            await response_manager.handle_error_response(
                client,
                message,
                "An error occurred while processing the voice message."
            )
    
    async def handle_text_to_voice(
        self,
        client: Client,
        message: Message,
        text: str
    ) -> None:
        try:
            user_id = message.from_user.id
            user_lang = await get_user_language(user_id)
            
            status_message = await message.reply_text(
                await translate_text_async("Converting text to voice...", user_lang)
            )
            
            voice_path = await self.processor.text_to_voice(text, user_lang)
            if not voice_path:
                await response_manager.handle_error_response(
                    client,
                    message,
                    await translate_text_async(
                        "Failed to convert text to voice. Please try again.",
                        user_lang
                    )
                )
                return
            
            duration = self.processor._get_audio_duration(voice_path)
            caption = await translate_text_async(
                f"Voice message for text: {text}",
                user_lang
            )
            
            await status_message.delete()
            await response_manager.handle_voice_response(
                client,
                message,
                voice_path,
                duration,
                caption
            )
            
            os.remove(voice_path)
        except Exception as e:
            logger.error(f"Error in handle_text_to_voice: {e}")
            await response_manager.handle_error_response(
                client,
                message,
                "An error occurred while converting text to voice."
            )

voice_handler = VoiceHandler()

async def handle_voice_message(client: Client, message: Message):
    await voice_handler.handle_voice_message(client, message)

async def handle_text_to_voice(client: Client, message: Message, text: str):
    await voice_handler.handle_text_to_voice(client, message, text) 