"""ElevenLabs Speech-to-Text service."""

from io import BytesIO

from elevenlabs.client import ElevenLabs

from app.config import settings

_client: ElevenLabs | None = None


def _get_client() -> ElevenLabs:
    global _client
    if _client is None:
        _client = ElevenLabs(api_key=settings.elevenlabs_api_key)
    return _client


async def speech_to_text(audio_bytes: bytes) -> str:
    """Transcribe audio bytes to text using ElevenLabs Scribe.

    Accepts raw audio bytes (wav, mp3, webm).
    Returns the transcribed text string.
    """
    client = _get_client()

    audio_file = BytesIO(audio_bytes)
    audio_file.name = "recording.webm"

    transcription = client.speech_to_text.convert(
        file=audio_file,
        model_id="scribe_v2",
    )

    # The SDK returns an object with a .text attribute
    if hasattr(transcription, "text"):
        return transcription.text
    # Fallback: might be a dict
    if isinstance(transcription, dict):
        return transcription.get("text", str(transcription))
    return str(transcription)
