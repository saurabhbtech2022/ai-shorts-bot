"""Natural Hindi voiceover via Edge TTS (primary) with optional gTTS fallback."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from app.config import Settings, get_settings
from app.logger import setup_logging

logger = setup_logging()

DEFAULT_EDGE_VOICE = "hi-IN-MadhurNeural"
# Natural speech should fill most of the Short; never slow-mo-stretch to fake length.
SPEECH_MIN_FILL_RATIO = 0.88
MAX_TTS_EXPANSION_ATTEMPTS = 5


def build_atempo_chain(tempo: float) -> str:
    """
    FFmpeg atempo accepts 0.5–2.0 per filter; chain to reach desired tempo.

    tempo > 1 speeds up (shorter), tempo < 1 slows down (longer).
    """
    filters: list[str] = []
    t = tempo
    while t < 0.5:
        filters.append("atempo=0.5")
        t /= 0.5
    while t > 2.0:
        filters.append("atempo=2.0")
        t /= 2.0
    filters.append(f"atempo={t:.4f}")
    return ",".join(filters)


def _probe_audio_duration(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return 0.0
    try:
        return max(0.0, float(result.stdout.strip()))
    except ValueError:
        return 0.0


def generate_voiceover(
    narration_text: str,
    output_mp3: Path,
    target_duration: float,
    settings: Settings | None = None,
    *,
    expand_text: Callable[[str, int], str] | None = None,
) -> Path | None:
    """
    Generate Hindi MP3 at natural speed; trim/pad to target_duration seconds.

    If speech is shorter than the video, ``expand_text`` may add more lines and
    re-synthesize (never time-stretch slow-mo to fill silence).
    """
    settings = settings or get_settings()
    if not narration_text.strip():
        return None

    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    raw_path = output_mp3.with_suffix(".raw.mp3")

    engine = settings.tts_engine.strip().lower()
    used_engine = ""
    text = narration_text.strip()
    ok = False
    speech_seconds = 0.0
    min_speech = target_duration * SPEECH_MIN_FILL_RATIO

    for attempt in range(MAX_TTS_EXPANSION_ATTEMPTS):
        ok = False
        if engine == "edge":
            ok = _synthesize_edge(text, raw_path, settings)
            if ok:
                used_engine = "edge"
        if not ok and (engine == "gtts" or settings.tts_fallback_gtts):
            ok = _synthesize_gtts(text, raw_path)
            if ok:
                used_engine = "gtts"
        if not ok:
            break

        speech_seconds = _probe_trimmed_speech_duration(raw_path)
        if speech_seconds >= min_speech:
            logger.info(
                "TTS length OK: %.2fs (target %.2fs) after %s attempt(s)",
                speech_seconds,
                target_duration,
                attempt + 1,
            )
            break
        if expand_text is None or attempt + 1 >= MAX_TTS_EXPANSION_ATTEMPTS:
            logger.warning(
                "TTS still short (%.2fs vs %.2fs); using natural speed without slow-mo",
                speech_seconds,
                target_duration,
            )
            break
        text = expand_text(text, attempt)
        logger.info("TTS short (%.2fs); expanding narration (attempt %s)", speech_seconds, attempt + 2)

    if not ok:
        logger.warning("All TTS engines failed; video will have music/silence only")
        return None

    try:
        _normalize_audio_duration(raw_path, output_mp3, target_duration)
        raw_path.unlink(missing_ok=True)
        logger.info("Voiceover saved to %s (engine=%s)", output_mp3, used_engine)
        return output_mp3
    except Exception as exc:
        logger.warning("Voiceover post-process failed: %s", exc)
        if raw_path.exists():
            raw_path.rename(output_mp3)
            return output_mp3
        return None


def _synthesize_edge(text: str, dest: Path, settings: Settings) -> bool:
    try:
        import edge_tts
    except ImportError:
        logger.warning("edge-tts not installed; pip install edge-tts")
        return False

    voice = settings.tts_voice or DEFAULT_EDGE_VOICE
    rate = settings.tts_rate
    pitch = settings.tts_pitch

    async def _run() -> None:
        communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
        await communicate.save(str(dest))

    try:
        asyncio.run(_run())
        if dest.is_file() and dest.stat().st_size > 500:
            logger.info("Edge TTS synthesized with voice=%s rate=%s", voice, rate)
            return True
    except Exception as exc:
        logger.warning("Edge TTS library failed: %s; trying CLI", exc)

    return _synthesize_edge_cli(text, dest, settings)


def _synthesize_edge_cli(text: str, dest: Path, settings: Settings) -> bool:
    binary = shutil.which("edge-tts")
    if not binary:
        venv_bin = Path(__file__).resolve().parent.parent / ".venv" / "bin" / "edge-tts"
        if venv_bin.is_file():
            binary = str(venv_bin)
        else:
            return False

    voice = settings.tts_voice or DEFAULT_EDGE_VOICE
    rate = settings.tts_rate or "+0%"
    cmd = [
        binary,
        f"--voice={voice}",
        f"--rate={rate}",
        "--text",
        text,
        "--write-media",
        str(dest),
    ]
    pitch = (settings.tts_pitch or "").strip()
    if pitch:
        # Use --pitch=-2Hz form; bare "-2Hz" is parsed as a separate CLI flag.
        cmd.append(f"--pitch={pitch}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
        if result.returncode == 0 and dest.is_file() and dest.stat().st_size > 500:
            logger.info("Edge TTS CLI synthesized voice=%s", settings.tts_voice)
            return True
        logger.warning("Edge TTS CLI failed: %s", (result.stderr or result.stdout)[:300])
    except Exception as exc:
        logger.warning("Edge TTS CLI error: %s", exc)
    return False


def _synthesize_gtts(text: str, dest: Path) -> bool:
    try:
        from gtts import gTTS
    except ImportError:
        return False
    try:
        gTTS(text=text, lang="hi").save(str(dest))
        return dest.is_file() and dest.stat().st_size > 500
    except Exception as exc:
        logger.warning("gTTS failed: %s", exc)
        return False


def _trim_silence_af() -> str:
    return (
        "silenceremove="
        "start_periods=1:start_duration=0.05:start_threshold=-45dB:"
        "stop_periods=-1:stop_duration=0.2:stop_threshold=-40dB"
    )


def _probe_trimmed_speech_duration(source: Path) -> float:
    trimmed = source.with_suffix(".probe.mp3")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-af",
        _trim_silence_af(),
        "-c:a",
        "libmp3lame",
        "-q:a",
        "9",
        str(trimmed),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not trimmed.is_file():
        return _probe_audio_duration(source)
    duration = _probe_audio_duration(trimmed)
    trimmed.unlink(missing_ok=True)
    return duration


def _normalize_audio_duration(source: Path, dest: Path, duration: float) -> None:
    """Trim trailing silence; speed up slightly if too long; pad to exact video length."""
    trimmed = dest.with_suffix(".trim.mp3")
    trim_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-af",
        _trim_silence_af(),
        "-c:a",
        "libmp3lame",
        "-q:a",
        "2",
        str(trimmed),
    ]
    trim_result = subprocess.run(trim_cmd, capture_output=True, text=True, check=False)
    if trim_result.returncode != 0 or not trimmed.is_file():
        trimmed = source

    raw_duration = _probe_audio_duration(trimmed)
    parts = ["afade=t=in:st=0:d=0.12"]
    if raw_duration > duration - 0.15:
        tempo = raw_duration / (duration * 0.96)
        if tempo > 1.02:
            parts.append(build_atempo_chain(tempo))
            logger.info(
                "Voice trim: raw=%.2fs max=%.2fs tempo=%.3f (speed up only)",
                raw_duration,
                duration,
                tempo,
            )
    fade_out_start = max(0.0, duration - 0.25)
    parts.extend(
        [
            f"afade=t=out:st={fade_out_start}:d=0.2",
            f"apad=pad_dur={duration}",
            f"atrim=0:{duration}",
        ]
    )
    af = ",".join(parts)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(trimmed),
        "-af",
        af,
        "-t",
        str(duration),
        "-c:a",
        "libmp3lame",
        "-q:a",
        "2",
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if trimmed != source:
        trimmed.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or "ffmpeg audio normalize failed")
