from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


@dataclass(frozen=True)
class Settings:
    groq_api_key: str = field(default_factory=lambda: _env("GROQ_API_KEY"))
    anthropic_api_key: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    deepgram_api_key: str = field(default_factory=lambda: _env("DEEPGRAM_API_KEY"))
    elevenlabs_api_key: str = field(default_factory=lambda: _env("ELEVENLABS_API_KEY"))
    elevenlabs_voice_id: str = field(
        default_factory=lambda: _env("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
    )
    twilio_account_sid: str = field(default_factory=lambda: _env("TWILIO_ACCOUNT_SID"))
    twilio_auth_token: str = field(default_factory=lambda: _env("TWILIO_AUTH_TOKEN"))
    twilio_from_number: str = field(default_factory=lambda: _env("TWILIO_FROM_NUMBER"))

    public_host: str = field(default_factory=lambda: _env("PUBLIC_HOST"))

    model: str = field(
        default_factory=lambda: _env("GROQ_MODEL", _env("ANTHROPIC_MODEL", "openai/gpt-oss-120b"))
    )
    # Voice turns must be quick enough to feel conversational. These are
    # monitoring thresholds, not an attempt to truncate a candidate.
    turn_budget_ms: int = 1500
    silence_reengage_ms: int = 4000

    data_dir: Path = field(
        default_factory=lambda: Path(_env("DATA_DIR", "data")).resolve()
    )

    # PostgreSQL Database configuration
    database_url: str = field(
        default_factory=lambda: _env(
            "DATABASE_URL",
            f"postgresql://{_env('DB_USER', 'postgres')}:{_env('DB_PASSWORD', '')}@{_env('DB_HOST', 'localhost')}:{_env('DB_PORT', '5432')}/{_env('DB_NAME', 'interview')}",
        )
    )
    db_host: str = field(default_factory=lambda: _env("DB_HOST", "localhost"))
    db_port: int = field(default_factory=lambda: int(_env("DB_PORT", "5432")))
    db_name: str = field(default_factory=lambda: _env("DB_NAME", "interview"))
    db_user: str = field(default_factory=lambda: _env("DB_USER", "postgres"))
    db_password: str = field(default_factory=lambda: _env("DB_PASSWORD", ""))

    def missing(self) -> list[str]:
        required = {
            "GROQ_API_KEY": self.groq_api_key or self.anthropic_api_key,
            "DEEPGRAM_API_KEY": self.deepgram_api_key,
            "ELEVENLABS_API_KEY": self.elevenlabs_api_key,
            "TWILIO_ACCOUNT_SID": self.twilio_account_sid,
            "TWILIO_AUTH_TOKEN": self.twilio_auth_token,
            "TWILIO_FROM_NUMBER": self.twilio_from_number,
            "PUBLIC_HOST": self.public_host,
        }
        return [k for k, v in required.items() if not v]

    def missing_for_call(self) -> list[str]:
        """Credentials required once an interview is actually dialled."""
        return self.missing()


settings = Settings()
