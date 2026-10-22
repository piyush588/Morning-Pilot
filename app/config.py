"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """All config via .env or environment variables."""

    # TinyFish
    tinyfish_api_key: str = Field(default="", description="TinyFish API key")

    # ElevenLabs
    elevenlabs_api_key: str = Field(default="", description="ElevenLabs API key")
    elevenlabs_voice_id: str = Field(
        default="JBFqnCBsd6RMkjVDRZzb", description="Default voice for briefings"
    )
    elevenlabs_model_id: str = Field(
        default="eleven_multilingual_v2", description="ElevenLabs TTS model"
    )

    # LLM
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="LLM model name")
    openai_base_url: str | None = Field(default=None, description="Custom OpenAI-compatible base URL")
    ollama_base_url: str = Field(
        default="http://localhost:11434/v1", description="Local Ollama base URL"
    )
    ollama_model: str = Field(default="llama3.2:3b", description="Local Ollama model name")

    # App
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    briefing_schedule_hour: int = Field(default=7)
    briefing_max_stories: int = Field(default=5)
    briefing_max_duration: int = Field(default=300)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def effective_port(self) -> int:
        import os
        return int(os.environ.get("PORT", self.app_port))


settings = Settings()
