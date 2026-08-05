"""Wiring from audio sources to transcribed segments.

Threading model — the capture callback never blocks and inference never runs on
a capture thread:

    sounddevice callback  →  RingBuffer (fixed size, drops oldest)
                              ↓
    one VAD thread per stream  →  frames, boundary decisions, recording tee
                              ↓
    one STT worker (shared)   →  PriorityQueue: finals first, stale partials dropped

A single STT worker means the Whisper models are loaded once no matter how many
streams are open, and partial inference can never delay a finalized segment.
"""

from __future__ import annotations

import queue
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

import numpy as np

from pathlib import Path

from .audio import AudioSource, ChannelKind
from .config import Config
from .recorder import RecordMode, SessionRecorder
from .stt import SttEngine, TranscribeResult
from .vad import SegmentBoundaryDetector

JobKind = Literal["partial", "final", "stop"]


@dataclass(order=True)
class _Job:
    """One inference request. Ordered so finals always outrank partials."""

    priority: int
    sequence: int
    kind: JobKind = field(compare=False, default="partial")
    channel: str = field(compare=False, default="")
    audio: np.ndarray = field(compare=False, default_factory=lambda: np.zeros(0, np.float32))
    start_ms: int = field(compare=False, default=0)
    end_ms: int = field(compare=False, default=0)
    epoch: int = field(compare=False, default=0)
    reason: str = field(compare=False, default="")
    queued_at: float = field(compare=False, default=0.0)


@dataclass
class SegmentDraft:
    """A finalized utterance, before language rules and persistence."""

    channel: str
    speaker_key: str
    start_ms: int
    end_ms: int
    text: str
    language: str
    language_prob: float
    duration_s: float
    reason: str
    synthetic: bool


@dataclass
class PartialUpdate:
    """In-progress text for the utterance currently being spoken."""

    channel: str
    speaker_key: str
    start_ms: int
    end_ms: int
    text: str
    synthetic: bool


@dataclass
class Channel:
    """One capture stream and the speaker it is attributed to."""

    source: AudioSource
    speaker_key: str
    speaker_label: str
    kind: ChannelKind

    @property
    def name(self) -> str:
        return self.source.name


