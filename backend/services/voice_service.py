"""
Voice Service for Speech-to-Text and Text-to-Speech

Integrates Whisper STT and OpenAI TTS for voice features.
"""

import asyncio
import logging
import tempfile
import os
from typing import Optional, BinaryIO, AsyncGenerator
from pathlib import Path
from datetime import datetime

from openai import AsyncOpenAI
import aiofiles

logger = logging.getLogger(__name__)


class VoiceService:
    """
    Service for voice processing.

    Features:
    - Speech-to-Text with Whisper
    - Text-to-Speech with OpenAI TTS
    - Multiple voice options
    - Audio format conversion
    - Streaming audio support
    """

    # Supported audio formats for STT
    SUPPORTED_FORMATS = [
        "flac", "m4a", "mp3", "mp4",
        "mpeg", "mpga", "oga", "ogg",
        "wav", "webm"
    ]

    # Available TTS voices
    TTS_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

    # TTS models
    TTS_MODELS = {
        "standard": "tts-1",       # Faster, lower quality
        "hd": "tts-1-hd"           # Higher quality
    }

    def __init__(self):
        self.client = None
        self.temp_dir = Path(tempfile.gettempdir()) / "lumenai_voice"
        self.temp_dir.mkdir(exist_ok=True)
        logger.info("VoiceService initialized")

    def _get_client(self) -> AsyncOpenAI:
        """Lazy initialization of OpenAI client."""
        if not self.client:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            self.client = AsyncOpenAI(api_key=api_key)
        return self.client

    async def transcribe_audio(
        self,
        audio_file: BinaryIO,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
        temperature: float = 0.0,
        model: str = "whisper-1"
    ) -> dict:
        """
        Transcribe audio to text using Whisper.

        Args:
            audio_file: Audio file object
            language: Optional ISO-639-1 language code
            prompt: Optional prompt to guide transcription
            temperature: Sampling temperature (0-1)
            model: Whisper model to use

        Returns:
            Transcription result with text and metadata
        """
        client = self._get_client()

        try:
            start_time = datetime.utcnow()

            # Transcribe
            response = await client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                language=language,
                prompt=prompt,
                temperature=temperature,
                response_format="verbose_json"
            )

            duration = (datetime.utcnow() - start_time).total_seconds()

            result = {
                "text": response.text,
                "language": response.language if hasattr(response, 'language') else language,
                "duration": response.duration if hasattr(response, 'duration') else None,
                "segments": response.segments if hasattr(response, 'segments') else None,
                "processing_time": duration,
                "model": model,
                "timestamp": datetime.utcnow().isoformat()
            }

            logger.info(
                f"Audio transcribed: language={result['language']}, "
                f"duration={result['duration']}s, "
                f"processing_time={duration:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise

    async def transcribe_from_file(
        self,
        file_path: str,
        **kwargs
    ) -> dict:
        """
        Transcribe audio from a file path.

        Args:
            file_path: Path to audio file
            **kwargs: Additional arguments for transcribe_audio

        Returns:
            Transcription result
        """
        async with aiofiles.open(file_path, 'rb') as audio_file:
            return await self.transcribe_audio(audio_file, **kwargs)

    async def synthesize_speech(
        self,
        text: str,
        voice: str = "alloy",
        model: str = "standard",
        speed: float = 1.0,
        response_format: str = "mp3"
    ) -> bytes:
        """
        Synthesize speech from text using OpenAI TTS.

        Args:
            text: Text to synthesize
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            model: TTS model (standard or hd)
            speed: Speech speed (0.25 - 4.0)
            response_format: Audio format (mp3, opus, aac, flac)

        Returns:
            Audio data as bytes
        """
        if voice not in self.TTS_VOICES:
            raise ValueError(f"Invalid voice. Must be one of: {self.TTS_VOICES}")

        if model not in self.TTS_MODELS:
            raise ValueError(f"Invalid model. Must be one of: {list(self.TTS_MODELS.keys())}")

        if not 0.25 <= speed <= 4.0:
            raise ValueError("Speed must be between 0.25 and 4.0")

        client = self._get_client()
        model_name = self.TTS_MODELS[model]

        try:
            start_time = datetime.utcnow()

            # Synthesize
            response = await client.audio.speech.create(
                model=model_name,
                voice=voice,
                input=text,
                speed=speed,
                response_format=response_format
            )

            audio_data = response.content

            duration = (datetime.utcnow() - start_time).total_seconds()

            logger.info(
                f"Speech synthesized: voice={voice}, model={model}, "
                f"text_length={len(text)}, audio_size={len(audio_data)} bytes, "
                f"processing_time={duration:.2f}s"
            )

            return audio_data

        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            raise

    async def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        **kwargs
    ) -> str:
        """
        Synthesize speech and save to file.

        Args:
            text: Text to synthesize
            output_path: Path to save audio file
            **kwargs: Additional arguments for synthesize_speech

        Returns:
            Path to saved audio file
        """
        audio_data = await self.synthesize_speech(text, **kwargs)

        async with aiofiles.open(output_path, 'wb') as f:
            await f.write(audio_data)

        logger.info(f"Speech saved to: {output_path}")
        return output_path

    async def stream_synthesize_speech(
        self,
        text_generator: AsyncGenerator[str, None],
        voice: str = "alloy",
        model: str = "standard",
        speed: float = 1.0
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream synthesized speech from a text generator.

        Useful for streaming TTS of LLM responses.

        Args:
            text_generator: Async generator yielding text chunks
            voice: Voice to use
            model: TTS model
            speed: Speech speed

        Yields:
            Audio data chunks
        """
        buffer = ""
        sentence_endings = [".", "!", "?", "\n"]

        async for text_chunk in text_generator:
            buffer += text_chunk

            # Check if we have a complete sentence
            for ending in sentence_endings:
                if ending in buffer:
                    # Split at sentence boundary
                    sentences = buffer.split(ending)
                    for sentence in sentences[:-1]:
                        if sentence.strip():
                            # Synthesize sentence
                            audio_data = await self.synthesize_speech(
                                sentence + ending,
                                voice=voice,
                                model=model,
                                speed=speed
                            )
                            yield audio_data

                    # Keep remainder in buffer
                    buffer = sentences[-1]
                    break

        # Synthesize remaining text
        if buffer.strip():
            audio_data = await self.synthesize_speech(
                buffer,
                voice=voice,
                model=model,
                speed=speed
            )
            yield audio_data

    async def create_conversation_audio(
        self,
        conversation: list,
        voice_mapping: Optional[dict] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        Create audio for an entire conversation.

        Args:
            conversation: List of messages with role and content
            voice_mapping: Optional mapping of roles to voices
            output_path: Optional path to save audio file

        Returns:
            Path to created audio file
        """
        if voice_mapping is None:
            voice_mapping = {
                "user": "echo",
                "assistant": "alloy",
                "system": "onyx"
            }

        if output_path is None:
            output_path = str(self.temp_dir / f"conversation_{datetime.utcnow().timestamp()}.mp3")

        # Combine all audio
        all_audio = b""

        for message in conversation:
            role = message.get("role", "assistant")
            content = message.get("content", "")
            voice = voice_mapping.get(role, "alloy")

            # Add role announcement
            announcement = f"{role}: "
            audio_data = await self.synthesize_speech(
                announcement + content,
                voice=voice
            )

            all_audio += audio_data

            # Small silence between messages (optional - would need audio processing library)
            # For now, just concatenate

        # Save combined audio
        async with aiofiles.open(output_path, 'wb') as f:
            await f.write(all_audio)

        logger.info(f"Conversation audio created: {output_path}")
        return output_path

    def get_supported_formats(self) -> list:
        """Get list of supported audio formats for STT."""
        return self.SUPPORTED_FORMATS.copy()

    def get_available_voices(self) -> list:
        """Get list of available TTS voices."""
        return self.TTS_VOICES.copy()

    def cleanup_temp_files(self, older_than_hours: int = 24):
        """
        Clean up temporary audio files older than specified hours.

        Args:
            older_than_hours: Remove files older than this many hours
        """
        import time

        current_time = time.time()
        cutoff_time = current_time - (older_than_hours * 3600)

        removed_count = 0
        for file_path in self.temp_dir.glob("*"):
            if file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    removed_count += 1
                except Exception as e:
                    logger.error(f"Error removing temp file {file_path}: {e}")

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} temporary audio files")


# Global instance
_voice_service = None


def get_voice_service() -> VoiceService:
    """Get or create the global VoiceService instance."""
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService()
    return _voice_service
