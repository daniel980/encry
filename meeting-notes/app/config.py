"""Central configuration.

Every tunable lives here and is overridable through environment variables or a
``.env`` file, so no path, key, or threshold is hardcoded at its point of use.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Populate ``os.environ`` from a .env file without overriding real env vars."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _env_str(key: str, default: str) -> str:
    value = os.environ.get(key, "").strip()
    return value or default


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, "").strip() or default)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, "").strip() or default)
    except ValueError:
        return default


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AudioConfig:
    """Capture and buffering parameters."""

    sample_rate: int = 16_000
    #: 512 samples @ 16 kHz = 32 ms, the frame size silero-vad requires.
    block_size: int = 512
    #: Hard upper bound on buffered audio per stream. Fixes memory for long meetings.
    ring_seconds: float = 30.0

    @property
    def block_ms(self) -> float:
        return 1000.0 * self.block_size / self.sample_rate

    @property
    def ring_samples(self) -> int:
        return int(self.ring_seconds * self.sample_rate)


@dataclass(frozen=True)
class VadConfig:
    """Speech detection and segment boundary rules."""

    speech_threshold: float = 0.5
    #: Lower threshold for leaving speech: hysteresis stops boundary chatter.
    silence_threshold: float = 0.35
    onset_frames: int = 3
    preroll_ms: float = 300.0
    silence_ms: float = 700.0
    max_segment_s: float = 25.0
    min_segment_ms: float = 300.0
    partial_interval_s: float = 1.5
    #: Upper bound the adaptive backoff may stretch the partial interval to.
    partial_interval_max_s: float = 3.0


@dataclass(frozen=True)
class SttConfig:
    """Whisper model selection and inference behaviour."""

    final_model: str = "large-v3-turbo"
    #: Smaller model used for partials on CPU, where re-decoding with the large
    #: model cannot keep up with a 1.5 s cadence.
    partial_model: str = "small"
    device: str = "auto"
    compute_type: str = "auto"
    beam_size: int = 1
    #: Whisper hallucinates confident text on silence; drop segments below this.
    no_speech_threshold: float = 0.6
    language: str = ""  # empty = autodetect
    model_dir: Path = BASE_DIR / "data" / "models"
    #: Below this detection probability the segment inherits the previous language.
    lang_prob_floor: float = 0.6
    lang_min_duration_s: float = 1.0
    allow_stub: bool = True


@dataclass(frozen=True)
class LlmConfig:
    """Anthropic API settings for translation and minutes."""

    api_key: str = ""
    model: str = "claude-sonnet-5"
    translate_model: str = ""  # empty = same as `model`
    max_batch: int = 5
    min_batch: int = 3
    batch_linger_s: float = 2.0
    max_retries: int = 6
    timeout_s: float = 60.0
    #: When true, no text ever leaves the machine; translation and minutes are off.
    local_only: bool = False

    @property
    def enabled(self) -> bool:
        return bool(self.api_key) and not self.local_only

    @property
    def translation_model(self) -> str:
        return self.translate_model or self.model


@dataclass(frozen=True)
class LanguageConfig:
    """Bilingual display rules."""

    #: Latin-character share above which a segment is treated as code-switched
    #: and gets the bilingual treatment even when Whisper reports Korean.
    en_ratio_threshold: float = 0.3
    #: Latin runs this short (e.g. "AI", "PR") are ignored by the ratio so that
    #: loanwords and acronyms inside Korean sentences do not trip the threshold.
    min_latin_token_len: int = 3


@dataclass(frozen=True)
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8420
    open_browser: bool = True


@dataclass(frozen=True)
class MinutesConfig:
    live_summary_interval_s: float = 300.0
    live_summary_min_segments: int = 4


@dataclass(frozen=True)
class Config:
    """Root configuration object passed down through the app."""

    audio: AudioConfig = field(default_factory=AudioConfig)
    vad: VadConfig = field(default_factory=VadConfig)
    stt: SttConfig = field(default_factory=SttConfig)
    llm: LlmConfig = field(default_factory=LlmConfig)
    lang: LanguageConfig = field(default_factory=LanguageConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    minutes: MinutesConfig = field(default_factory=MinutesConfig)
    base_dir: Path = BASE_DIR
    db_path: Path = BASE_DIR / "data" / "sessions.db"
    export_dir: Path = BASE_DIR / "data" / "exports"
    web_dir: Path = BASE_DIR / "web"


def load_config(env_file: Path | None = None) -> Config:
    """Build a :class:`Config` from the environment and an optional .env file."""
    _load_dotenv(env_file or (BASE_DIR / ".env"))

    data_dir = Path(_env_str("DATA_DIR", str(BASE_DIR / "data"))).expanduser()

    return Config(
        audio=AudioConfig(
            sample_rate=_env_int("SAMPLE_RATE", 16_000),
            block_size=_env_int("BLOCK_SIZE", 512),
            ring_seconds=_env_float("RING_SECONDS", 30.0),
        ),
        vad=VadConfig(
            speech_threshold=_env_float("VAD_SPEECH_THRESHOLD", 0.5),
            silence_threshold=_env_float("VAD_SILENCE_THRESHOLD", 0.35),
            onset_frames=_env_int("VAD_ONSET_FRAMES", 3),
            preroll_ms=_env_float("VAD_PREROLL_MS", 300.0),
            silence_ms=_env_float("VAD_SILENCE_MS", 700.0),
            max_segment_s=_env_float("VAD_MAX_SEGMENT_S", 25.0),
            min_segment_ms=_env_float("VAD_MIN_SEGMENT_MS", 300.0),
            partial_interval_s=_env_float("PARTIAL_INTERVAL_S", 1.5),
            partial_interval_max_s=_env_float("PARTIAL_INTERVAL_MAX_S", 3.0),
        ),
        stt=SttConfig(
            final_model=_env_str("WHISPER_MODEL_FINAL", "large-v3-turbo"),
            partial_model=_env_str("WHISPER_MODEL_PARTIAL", "small"),
            device=_env_str("WHISPER_DEVICE", "auto"),
            compute_type=_env_str("WHISPER_COMPUTE_TYPE", "auto"),
            beam_size=_env_int("WHISPER_BEAM_SIZE", 1),
            no_speech_threshold=_env_float("WHISPER_NO_SPEECH_THRESHOLD", 0.6),
            language=_env_str("WHISPER_LANGUAGE", ""),
            model_dir=Path(_env_str("WHISPER_MODEL_DIR", str(data_dir / "models"))),
            lang_prob_floor=_env_float("LANG_PROB_FLOOR", 0.6),
            lang_min_duration_s=_env_float("LANG_MIN_DURATION_S", 1.0),
            allow_stub=_env_bool("ALLOW_STUB_STT", True),
        ),
        llm=LlmConfig(
            api_key=_env_str("ANTHROPIC_API_KEY", ""),
            model=_env_str("ANTHROPIC_MODEL", "claude-sonnet-5"),
            translate_model=_env_str("ANTHROPIC_TRANSLATE_MODEL", ""),
            max_batch=_env_int("TRANSLATE_MAX_BATCH", 5),
            min_batch=_env_int("TRANSLATE_MIN_BATCH", 3),
            batch_linger_s=_env_float("TRANSLATE_BATCH_LINGER_S", 2.0),
            max_retries=_env_int("TRANSLATE_MAX_RETRIES", 6),
            timeout_s=_env_float("LLM_TIMEOUT_S", 60.0),
            local_only=_env_bool("LOCAL_ONLY", False),
        ),
        lang=LanguageConfig(
            en_ratio_threshold=_env_float("EN_RATIO_THRESHOLD", 0.3),
            min_latin_token_len=_env_int("MIN_LATIN_TOKEN_LEN", 3),
        ),
        server=ServerConfig(
            host=_env_str("HOST", "127.0.0.1"),
            port=_env_int("PORT", 8420),
            open_browser=_env_bool("OPEN_BROWSER", True),
        ),
        minutes=MinutesConfig(
            live_summary_interval_s=_env_float("LIVE_SUMMARY_INTERVAL_S", 300.0),
            live_summary_min_segments=_env_int("LIVE_SUMMARY_MIN_SEGMENTS", 4),
        ),
        base_dir=BASE_DIR,
        db_path=Path(_env_str("DB_PATH", str(data_dir / "sessions.db"))),
        export_dir=Path(_env_str("EXPORT_DIR", str(data_dir / "exports"))),
        web_dir=BASE_DIR / "web",
    )
