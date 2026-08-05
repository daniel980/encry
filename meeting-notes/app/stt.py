"""Speech-to-text via faster-whisper, with a deterministic offline stub.

Two models are held on CPU: a small one for the 1.5 s partial cadence and
large-v3-turbo for finals. Re-decoding a growing segment with the large model
every 1.5 s does not fit in a CPU budget, and a partial that arrives after the
final is worse than no partial at all. On CUDA the split collapses to a single
turbo model, since one GPU pass is cheaper than keeping two graphs resident.

When the weights cannot be fetched (offline machine, blocked host), the engine
falls back to :class:`StubEngine` so that the surrounding pipeline — buffering,
segmentation, translation, minutes — remains testable. Stub output is clearly
marked as synthetic and must never be mistaken for a transcript.
"""

from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from .config import SttConfig

InferenceMode = Literal["partial", "final"]


@dataclass
class TranscribeResult:
    """One inference pass over a segment of audio."""

    text: str
    language: str = ""
    language_prob: float = 0.0
    duration_s: float = 0.0
    no_speech_prob: float = 0.0
    #: Wall-clock seconds the inference itself took, used by the adaptive pacer.
    latency_s: float = 0.0
    synthetic: bool = False


class SttEngine:
    """Interface implemented by the real and stub engines."""

    name = "stt"
    synthetic = False

    def describe(self) -> str:
        return self.name

    def warmup(self) -> None:
        return None

    def transcribe(self, audio: np.ndarray, mode: InferenceMode) -> TranscribeResult:
        raise NotImplementedError

    def close(self) -> None:
        return None


def _select_device(cfg: SttConfig) -> tuple[str, str]:
    """Resolve ``auto`` device/compute settings against the actual machine."""
    device = cfg.device
    if device == "auto":
        device = "cpu"
        try:
            import ctranslate2  # noqa: PLC0415

            if ctranslate2.get_cuda_device_count() > 0:
                device = "cuda"
        except Exception:
            device = "cpu"

    compute = cfg.compute_type
    if compute == "auto":
        compute = "float16" if device == "cuda" else "int8"
    return device, compute


class WhisperEngine(SttEngine):
    """faster-whisper wrapper holding one or two models."""

    name = "faster-whisper"

    def __init__(self, cfg: SttConfig) -> None:
        self.cfg = cfg
        self.device, self.compute_type = _select_device(cfg)
        # A single GPU model serves both modes; CPU splits the work by size.
        self.single_model = self.device == "cuda"
        self._models: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._load(cfg.final_model)
        if not self.single_model and cfg.partial_model != cfg.final_model:
            self._load(cfg.partial_model)

    def _load(self, model_name: str) -> Any:
        from faster_whisper import WhisperModel  # noqa: PLC0415

        if model_name in self._models:
            return self._models[model_name]
        self.cfg.model_dir.mkdir(parents=True, exist_ok=True)
        model = WhisperModel(
            model_name,
            device=self.device,
            compute_type=self.compute_type,
            download_root=str(self.cfg.model_dir),
            num_workers=1,
        )
        self._models[model_name] = model
        return model

    def _model_for(self, mode: InferenceMode) -> Any:
        if self.single_model or mode == "final":
            return self._models[self.cfg.final_model]
        return self._models.get(self.cfg.partial_model, self._models[self.cfg.final_model])

    def describe(self) -> str:
        if self.single_model:
            return f"faster-whisper {self.cfg.final_model} ({self.device}/{self.compute_type})"
        return (
            f"faster-whisper {self.cfg.partial_model}+{self.cfg.final_model} "
            f"({self.device}/{self.compute_type})"
        )

    def warmup(self) -> None:
        """Force graph allocation so the first real utterance is not slow."""
        silence = np.zeros(16_000, dtype=np.float32)
        for mode in ("partial", "final"):
            try:
                self.transcribe(silence, mode)  # type: ignore[arg-type]
            except Exception:
                pass

    def transcribe(self, audio: np.ndarray, mode: InferenceMode) -> TranscribeResult:
        started = time.monotonic()
        model = self._model_for(mode)
        audio = np.asarray(audio, dtype=np.float32).reshape(-1)

        # Partials favour latency: greedy, no extra passes. Finals favour quality.
        options: dict[str, Any] = {
            "beam_size": 1 if mode == "partial" else max(1, self.cfg.beam_size),
            "vad_filter": False,  # silero already gated this audio
            "condition_on_previous_text": False,  # avoids repetition loops
            "no_speech_threshold": self.cfg.no_speech_threshold,
        }
        if self.cfg.language:
            options["language"] = self.cfg.language
        if mode == "partial":
            options["temperature"] = 0.0
            options["without_timestamps"] = True

        with self._lock:
            segments, info = model.transcribe(audio, **options)
            parts: list[str] = []
            no_speech = 0.0
            for seg in segments:
                parts.append(seg.text)
                no_speech = max(no_speech, float(getattr(seg, "no_speech_prob", 0.0) or 0.0))

        return TranscribeResult(
            text="".join(parts).strip(),
            language=str(getattr(info, "language", "") or ""),
            language_prob=float(getattr(info, "language_probability", 0.0) or 0.0),
            duration_s=audio.size / 16_000.0,
            no_speech_prob=no_speech,
            latency_s=time.monotonic() - started,
        )


