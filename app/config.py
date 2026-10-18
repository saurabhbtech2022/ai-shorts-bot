"""Application settings loaded from environment and .env file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
PROMPTS_FILE = DATA_DIR / "prompts.txt"
STATE_FILE = DATA_DIR / "state.json"
MUSIC_DIR = DATA_DIR / "music"
FALLBACK_IMAGES_DIR = DATA_DIR / "fallback_images"
ASSETS_FONTS_DIR = PROJECT_ROOT / "assets" / "fonts"


class Settings(BaseSettings):
    """All configuration for pipeline and FastAPI server."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    yt_client_id: str = Field(default="", alias="YT_CLIENT_ID")
    yt_client_secret: str = Field(default="", alias="YT_CLIENT_SECRET")
    yt_refresh_token: str = Field(default="", alias="YT_REFRESH_TOKEN")

    api_key: str = Field(default="", alias="API_KEY")

    timezone: str = Field(default="Asia/Kolkata", alias="TIMEZONE")
    run_scheduler: bool = Field(default=False, alias="RUN_SCHEDULER")

    upload_time_morning: str = Field(default="08:00", alias="UPLOAD_TIME_MORNING")
    upload_time_afternoon: str = Field(default="13:00", alias="UPLOAD_TIME_AFTERNOON")
    upload_time_evening: str = Field(default="18:00", alias="UPLOAD_TIME_EVENING")
    # Deprecated alias kept for older .env files
    daily_upload_time: str = Field(default="08:00", alias="DAILY_UPLOAD_TIME")

    cf_account_id: str = Field(default="", alias="CF_ACCOUNT_ID")
    cf_api_token: str = Field(default="", alias="CF_API_TOKEN")
    pollinations_api_key: str = Field(default="", alias="POLLINATIONS_API_KEY")
    enable_pollinations: bool = Field(
        default=False,
        alias="ENABLE_POLLINATIONS",
        description="Set true only if you explicitly want Pollinations (off by default)",
    )
    pollinations_free_fallback: bool = Field(
        default=False,
        alias="POLLINATIONS_FREE_FALLBACK",
    )

    scenes_per_run: int = Field(default=1, alias="SCENES_PER_RUN", ge=1, le=10)
    scene_slide_seconds: int = Field(default=15, alias="SCENE_SLIDE_SECONDS", ge=1, le=59)
    slideshow_crossfade_seconds: float = Field(
        default=0.5,
        alias="SLIDESHOW_CROSSFADE_SECONDS",
        ge=0.0,
        le=3.0,
    )
    video_duration: int = Field(default=15, alias="VIDEO_DURATION", ge=1, le=59)
    privacy_status: str = Field(default="public", alias="PRIVACY_STATUS")
    enable_voiceover: bool = Field(default=True, alias="ENABLE_VOICEOVER")
    tts_engine: str = Field(default="edge", alias="TTS_ENGINE")
    tts_voice: str = Field(default="hi-IN-MadhurNeural", alias="TTS_VOICE")
    tts_rate: str = Field(
        default="+5%",
        alias="TTS_RATE",
        description="Edge TTS speaking rate, e.g. -10% slower, +5% faster",
    )
    tts_pitch: str = Field(default="-2Hz", alias="TTS_PITCH")
    tts_fallback_gtts: bool = Field(default=False, alias="TTS_FALLBACK_GTTS")
    enable_text_overlay: bool = Field(default=True, alias="ENABLE_TEXT_OVERLAY")
    enable_part_badge: bool = Field(default=True, alias="ENABLE_PART_BADGE")
    part_badge_corner: str = Field(default="right", alias="PART_BADGE_CORNER")
    enable_subscribe_cta: bool = Field(default=True, alias="ENABLE_SUBSCRIBE_CTA")
    subscribe_cta_seconds: float = Field(default=4.0, alias="SUBSCRIBE_CTA_SECONDS", ge=2.0, le=8.0)
    subscribe_cta_overlay: str = Field(
        default="अगले भाग के लिए सब्सक्राइब करें",
        alias="SUBSCRIBE_CTA_OVERLAY",
    )
    subscribe_cta_overlay_sub: str = Field(
        default="घंटी दबाएँ — नोटिफिकेशन ऑन करें",
        alias="SUBSCRIBE_CTA_OVERLAY_SUB",
    )
    subscribe_cta_voice: str = Field(
        default="चैनल सब्सक्राइब करें, अगला भाग मत चूकिए।",
        alias="SUBSCRIBE_CTA_VOICE",
    )
    image_style_suffix: str = Field(
        default=(
            ", divine, cinematic lighting, highly detailed, "
            "traditional Indian art style, respectful depiction"
        ),
        alias="IMAGE_STYLE_SUFFIX",
    )
    channel_hashtags: str = Field(
        default="#Ramcharitmanas #Ramayan #Shorts #Hindu #Itihas #Tulsidas #AIart",
        alias="CHANNEL_HASHTAGS",
    )

    pollinations_timeout_seconds: float = 180.0
    cloudflare_timeout_seconds: float = 120.0
    youtube_upload_chunksize: int = 1024 * 1024 * 8

    @property
    def youtube_configured(self) -> bool:
        """True when all YouTube OAuth env vars are non-empty."""
        return bool(self.yt_client_id and self.yt_client_secret and self.yt_refresh_token)

    @property
    def cloudflare_configured(self) -> bool:
        """True when Cloudflare Workers AI credentials are set."""
        return bool(self.cf_account_id and self.cf_api_token)

    @property
    def pollinations_enabled(self) -> bool:
        """Pollinations is opt-in only (ENABLE_POLLINATIONS=true)."""
        if not self.enable_pollinations:
            return False
        return self.pollinations_free_fallback or bool(self.pollinations_api_key)


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
