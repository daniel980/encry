"""Voice activity detection and segment boundary decisions.

silero-vad is loaded through onnxruntime rather than torch: the pip wheel ships
the ONNX weights, so this avoids a ~200 MB torch dependency and starts faster.
The model signature differs across silero v4/v5/v6, so inputs are introspected
at load time instead of hardcoded.

The boundary state machine is deliberately hysteretic — speech starts on a
higher threshold than it ends on — because a single threshold makes segment
edges chatter on breath and room tone.
"""

from __future__ import annotations

import collections
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np

from .config import VadConfig

SegmentReason = Literal["silence", "max_length", "flush"]


class SpeechDetector:
    """Frame-level speech probability. Falls back to energy gating if needed."""

    def __init__(self, sample_rate: int = 16_000) -> None:
        self.sample_rate = sample_rate
        self.backend = "none"
        self.load_error = ""
        self._session: Any = None
        self._state: np.ndarray | None = None
        self._input_names: list[str] = []
        self._state_name = ""
        self._sr_name = ""
        self._context = np.zeros(0, dtype=np.float32)
        self._context_size = 64 if sample_rate == 16_000 else 32
        self._noise_floor = 1e-3
        self._load()

    def _model_path(self) -> Path | None:
        try:
            import silero_vad  # noqa: PLC0415
        except Exception as exc:
            self.load_error = f"silero-vad 패키지를 불러올 수 없습니다: {exc}"
            return None
        data_dir = Path(silero_vad.__file__).resolve().parent / "data"
        # Prefer the 16 kHz-specific graph; fall back to the general one.
        for name in ("silero_vad_16k_op15.onnx", "silero_vad.onnx"):
            candidate = data_dir / name
            if candidate.is_file():
                return candidate
        self.load_error = f"silero ONNX 가중치를 찾을 수 없습니다 ({data_dir})"
        return None

    def _load(self) -> None:
        path = self._model_path()
        if path is None:
            self.backend = "energy"
            return
        try:
            import onnxruntime as ort  # noqa: PLC0415

            opts = ort.SessionOptions()
            # One thread: VAD runs per stream and must not fight the STT worker
            # for cores. A single frame is 32 ms of audio — it does not need more.
            opts.inter_op_num_threads = 1
            opts.intra_op_num_threads = 1
            opts.log_severity_level = 3
            self._session = ort.InferenceSession(
                str(path), sess_options=opts, providers=["CPUExecutionProvider"]
            )
        except Exception as exc:
            self.load_error = f"onnxruntime 초기화 실패: {exc}"
            self.backend = "energy"
            return

        self._input_names = [i.name for i in self._session.get_inputs()]
        for name in self._input_names:
            lowered = name.lower()
            if lowered in {"state", "h", "c", "hn", "cn"} or "state" in lowered:
                self._state_name = name
            elif lowered in {"sr", "samplerate", "sample_rate"}:
                self._sr_name = name
        self.backend = f"silero-onnx ({path.name})"
        self.reset()

    def reset(self) -> None:
        """Clear recurrent state. Call between independent audio streams."""
        self._context = np.zeros(0, dtype=np.float32)
        if self._session is None or not self._state_name:
            self._state = None
            return
        shape = next(i.shape for i in self._session.get_inputs() if i.name == self._state_name)
        dims = [d if isinstance(d, int) and d > 0 else 1 for d in shape]
        self._state = np.zeros(dims, dtype=np.float32)

    def _energy_probability(self, frame: np.ndarray) -> float:
        rms = float(np.sqrt(np.mean(np.square(frame, dtype=np.float64))) + 1e-12)
        # Slow-rising / fast-falling noise floor tracker.
        if rms < self._noise_floor:
            self._noise_floor = 0.9 * self._noise_floor + 0.1 * rms
        else:
            self._noise_floor = 0.999 * self._noise_floor + 0.001 * rms
        ratio = rms / max(self._noise_floor, 1e-6)
        return float(np.clip((ratio - 2.0) / 6.0, 0.0, 1.0))

    def probability(self, frame: np.ndarray) -> float:
        """Probability that ``frame`` (one block of float32 mono) contains speech."""
        frame = np.asarray(frame, dtype=np.float32).reshape(-1)
        if self._session is None:
            return self._energy_probability(frame)

        try:
            # silero v5+ expects the previous frames' tail prepended as context.
            if self._context.size != self._context_size:
                self._context = np.zeros(self._context_size, dtype=np.float32)
            windowed = np.concatenate((self._context, frame))
            self._context = frame[-self._context_size :].copy()

            feed: dict[str, Any] = {}
            for name in self._input_names:
                if name == self._state_name:
                    feed[name] = self._state
                elif name == self._sr_name:
                    feed[name] = np.array(self.sample_rate, dtype=np.int64)
                else:
                    feed[name] = windowed.reshape(1, -1)

            outputs = self._session.run(None, feed)
            prob = float(np.asarray(outputs[0]).reshape(-1)[0])
            if len(outputs) > 1 and self._state_name:
                self._state = np.asarray(outputs[-1], dtype=np.float32)
            return prob
        except Exception as exc:
            # Never let a model hiccup take the pipeline down — degrade to energy.
            self.load_error = f"silero 추론 실패, 에너지 기반으로 전환: {exc}"
            self._session = None
            self.backend = "energy"
            return self._energy_probability(frame)


@dataclass
class PendingSegment:
    """Audio accumulated for the utterance currently being spoken."""

    frames: list[np.ndarray] = field(default_factory=list)
    start_sample: int = 0
    sample_count: int = 0

    def add(self, frame: np.ndarray) -> None:
        self.frames.append(frame)
        self.sample_count += frame.size

    def audio(self) -> np.ndarray:
        if not self.frames:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(self.frames)

    def clear(self) -> None:
        self.frames.clear()
        self.sample_count = 0


