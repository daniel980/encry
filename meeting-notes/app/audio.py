"""Audio device enumeration, capture, and bounded buffering.

The capture callback never blocks: it copies its block into a fixed-size ring
buffer and returns. When a consumer falls behind, the oldest audio is discarded
and counted rather than growing memory, which is what keeps a three-hour
recording flat in RSS.

``sounddevice`` is imported lazily so that the rest of the app (server, UI,
stored-session playback) still runs on machines with no PortAudio installed.
"""

from __future__ import annotations

import platform
import queue
import threading
import time
import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator, Literal

import numpy as np

from .config import AudioConfig

ChannelKind = Literal["mic", "loopback", "unknown"]

#: Substrings that mark a device as a system-audio loopback, per platform.
_LOOPBACK_HINTS: dict[str, tuple[str, ...]] = {
    "Darwin": ("blackhole", "loopback", "soundflower", "multi-output", "aggregate"),
    "Linux": (".monitor", "monitor of", "monitor_"),
    "Windows": ("stereo mix", "loopback", "what u hear", "wave out mix"),
}


class AudioError(RuntimeError):
    """Raised when audio capture cannot start or has died."""


@dataclass(frozen=True)
class InputDevice:
    """A capture-capable device as offered to the user."""

    index: int
    name: str
    channels: int
    default_samplerate: float
    hostapi: str
    kind: ChannelKind
    #: True when this is an *output* device to be captured via WASAPI loopback.
    wasapi_loopback: bool = False

    @property
    def key(self) -> str:
        return f"{self.index}:wasapi" if self.wasapi_loopback else str(self.index)

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "index": self.index,
            "name": self.name,
            "channels": self.channels,
            "default_samplerate": self.default_samplerate,
            "hostapi": self.hostapi,
            "kind": self.kind,
            "wasapi_loopback": self.wasapi_loopback,
        }


def _classify(name: str) -> ChannelKind:
    lowered = name.lower()
    for hint in _LOOPBACK_HINTS.get(platform.system(), ()):  # noqa: SIM110
        if hint in lowered:
            return "loopback"
    return "mic"


def _sounddevice() -> Any:
    try:
        import sounddevice as sd  # noqa: PLC0415
    except Exception as exc:  # pragma: no cover - depends on host libraries
        raise AudioError(
            "sounddevice is unavailable. Install the PortAudio system library "
            "(macOS: `brew install portaudio`, Debian/Ubuntu: "
            "`apt install libportaudio2`) and then `pip install sounddevice`."
        ) from exc
    return sd


def enumerate_inputs() -> list[InputDevice]:
    """List capture-capable devices, tagging likely system-audio loopbacks.

    Returns an empty list rather than raising when PortAudio is missing, so the
    UI can render an explanatory empty state instead of an error page.
    """
    try:
        sd = _sounddevice()
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
    except Exception:
        return []

    found: list[InputDevice] = []
    for index, dev in enumerate(devices):
        hostapi_name = ""
        try:
            hostapi_name = str(hostapis[dev["hostapi"]]["name"])
        except (IndexError, KeyError, TypeError):
            pass

        if int(dev.get("max_input_channels", 0)) > 0:
            found.append(
                InputDevice(
                    index=index,
                    name=str(dev.get("name", f"device {index}")),
                    channels=int(dev["max_input_channels"]),
                    default_samplerate=float(dev.get("default_samplerate", 0.0) or 0.0),
                    hostapi=hostapi_name,
                    kind=_classify(str(dev.get("name", ""))),
                )
            )

        # On Windows, any output device can be captured through WASAPI loopback,
        # which is the reliable way to get meeting audio without extra software.
        is_wasapi = "wasapi" in hostapi_name.lower()
        if is_wasapi and int(dev.get("max_output_channels", 0)) > 0:
            found.append(
                InputDevice(
                    index=index,
                    name=f"{dev.get('name', f'device {index}')} (loopback)",
                    channels=int(dev["max_output_channels"]),
                    default_samplerate=float(dev.get("default_samplerate", 0.0) or 0.0),
                    hostapi=hostapi_name,
                    kind="loopback",
                    wasapi_loopback=True,
                )
            )
    return found


