"""
Voice Processing API Endpoints (STT & TTS)
"""

import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import Response, StreamingResponse
import io

from backend.services.voice_service import get_voice_service
from backend.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    temperature: float = Form(0.0),
    user = Depends(get_current_user)
):
    """
    Transcribe audio to text using Whisper STT.

    - **file**: Audio file (mp3, wav, m4a, etc.)
    - **language**: ISO-639-1 language code (e.g., 'en', 'pl')
    - **prompt**: Optional prompt to guide transcription
    - **temperature**: Sampling temperature (0-1)
    """
    voice_service = get_voice_service()
    user_id = user["user_id"]

    try:
        # Validate file format
        filename = file.filename.lower()
        supported_formats = voice_service.get_supported_formats()

        if not any(filename.endswith(fmt) for fmt in supported_formats):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format. Supported: {supported_formats}"
            )

        # Read file
        contents = await file.read()

        # Create file-like object
        audio_file = io.BytesIO(contents)
        audio_file.name = file.filename

        # Transcribe
        result = await voice_service.transcribe_audio(
            audio_file=audio_file,
            language=language,
            prompt=prompt,
            temperature=temperature
        )

        logger.info(
            f"Audio transcribed: user={user_id}, "
            f"duration={result.get('duration')}s, "
            f"text_length={len(result['text'])}"
        )

        return {
            "text": result["text"],
            "language": result.get("language"),
            "duration": result.get("duration"),
            "processing_time": result.get("processing_time"),
            "model": result.get("model")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/synthesize")
async def synthesize_speech(
    text: str = Form(..., min_length=1, max_length=4096),
    voice: str = Form("alloy"),
    model: str = Form("standard"),
    speed: float = Form(1.0),
    response_format: str = Form("mp3"),
    user = Depends(get_current_user)
):
    """
    Synthesize speech from text using OpenAI TTS.

    - **text**: Text to synthesize (max 4096 characters)
    - **voice**: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
    - **model**: TTS model (standard or hd)
    - **speed**: Speech speed (0.25 - 4.0)
    - **response_format**: Audio format (mp3, opus, aac, flac)
    """
    voice_service = get_voice_service()
    user_id = user["user_id"]

    try:
        # Validate voice
        available_voices = voice_service.get_available_voices()
        if voice not in available_voices:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid voice. Available: {available_voices}"
            )

        # Validate speed
        if not 0.25 <= speed <= 4.0:
            raise HTTPException(
                status_code=400,
                detail="Speed must be between 0.25 and 4.0"
            )

        # Synthesize
        audio_data = await voice_service.synthesize_speech(
            text=text,
            voice=voice,
            model=model,
            speed=speed,
            response_format=response_format
        )

        logger.info(
            f"Speech synthesized: user={user_id}, "
            f"text_length={len(text)}, voice={voice}, "
            f"audio_size={len(audio_data)} bytes"
        )

        # Return audio file
        media_type = {
            "mp3": "audio/mpeg",
            "opus": "audio/opus",
            "aac": "audio/aac",
            "flac": "audio/flac"
        }.get(response_format, "audio/mpeg")

        return Response(
            content=audio_data,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="speech.{response_format}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Speech synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voices")
async def get_available_voices():
    """Get list of available TTS voices."""
    voice_service = get_voice_service()

    voices = voice_service.get_available_voices()

    return {
        "voices": [
            {
                "id": voice,
                "name": voice.capitalize(),
                "description": {
                    "alloy": "Neutral and balanced",
                    "echo": "Clear and professional",
                    "fable": "Warm and expressive",
                    "onyx": "Deep and authoritative",
                    "nova": "Energetic and youthful",
                    "shimmer": "Soft and friendly"
                }.get(voice, "")
            }
            for voice in voices
        ],
        "models": [
            {
                "id": "standard",
                "name": "Standard Quality",
                "description": "Faster, good quality"
            },
            {
                "id": "hd",
                "name": "HD Quality",
                "description": "Higher quality, slower"
            }
        ]
    }


@router.get("/supported-formats")
async def get_supported_audio_formats():
    """Get list of supported audio formats for STT."""
    voice_service = get_voice_service()

    return {
        "formats": voice_service.get_supported_formats(),
        "description": "Supported audio formats for speech-to-text"
    }
