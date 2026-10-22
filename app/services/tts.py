"""ElevenLabs Text-to-Speech service."""

import os
from pathlib import Path

from elevenlabs.client import ElevenLabs

from app.config import settings
from app.core.db import BRIEFINGS_DIR

_client: ElevenLabs | None = None


def _get_client() -> ElevenLabs:
    global _client
    if _client is None:
        _client = ElevenLabs(api_key=settings.elevenlabs_api_key)
    return _client


async def text_to_speech(
    text: str,
    output_filename: str,
    voice_id: str | None = None,
) -> str:
    """Convert text to speech and save as MP3.

    Returns the path to the saved audio file.
    """
    client = _get_client()
    vid = voice_id or settings.elevenlabs_voice_id

    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = BRIEFINGS_DIR / output_filename

    # Generate audio
    audio = client.text_to_speech.convert(
        voice_id=vid,
        text=text,
        model_id=settings.elevenlabs_model_id,
        output_format="mp3_44100_128",
    )

    # Write chunks to file
    with open(output_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    return str(output_path)


async def text_to_speech_bytes(
    text: str,
    voice_id: str | None = None,
) -> bytes:
    """Convert text to speech and return raw MP3 bytes.

    Useful for streaming short Q&A answers.
    """
    client = _get_client()
    vid = voice_id or settings.elevenlabs_voice_id

    audio = client.text_to_speech.convert(
        voice_id=vid,
        text=text,
        model_id=settings.elevenlabs_model_id,
        output_format="mp3_44100_128",
    )

    audio_bytes = b""
    for chunk in audio:
        audio_bytes += chunk

    return audio_bytes