def loopback_guidance() -> dict[str, str]:
    """Platform-specific instructions shown when no loopback device is found."""
    system = platform.system()
    if system == "Darwin":
        return {
            "platform": "macOS",
            "title": "시스템 오디오 캡처에는 BlackHole이 필요합니다",
            "body": (
                "1. `brew install blackhole-2ch` (또는 existential.audio/blackhole 에서 설치)\n"
                "2. 오디오 MIDI 설정 → + → '다중 출력 장치' 생성\n"
                "3. 다중 출력 장치에서 사용하는 스피커와 BlackHole 2ch를 모두 체크\n"
                "4. 시스템 설정 → 사운드 → 출력을 그 다중 출력 장치로 변경\n"
                "5. 이 앱을 재시작하면 입력 목록에 BlackHole 2ch가 나타납니다"
            ),
        }
    if system == "Windows":
        return {
            "platform": "Windows",
            "title": "WASAPI 루프백으로 시스템 오디오를 캡처합니다",
            "body": (
                "출력 장치 이름 뒤에 (loopback)이 붙은 항목을 선택하세요. "
                "목록에 없다면 사운드 설정에서 해당 출력 장치가 활성 상태인지 "
                "확인한 뒤 앱을 재시작하세요."
            ),
        }
    return {
        "platform": "Linux",
        "title": "PulseAudio/PipeWire monitor 소스를 사용합니다",
        "body": (
            "`pactl list short sources | grep monitor` 로 monitor 소스를 확인하세요. "
            "보이지 않으면 `pactl load-module module-null-sink` 후 재시작하거나, "
            "pavucontrol의 녹음 탭에서 이 앱의 입력을 monitor로 지정하세요."
        ),
    }