#: Scripted utterances used only by the stub, alternating Korean and English so
#: the bilingual display and minutes rules can be exercised without a mic.
_STUB_SCRIPT: list[tuple[str, str]] = [
    ("ko", "지난주에 논의한 DPU 텔레메트리 경로부터 정리하고 시작하겠습니다."),
    ("en", "We should finalize the DPU telemetry path before the next sprint."),
    ("ko", "수집 주기는 일단 10초로 두고, 부하를 보고 조정하는 게 좋겠습니다."),
    ("en", "I can take the collector side and have a draft ready by Thursday."),
    ("ko", "그러면 대시보드 쪽은 제가 맡아서 다음 주 화요일까지 초안을 만들겠습니다."),
    ("en", "One open question is whether we keep the legacy agent running in parallel."),
    ("ko", "레거시 에이전트는 아직 결론이 안 났으니 다음 회의에서 다시 보시죠."),
    ("en", "Let's also confirm the storage budget with the platform team."),
    ("ko", "스토리지 예산은 플랫폼 팀 확인 후에 확정하는 것으로 하겠습니다."),
    ("en", "Agreed. I will send the summary to the mailing list today."),
]


class StubEngine(SttEngine):
    """Deterministic offline stand-in for Whisper.

    Output is derived from the audio's length and energy, so the same input
    always yields the same text. This exists to exercise the pipeline where the
    real weights are unavailable; every result is flagged ``synthetic`` and the
    UI labels it, because synthetic text must never read as a real transcript.
    """

    name = "stub"
    synthetic = True

    def __init__(self, reason: str = "") -> None:
        self.reason = reason

    def describe(self) -> str:
        return f"stub (합성 텍스트 — 실제 전사 아님){f': {self.reason}' if self.reason else ''}"

    def transcribe(self, audio: np.ndarray, mode: InferenceMode) -> TranscribeResult:
        started = time.monotonic()
        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
        duration = audio.size / 16_000.0
        rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64)))) if audio.size else 0.0

        if rms < 1e-4:
            return TranscribeResult(
                text="", duration_s=duration, no_speech_prob=1.0, synthetic=True,
                latency_s=time.monotonic() - started,
            )

        digest = hashlib.sha1(
            f"{audio.size}:{round(rms, 4)}".encode(), usedforsecurity=False
        ).digest()
        lang, sentence = _STUB_SCRIPT[digest[0] % len(_STUB_SCRIPT)]

        if mode == "partial":
            # Reveal the sentence progressively so partial rendering is visible.
            words = sentence.split()
            take = max(1, min(len(words), int(duration / 0.6)))
            sentence = " ".join(words[:take])

        # Emulate real inference cost so the adaptive pacer sees plausible timing.
        time.sleep(min(0.12, duration * (0.03 if mode == "partial" else 0.06)))
        return TranscribeResult(
            text=sentence,
            language=lang,
            language_prob=0.95,
            duration_s=duration,
            no_speech_prob=0.02,
            latency_s=time.monotonic() - started,
            synthetic=True,
        )


def create_engine(cfg: SttConfig) -> tuple[SttEngine, str]:
    """Build the best available engine.

    Returns the engine and a human-readable notice describing any degradation,
    which the server forwards to the UI status bar.
    """
    try:
        engine = WhisperEngine(cfg)
        return engine, ""
    except Exception as exc:
        reason = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
        if not cfg.allow_stub:
            raise
        notice = (
            f"Whisper 모델을 불러오지 못해 합성(stub) 엔진으로 동작합니다. "
            f"표시되는 문장은 실제 전사가 아닙니다. 원인: {reason}"
        )
        return StubEngine(reason), notice