class Pipeline:
    """Runs capture, segmentation, and transcription for one meeting."""

    def __init__(
        self,
        cfg: Config,
        engine: SttEngine,
        *,
        on_partial: Callable[[PartialUpdate], None] | None = None,
        on_final: Callable[[SegmentDraft], None] | None = None,
        on_status: Callable[[str, str], None] | None = None,
        recorder: SessionRecorder | None = None,
    ) -> None:
        self.cfg = cfg
        self.engine = engine
        self.on_partial = on_partial
        self.on_final = on_final
        self.on_status = on_status
        self.recorder = recorder

        self.channels: dict[str, Channel] = {}
        self._detectors: dict[str, SegmentBoundaryDetector] = {}
        self._epochs: dict[str, int] = {}
        self._threads: list[threading.Thread] = []
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._jobs: queue.PriorityQueue[_Job] = queue.PriorityQueue()
        self._job_seq = 0
        self._job_lock = threading.Lock()
        self._started_at = 0.0
        self._paused_total = 0.0
        self._paused_at = 0.0

        self._latencies: deque[float] = deque(maxlen=8)
        self.partial_interval_s = cfg.vad.partial_interval_s
        self.adaptive_note = ""
        self.last_error = ""
        #: One in-flight partial per channel is enough; a second only means the
        #: worker hasn't caught up yet. Skipping the resubmit — rather than
        #: queueing it — is what keeps memory bounded when inference falls
        #: behind capture (queued jobs hold full audio arrays).
        self._partial_inflight: set[str] = set()
        self._partial_dropped_for_backlog = 0

    # ---------------------------------------------------------------- lifecycle

    def add_channel(
        self, source: AudioSource, speaker_key: str, speaker_label: str
    ) -> Channel:
        channel = Channel(source, speaker_key, speaker_label, source.kind)
        self.channels[source.name] = channel
        self._detectors[source.name] = SegmentBoundaryDetector(
            self.cfg.vad, self.cfg.audio.sample_rate, self.cfg.audio.block_size
        )
        self._epochs[source.name] = 0
        return channel

    def attach_recorder(self, path: Path, mode: RecordMode = "mix") -> SessionRecorder:
        """Build a recorder wired to this pipeline's channels and attach it.

        The recorder's channel keys must exactly match the audio source names
        used in :meth:`add_channel` — building it here, after channels are
        added, is what guarantees that instead of leaving it to the caller to
        keep two channel-name lists in sync.
        """
        recorder = SessionRecorder(
            path, list(self.channels.keys()), self.cfg.audio.sample_rate, mode=mode
        )
        self.recorder = recorder
        return recorder

    def start(self) -> None:
        if not self.channels:
            raise RuntimeError("입력 채널이 없습니다.")
        self._stop.clear()
        self._started_at = time.time()

        for channel in self.channels.values():
            channel.source.start()

        worker = threading.Thread(target=self._stt_loop, name="stt-worker", daemon=True)
        worker.start()
        self._threads.append(worker)

        for name in self.channels:
            thread = threading.Thread(
                target=self._vad_loop, args=(name,), name=f"vad-{name}", daemon=True
            )
            thread.start()
            self._threads.append(thread)

        health = threading.Thread(target=self._health_loop, name="health", daemon=True)
        health.start()
        self._threads.append(health)

    def pause(self) -> None:
        """Stop consuming audio without tearing down devices or models."""
        if not self._paused.is_set():
            self._paused.set()
            self._paused_at = time.time()

    def resume(self) -> None:
        if self._paused.is_set():
            self._paused_total += time.time() - self._paused_at
            self._paused.clear()

    def stop(self) -> None:
        """Finalize in-flight speech, then shut every thread and device down."""
        self._paused.clear()
        for name, detector in self._detectors.items():
            event = detector.flush()
            if event is not None and event.audio.size:
                self._submit(name, "final", event.audio, event.start_ms, event.end_ms, "flush")

        # Let the worker drain the flushed finals before we tell it to exit.
        deadline = time.monotonic() + 10.0
        while not self._jobs.empty() and time.monotonic() < deadline:
            time.sleep(0.05)

        self._stop.set()
        with self._job_lock:
            self._job_seq += 1
            sequence = self._job_seq
        self._jobs.put(_Job(priority=-1, sequence=sequence, kind="stop"))
        for channel in self.channels.values():
            try:
                channel.source.stop()
            except Exception:
                pass
        for thread in self._threads:
            thread.join(timeout=3.0)
        self._threads.clear()
        if self.recorder is not None:
            self.recorder.close()

    # -------------------------------------------------------------------- loops

    def _vad_loop(self, name: str) -> None:
        channel = self.channels[name]
        detector = self._detectors[name]

        try:
            for position, frame in channel.source.frames(self._stop):
                if self._paused.is_set():
                    continue
                if self.recorder is not None:
                    self.recorder.write(name, position, frame)

                detector.partial_interval_s = self.partial_interval_s
                for event in detector.push(frame, position):
                    if event.kind == "partial":
                        self._submit(
                            name, "partial", event.audio, event.start_ms, event.end_ms, ""
                        )
                    elif event.kind == "final":
                        self._submit(
                            name,
                            "final",
                            event.audio,
                            event.start_ms,
                            event.end_ms,
                            event.reason or "",
                        )
        except Exception as exc:  # a dead stream must not kill the meeting
            self._report(f"'{name}' 처리 중 오류: {exc}")

    def _submit(
        self, channel: str, kind: JobKind, audio: np.ndarray, start_ms: int, end_ms: int, reason: str
    ) -> None:
        if audio.size == 0:
            return
        with self._job_lock:
            if kind == "partial":
                if channel in self._partial_inflight:
                    # Worker hasn't caught up on the last one; queueing another
                    # would only grow memory (each job holds a full audio array)
                    # without improving latency. Wait for the next tick instead.
                    self._partial_dropped_for_backlog += 1
                    return
                self._partial_inflight.add(channel)
            self._job_seq += 1
            sequence = self._job_seq
            if kind == "final":
                # A finalized utterance supersedes every partial for this channel.
                self._epochs[channel] += 1
            epoch = self._epochs[channel]

        self._jobs.put(
            _Job(
                priority=0 if kind == "final" else 1,
                sequence=sequence,
                kind=kind,
                channel=channel,
                audio=audio,
                start_ms=start_ms,
                end_ms=end_ms,
                epoch=epoch,
                reason=reason,
                queued_at=time.monotonic(),
            )
        )

    def _stt_loop(self) -> None:
        while not self._stop.is_set():
            try:
                job = self._jobs.get(timeout=0.25)
            except queue.Empty:
                continue
            if job.kind == "stop":
                return

            # Drop partials that a newer partial or a final has already replaced.
            if job.kind == "partial":
                with self._job_lock:
                    self._partial_inflight.discard(job.channel)
                    stale = job.epoch != self._epochs.get(job.channel, 0)
                if stale:
                    continue

            try:
                result = self.engine.transcribe(job.audio, job.kind)
            except Exception as exc:
                self._report(f"추론 실패: {exc}")
                continue

            if job.kind == "partial":
                self._record_latency(time.monotonic() - job.queued_at)
                self._emit_partial(job, result)
            else:
                self._emit_final(job, result)

    def _emit_partial(self, job: _Job, result: TranscribeResult) -> None:
        text = result.text.strip()
        if not text or self.on_partial is None:
            return
        channel = self.channels[job.channel]
        self.on_partial(
            PartialUpdate(
                channel=job.channel,
                speaker_key=channel.speaker_key,
                start_ms=job.start_ms,
                end_ms=job.end_ms,
                text=text,
                synthetic=result.synthetic,
            )
        )

    def _emit_final(self, job: _Job, result: TranscribeResult) -> None:
        text = result.text.strip()
        if not text or result.no_speech_prob >= 0.9 or self.on_final is None:
            return
        channel = self.channels[job.channel]
        self.on_final(
            SegmentDraft(
                channel=job.channel,
                speaker_key=channel.speaker_key,
                start_ms=job.start_ms,
                end_ms=job.end_ms,
                text=text,
                language=result.language,
                language_prob=result.language_prob,
                duration_s=result.duration_s,
                reason=job.reason,
                synthetic=result.synthetic,
            )
        )

    def _record_latency(self, latency: float) -> None:
        """Widen the partial cadence when inference cannot keep up, and narrow it back."""
        self._latencies.append(latency)
        if len(self._latencies) < 4:
            return
        ordered = sorted(self._latencies)
        p90 = ordered[max(0, int(len(ordered) * 0.9) - 1)]
        budget = self.partial_interval_s * 0.7

        if p90 > budget and self.partial_interval_s < self.cfg.vad.partial_interval_max_s:
            self.partial_interval_s = min(
                self.cfg.vad.partial_interval_max_s, self.partial_interval_s + 0.5
            )
            self.adaptive_note = (
                f"추론이 느려 partial 간격을 {self.partial_interval_s:.1f}초로 늘렸습니다"
            )
            self._report(self.adaptive_note, level="info")
        elif p90 < budget * 0.5 and self.partial_interval_s > self.cfg.vad.partial_interval_s:
            self.partial_interval_s = max(
                self.cfg.vad.partial_interval_s, self.partial_interval_s - 0.5
            )
            self.adaptive_note = (
                f"partial 간격을 {self.partial_interval_s:.1f}초로 되돌렸습니다"
                if self.partial_interval_s > self.cfg.vad.partial_interval_s
                else ""
            )

    def _health_loop(self) -> None:
        while not self._stop.wait(2.0):
            for channel in self.channels.values():
                poll = getattr(channel.source, "poll_health", None)
                if poll is None:
                    continue
                message = poll()
                if message:
                    self._report(message)
            if self.recorder is not None:
                self.recorder.flush()
                if self.recorder.stats.error:
                    self._report(self.recorder.stats.error)

    def _report(self, message: str, level: str = "error") -> None:
        if level == "error":
            self.last_error = message
        if self.on_status is not None:
            self.on_status(level, message)

    # ------------------------------------------------------------------ metrics

    @property
    def elapsed_s(self) -> float:
        if not self._started_at:
            return 0.0
        end = self._paused_at if self._paused.is_set() else time.time()
        return max(0.0, end - self._started_at - self._paused_total)

    @property
    def paused(self) -> bool:
        return self._paused.is_set()

    def snapshot(self) -> dict[str, Any]:
        """Everything the status bar and level meter need, in one cheap read."""
        channels = []
        dropped_total = 0
        for name, channel in self.channels.items():
            dropped = channel.source.ring.dropped_samples
            dropped_total += dropped
            detector = self._detectors[name]
            channels.append(
                {
                    "name": name,
                    "speaker_key": channel.speaker_key,
                    "speaker_label": channel.speaker_label,
                    "kind": channel.kind,
                    "level": round(channel.source.stats.level, 5),
                    "speech_prob": round(detector.last_probability, 3),
                    "dropped_samples": dropped,
                    "overflow_blocks": channel.source.stats.overflow_blocks,
                    "running": channel.source.running,
                }
            )

        latency_p90 = 0.0
        if self._latencies:
            ordered = sorted(self._latencies)
            latency_p90 = round(ordered[max(0, int(len(ordered) * 0.9) - 1)], 3)

        return {
            "elapsed_s": round(self.elapsed_s, 2),
            "paused": self.paused,
            "channels": channels,
            "dropped_samples": dropped_total,
            "dropped_seconds": round(dropped_total / self.cfg.audio.sample_rate, 2),
            "queue_depth": self._jobs.qsize(),
            "partial_dropped_for_backlog": self._partial_dropped_for_backlog,
            "partial_interval_s": round(self.partial_interval_s, 2),
            "partial_latency_p90": latency_p90,
            "adaptive_note": self.adaptive_note,
            "engine": self.engine.describe(),
            "synthetic": self.engine.synthetic,
            "vad": self._detectors[next(iter(self._detectors))].detector.backend
            if self._detectors
            else "",
            "recording": bool(self.recorder and self.recorder.active),
            "recorded_s": round(self.recorder.stats.duration_s, 1) if self.recorder else 0.0,
            "error": self.last_error,
        }