def resample_linear(data: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Resample mono float32 audio by linear interpolation.

    Good enough for 16 kHz speech: Whisper's own front end is far more lossy
    than the interpolation error, and this avoids a scipy/soxr dependency.
    """
    if src_rate == dst_rate or data.size == 0:
        return data.astype(np.float32, copy=False)
    duration = data.size / float(src_rate)
    dst_len = max(1, int(round(duration * dst_rate)))
    src_x = np.arange(data.size, dtype=np.float64)
    dst_x = np.linspace(0.0, data.size - 1, dst_len, dtype=np.float64)
    return np.interp(dst_x, src_x, data).astype(np.float32)


def to_mono(data: np.ndarray) -> np.ndarray:
    """Collapse an (n, channels) block to mono float32."""
    if data.ndim == 1:
        return data.astype(np.float32, copy=False)
    return data.mean(axis=1).astype(np.float32)


class RingBuffer:
    """Single-producer/single-consumer circular buffer with a hard capacity.

    Overflow discards the oldest samples and advances the read cursor, so a slow
    consumer degrades into dropped audio (counted in :attr:`dropped_samples`)
    instead of unbounded memory growth.
    """

    def __init__(self, capacity: int) -> None:
        self._capacity = int(capacity)
        self._buf = np.zeros(self._capacity, dtype=np.float32)
        self._written = 0  # monotonic total samples written
        self._read = 0  # monotonic total samples consumed
        self._dropped = 0
        self._closed = False
        self._cond = threading.Condition(threading.Lock())

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def dropped_samples(self) -> int:
        with self._cond:
            return self._dropped

    @property
    def read_position(self) -> int:
        """Absolute index of the next sample a consumer will receive.

        Dropped samples advance this cursor, so it stays aligned with real time
        and is the timestamp reference for both transcripts and recordings.
        """
        with self._cond:
            return self._read

    @property
    def pending(self) -> int:
        with self._cond:
            return self._written - self._read

    def close(self) -> None:
        with self._cond:
            self._closed = True
            self._cond.notify_all()

    def write(self, data: np.ndarray) -> None:
        """Append a block. Called from the audio callback; never blocks."""
        block = np.asarray(data, dtype=np.float32).reshape(-1)
        n = block.size
        if n == 0:
            return
        if n > self._capacity:  # pathologically large block: keep the newest tail
            block = block[-self._capacity :]
            n = block.size

        with self._cond:
            start = self._written % self._capacity
            end = start + n
            if end <= self._capacity:
                self._buf[start:end] = block
            else:
                split = self._capacity - start
                self._buf[start:] = block[:split]
                self._buf[: end - self._capacity] = block[split:]
            self._written += n

            behind = self._written - self._read
            if behind > self._capacity:
                lost = behind - self._capacity
                self._read += lost
                self._dropped += lost
            self._cond.notify_all()

    def read(self, n: int, timeout: float = 0.5) -> np.ndarray | None:
        """Consume exactly ``n`` samples, waiting up to ``timeout`` seconds.

        Returns ``None`` on timeout or after :meth:`close`, which lets consumer
        loops poll their own stop flag between calls.
        """
        deadline = time.monotonic() + timeout
        with self._cond:
            while (self._written - self._read) < n:
                if self._closed:
                    return None
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._cond.wait(remaining)

            start = self._read % self._capacity
            end = start + n
            if end <= self._capacity:
                out = self._buf[start:end].copy()
            else:
                split = self._capacity - start
                out = np.concatenate((self._buf[start:], self._buf[: end - self._capacity]))
            self._read += n
            return out


@dataclass
class SourceStats:
    """Live health counters surfaced in the status bar."""

    dropped_blocks: int = 0
    overflow_blocks: int = 0
    level: float = 0.0
    started_at: float = 0.0
    error: str = ""


class AudioSource(ABC):
    """A 16 kHz mono audio producer feeding a :class:`RingBuffer`."""

    def __init__(self, name: str, kind: ChannelKind, cfg: AudioConfig) -> None:
        self.name = name
        self.kind: ChannelKind = kind
        self.cfg = cfg
        self.ring = RingBuffer(cfg.ring_samples)
        self.stats = SourceStats()
        self._running = threading.Event()

    @property
    def running(self) -> bool:
        return self._running.is_set()

    def _ingest(self, mono: np.ndarray) -> None:
        """Common tail of every producer: level metering, then buffer write."""
        if mono.size:
            self.stats.level = float(np.sqrt(np.mean(np.square(mono, dtype=np.float64))))
        self.ring.write(mono)

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    def frames(self, stop: threading.Event) -> Iterator[tuple[int, np.ndarray]]:
        """Yield ``(absolute sample index, frame)`` until stopped or exhausted."""
        while not stop.is_set():
            position = self.ring.read_position
            frame = self.ring.read(self.cfg.block_size, timeout=0.25)
            if frame is None:
                if not self.running and self.ring.pending < self.cfg.block_size:
                    return
                continue
            yield position, frame


class DeviceSource(AudioSource):
    """Live capture from a hardware or virtual input device."""

    def __init__(self, device: InputDevice, cfg: AudioConfig) -> None:
        super().__init__(device.name, device.kind, cfg)
        self.device = device
        self._stream: Any = None
        self._native_rate = cfg.sample_rate
        self._on_error: Callable[[str], None] | None = None

    def set_error_handler(self, handler: Callable[[str], None]) -> None:
        self._on_error = handler

    def _callback(self, indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        # Runs on PortAudio's realtime thread: copy, convert, hand off, return.
        if status:
            if getattr(status, "input_overflow", False):
                self.stats.overflow_blocks += 1
        mono = to_mono(np.asarray(indata))
        if self._native_rate != self.cfg.sample_rate:
            mono = resample_linear(mono, self._native_rate, self.cfg.sample_rate)
        self._ingest(mono)

    def _open(self, samplerate: int, channels: int) -> Any:
        sd = _sounddevice()
        extra: Any = None
        if self.device.wasapi_loopback:
            try:
                extra = sd.WasapiSettings(loopback=True)
            except Exception:  # pragma: no cover - non-Windows hosts
                extra = None
        return sd.InputStream(
            device=self.device.index,
            channels=channels,
            samplerate=samplerate,
            blocksize=self.cfg.block_size,
            dtype="float32",
            callback=self._callback,
            extra_settings=extra,
        )

    def start(self) -> None:
        channels = max(1, min(2, self.device.channels))
        attempts: list[tuple[int, int]] = [(self.cfg.sample_rate, channels)]
        native = int(self.device.default_samplerate or 0)
        if native and native != self.cfg.sample_rate:
            attempts.append((native, channels))
        if channels != 1:
            attempts.append((self.cfg.sample_rate, 1))

        last_error: Exception | None = None
        for rate, chans in attempts:
            try:
                self._native_rate = rate
                self._stream = self._open(rate, chans)
                self._stream.start()
                self._running.set()
                self.stats.started_at = time.time()
                return
            except Exception as exc:  # try the next fallback combination
                last_error = exc
                self._stream = None
        raise AudioError(f"'{self.device.name}' 입력을 열 수 없습니다: {last_error}")

    def stop(self) -> None:
        self._running.clear()
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        self.ring.close()

    def poll_health(self) -> str:
        """Report a disconnected device; the pipeline surfaces this to the UI."""
        if self._stream is None or not self._running.is_set():
            return ""
        try:
            if not self._stream.active:
                return f"'{self.device.name}' 입력이 중단되었습니다 (장치 연결 확인)"
        except Exception as exc:
            return f"'{self.device.name}' 입력 오류: {exc}"
        return ""


class FileSource(AudioSource):
    """Feed a WAV file through the pipeline as if it were a live device.

    Used for deterministic regression tests and for verifying the pipeline on
    machines with no capture hardware. ``speed`` above 1.0 compresses wall-clock
    time, which is how the long-run memory test covers hours in minutes.
    """

    def __init__(
        self,
        path: Path,
        cfg: AudioConfig,
        *,
        kind: ChannelKind = "mic",
        speed: float = 1.0,
        loop: bool = False,
        name: str = "",
    ) -> None:
        super().__init__(name or f"file:{Path(path).name}", kind, cfg)
        self.path = Path(path)
        self.speed = max(0.0, speed)
        self.loop = loop
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.finished = threading.Event()

    def _read_wav(self) -> np.ndarray:
        with wave.open(str(self.path), "rb") as wav:
            channels = wav.getnchannels()
            width = wav.getsampwidth()
            rate = wav.getframerate()
            raw = wav.readframes(wav.getnframes())

        if width == 2:
            data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        elif width == 4:
            data = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
        elif width == 1:
            data = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
        else:
            raise AudioError(f"지원하지 않는 WAV 샘플 폭입니다: {width * 8}bit")

        if channels > 1:
            data = data.reshape(-1, channels).mean(axis=1)
        return resample_linear(data, rate, self.cfg.sample_rate)

    def _run(self) -> None:
        try:
            samples = self._read_wav()
        except Exception as exc:
            self.stats.error = str(exc)
            self._running.clear()
            self.finished.set()
            self.ring.close()
            return

        block = self.cfg.block_size
        period = block / self.cfg.sample_rate / self.speed if self.speed > 0 else 0.0
        next_at = time.monotonic()
        while not self._stop.is_set():
            for start in range(0, samples.size, block):
                if self._stop.is_set():
                    break
                chunk = samples[start : start + block]
                if chunk.size < block:
                    chunk = np.pad(chunk, (0, block - chunk.size))
                self._ingest(chunk)
                if period > 0:
                    next_at += period
                    delay = next_at - time.monotonic()
                    if delay > 0:
                        time.sleep(delay)
                    else:
                        next_at = time.monotonic()
            if not self.loop:
                break
        # Let the consumer drain the tail before the ring reports end-of-stream.
        self._running.clear()
        self.finished.set()
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if (self.ring._written - self.ring._read) < block:
                break
            time.sleep(0.02)
        self.ring.close()

    def start(self) -> None:
        if not self.path.is_file():
            raise AudioError(f"파일을 찾을 수 없습니다: {self.path}")
        self._running.set()
        self.stats.started_at = time.time()
        self._thread = threading.Thread(target=self._run, name="file-source", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self.ring.close()

    def poll_health(self) -> str:
        return self.stats.error
