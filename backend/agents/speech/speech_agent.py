"""
Speech Agent - Speech-to-Text (STT) and Text-to-Speech (TTS)
"""

from typing import Dict, Any, Optional
from loguru import logger
import io
import tempfile
from pathlib import Path
import base64

from backend.agents.base import BaseAgent


class SpeechAgent(BaseAgent):
    """
    Specialized agent for speech processing
    - Speech-to-Text using OpenAI Whisper
    - Text-to-Speech using OpenAI TTS
    - Voice commands processing
    - Audio transcription
    """

    def __init__(self, memory_manager=None):
        super().__init__(
            name="Speech",
            description="Transkrypcja mowy na tekst i synteza głosu",
            memory_manager=memory_manager
        )

        # Supported audio formats
        self.supported_formats = [
            'mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm', 'ogg'
        ]

    async def process(
        self,
        user_id: str,
        message: str,
        context: Dict[str, Any],
        metadata: Optional[Dict] = None
    ) -> str:
        """Process speech-related requests"""

        logger.info(f"Speech Agent processing for {user_id}")

        # Determine if this is STT or TTS request
        processing_type = await self._determine_processing_type(message, metadata)

        try:
            if processing_type == "stt":
                # Speech-to-Text
                if not metadata or "audio" not in metadata:
                    return "🎤 Aby przetworzyć mowę na tekst, prześlij plik audio!"

                audio_data = metadata.get("audio")
                return await self._speech_to_text(audio_data, message, metadata)

            elif processing_type == "tts":
                # Text-to-Speech
                text_to_speak = await self._extract_text_to_speak(message)
                return await self._text_to_speech(text_to_speak, metadata)

            else:
                return "🎙️ Mogę pomóc z:\n- 🎤 Transkrypcją audio na tekst\n- 🔊 Syntezą mowy z tekstu\n\nWyślij audio lub poproś o przeczytanie tekstu!"

        except Exception as e:
            logger.error(f"Speech processing error: {e}")
            return f"❌ Wystąpił błąd podczas przetwarzania audio: {str(e)}"

    async def _determine_processing_type(
        self,
        message: str,
        metadata: Optional[Dict]
    ) -> str:
        """Determine if this is STT or TTS request"""

        # If audio data provided, it's STT
        if metadata and "audio" in metadata:
            return "stt"

        message_lower = message.lower()

        # TTS keywords
        if any(word in message_lower for word in [
            "przeczytaj", "powiedz", "nagraj", "wypowiedz",
            "read aloud", "speak", "say", "voice"
        ]):
            return "tts"

        # STT keywords
        if any(word in message_lower for word in [
            "transkrypcja", "co mówię", "zapisz to", "speech to text",
            "transcribe", "what did i say"
        ]):
            return "stt"

        return "unknown"

    async def _speech_to_text(
        self,
        audio_data: Any,
        message: str,
        metadata: Dict
    ) -> str:
        """Convert speech to text using Whisper"""

        try:
            from backend.shared.config.settings import settings
            import openai

            # Initialize OpenAI client
            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            # Prepare audio file
            audio_file = await self._prepare_audio_file(audio_data, metadata)

            # Get language hint if provided
            language = metadata.get("language", "pl")  # Default to Polish

            # Transcribe using Whisper
            logger.info(f"Transcribing audio with Whisper (language: {language})")

            with open(audio_file, "rb") as f:
                transcript = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language=language if language != "auto" else None,
                    response_format="verbose_json"
                )

            # Clean up temp file
            Path(audio_file).unlink(missing_ok=True)

            # Extract transcription
            transcribed_text = transcript.text

            if not transcribed_text.strip():
                return "🎤 Nie wykryto mowy w nagraniu. Spróbuj ponownie!"

            # If user asked a question about the audio, answer it
            if message and len(message) > 10:
                system_prompt = """
Użytkownik wysłał nagranie audio, które zostało transkrybowane.
Odpowiedz na jego pytanie dotyczące tego nagrania.

Bądź pomocny i naturalny.
"""
                llm_response = await self._call_llm(
                    prompt=f"Pytanie: {message}\n\nTranskrypcja: {transcribed_text}",
                    system_prompt=system_prompt
                )

                return f"🎤 **Transkrypcja:**\n{transcribed_text}\n\n---\n\n{llm_response}"

            else:
                # Just return transcription
                return f"🎤 **Transkrypcja:**\n\n{transcribed_text}"

        except Exception as e:
            logger.error(f"STT error: {e}")
            return f"❌ Błąd transkrypcji: {str(e)}"

    async def _text_to_speech(self, text: str, metadata: Optional[Dict] = None) -> str:
        """Convert text to speech using OpenAI TTS"""

        try:
            from backend.shared.config.settings import settings
            import openai

            # Initialize OpenAI client
            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            # Get voice preference (default: alloy)
            voice = metadata.get("voice", "alloy") if metadata else "alloy"
            # Available voices: alloy, echo, fable, onyx, nova, shimmer

            # Get model preference
            model = metadata.get("tts_model", "tts-1") if metadata else "tts-1"
            # tts-1 is faster, tts-1-hd is higher quality

            logger.info(f"Generating speech with TTS (voice: {voice}, model: {model})")

            # Generate speech
            response = await client.audio.speech.create(
                model=model,
                voice=voice,
                input=text[:4096]  # Max 4096 chars
            )

            # Convert to base64 for transmission
            audio_bytes = response.content
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

            # Return audio data in metadata
            return {
                "text": f"🔊 **Wygenerowano mowę:** {len(text)} znaków",
                "audio_base64": audio_base64,
                "audio_format": "mp3",
                "voice": voice
            }

        except Exception as e:
            logger.error(f"TTS error: {e}")
            return f"❌ Błąd syntezy mowy: {str(e)}"

    async def _prepare_audio_file(
        self,
        audio_data: Any,
        metadata: Dict
    ) -> str:
        """Prepare audio file for Whisper API"""

        # Create temp file
        audio_format = metadata.get("audio_format", "mp3")

        if audio_format not in self.supported_formats:
            audio_format = "mp3"

        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=f".{audio_format}"
        )

        try:
            if isinstance(audio_data, str):
                # Base64 encoded
                if audio_data.startswith('data:audio'):
                    audio_data = audio_data.split(',')[1]

                audio_bytes = base64.b64decode(audio_data)
                temp_file.write(audio_bytes)

            elif isinstance(audio_data, bytes):
                temp_file.write(audio_data)

            else:
                raise ValueError(f"Unsupported audio data type: {type(audio_data)}")

            temp_file.flush()
            return temp_file.name

        finally:
            temp_file.close()

    async def _extract_text_to_speak(self, message: str) -> str:
        """Extract text that should be spoken from user message"""

        message_lower = message.lower()

        # Remove common TTS trigger phrases
        triggers = [
            "przeczytaj", "powiedz", "nagraj", "wypowiedz",
            "read aloud", "speak", "say"
        ]

        for trigger in triggers:
            if trigger in message_lower:
                # Remove trigger and extract text
                parts = message_lower.split(trigger, 1)
                if len(parts) > 1:
                    return parts[1].strip(' :"\'')

        return message

    async def transcribe_file(self, file_path: str, language: str = "pl") -> str:
        """
        Utility method to transcribe audio file directly
        """
        with open(file_path, "rb") as f:
            audio_bytes = f.read()

        metadata = {
            "audio_format": Path(file_path).suffix[1:],  # Remove dot
            "language": language
        }

        result = await self._speech_to_text(audio_bytes, "", metadata)
        return result

    async def can_handle(self, message: str, context: Dict) -> float:
        """Check if this agent should handle the message"""

        speech_keywords = [
            "audio", "mowa", "głos", "nagranie", "nagraj",
            "transkrypcja", "przeczytaj", "powiedz",
            "speech", "voice", "transcribe", "say", "speak"
        ]

        message_lower = message.lower()
        matches = sum(1 for keyword in speech_keywords if keyword in message_lower)

        # High confidence if metadata contains audio
        if context.get("has_audio"):
            return 0.9

        return min(matches * 0.3, 0.8)