@dataclass
class VadEvent:
    """Something the boundary detector wants the pipeline to act on."""

    kind: Literal["partial", "final", "speech_start"]
    audio: np.ndarray
    start_ms: int
    end_ms: int
    reason: SegmentReason | None = None


class SegmentBoundaryDetector:
    """Turns a stream of frames into partial ticks and finalized segments.

    Rules (all tunable in :class:`~app.config.VadConfig`):

    * speech starts after ``onset_frames`` consecutive frames above the speech
      threshold, with ``preroll_ms`` of prior audio prepended so the first
      syllable is not clipped;
    * a partial is emitted every ``partial_interval_s`` of ongoing speech;
    * the segment finalizes after ``silence_ms`` below the silence threshold, or
      immediately at ``max_segment_s`` — in which case the next segment picks up
      without waiting for silence;
    * segments shorter than ``min_segment_ms`` are dropped as coughs or clicks.
    """

    def __init__(self, cfg: VadConfig, sample_rate: int, block_size: int) -> None:
        self.cfg = cfg
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.detector = SpeechDetector(sample_rate)

        preroll_frames = max(1, int(cfg.preroll_ms / (1000.0 * block_size / sample_rate)))
        # Each entry is (absolute sample index of the frame's first sample, frame).
        self._preroll: collections.deque[tuple[int, np.ndarray]] = collections.deque(
            maxlen=preroll_frames
        )
        self._pending = PendingSegment()
        self._in_speech = False
        self._onset_run = 0
        self._silence_samples = 0
        self._last_partial_at = 0
        #: Widened by the pipeline when inference cannot keep the 1.5 s cadence.
        self.partial_interval_s = cfg.partial_interval_s
        self.last_probability = 0.0

    def _ms(self, samples: int) -> int:
        return int(1000 * samples / self.sample_rate)

    def push(self, frame: np.ndarray, position: int) -> list[VadEvent]:
        """Feed one frame.

        ``position`` is the frame's absolute sample index in the stream, taken
        from the ring buffer's read cursor. Using it rather than a local counter
        keeps timestamps true to wall clock even after the buffer drops audio.
        """
        events: list[VadEvent] = []
        prob = self.detector.probability(frame)
        self.last_probability = prob
        stream_end = position + frame.size

        if not self._in_speech:
            self._preroll.append((position, frame))
            if prob >= self.cfg.speech_threshold:
                self._onset_run += 1
            else:
                self._onset_run = 0

            if self._onset_run >= self.cfg.onset_frames:
                self._in_speech = True
                self._onset_run = 0
                self._silence_samples = 0
                self._pending.clear()
                preroll = list(self._preroll)
                self._preroll.clear()
                self._pending.start_sample = preroll[0][0] if preroll else position
                for _, buffered in preroll:
                    self._pending.add(buffered)
                self._last_partial_at = self._pending.sample_count
                events.append(
                    VadEvent(
                        kind="speech_start",
                        audio=np.zeros(0, dtype=np.float32),
                        start_ms=self._ms(self._pending.start_sample),
                        end_ms=self._ms(stream_end),
                    )
                )
            return events

        # --- in speech ---
        self._pending.add(frame)
        if prob < self.cfg.silence_threshold:
            self._silence_samples += frame.size
        else:
            self._silence_samples = 0

        silence_limit = self.cfg.silence_ms * self.sample_rate / 1000.0
        max_samples = self.cfg.max_segment_s * self.sample_rate

        if self._silence_samples >= silence_limit:
            events.append(self._finalize("silence"))
            return [e for e in events if e is not None]
        if self._pending.sample_count >= max_samples:
            events.append(self._finalize("max_length"))
            return [e for e in events if e is not None]

        partial_stride = self.partial_interval_s * self.sample_rate
        if self._pending.sample_count - self._last_partial_at >= partial_stride:
            self._last_partial_at = self._pending.sample_count
            events.append(
                VadEvent(
                    kind="partial",
                    audio=self._pending.audio(),
                    start_ms=self._ms(self._pending.start_sample),
                    end_ms=self._ms(self._pending.start_sample + self._pending.sample_count),
                )
            )
        return events

    def _finalize(self, reason: SegmentReason) -> VadEvent | None:
        audio = self._pending.audio()
        start = self._pending.start_sample
        count = self._pending.sample_count

        self._in_speech = False
        self._onset_run = 0
        self._silence_samples = 0
        self._pending = PendingSegment()
        self._preroll.clear()

        # A max-length cut means the speaker is still talking: resume immediately
        # so the following audio is not treated as a fresh onset.
        if reason == "max_length":
            self._in_speech = True
            self._pending.start_sample = start + count
            self._last_partial_at = 0

        if count < self.cfg.min_segment_ms * self.sample_rate / 1000.0:
            return None
        # Trim the trailing silence we used only as the end-of-speech signal.
        if reason == "silence":
            keep = max(0, count - int(self.cfg.silence_ms * self.sample_rate / 1000.0 * 0.6))
            audio = audio[:keep] if keep else audio

        return VadEvent(
            kind="final",
            audio=audio,
            start_ms=self._ms(start),
            end_ms=self._ms(start + count),
            reason=reason,
        )

    def flush(self) -> VadEvent | None:
        """Finalize any in-flight utterance, e.g. when the meeting is stopped."""
        if not self._in_speech or self._pending.sample_count == 0:
            return None
        event = self._finalize("flush")
        self._in_speech = False
        self._pending = PendingSegment()
        return event
