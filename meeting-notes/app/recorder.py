"""Session audio recording for later playback.

Audio is written as 16-bit PCM WAV with a header that is patched on close. If
the process dies mid-meeting the header still claims zero length, so
:func:`repair_wav` rebuilds it from the actual file size — the recording of a
crashed session stays playable, which matches the same guarantee the segment
store makes for text.

Channels are aligned by absolute sample index rather than arrival order, so a
stream that stalls leaves silence in its lane instead of shifting the other
stream's audio out of sync with the transcript timestamps.
"""

from __future__ import annotations

import collections
import struct
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Literal

import numpy as np

RecordMode = Literal["mix", "stereo", "off"]

_HEADER_SIZE = 44


def _write_header(fh: BinaryIO, channels: int, sample_rate: int, data_bytes: int) -> None:
    byte_rate = sample_rate * channels * 2
    fh.write(b"RIFF")
    fh.write(struct.pack("<I", 36 + data_bytes))
    fh.write(b"WAVEfmt ")
    fh.write(struct.pack("<IHHIIHH", 16, 1, channels, sample_rate, byte_rate, channels * 2, 16))
    fh.write(b"data")
    fh.write(struct.pack("<I", data_bytes))


def repair_wav(path: Path) -> bool:
    """Patch a truncated/unfinalized WAV header from the on-disk size.

    Returns True when the file was modified.
    """
    try:
        size = path.stat().st_size
        if size <= _HEADER_SIZE:
            return False
        with path.open("r+b") as fh:
            fh.seek(4)
            riff_size = struct.unpack("<I", fh.read(4))[0]
            fh.seek(40)
            data_size = struct.unpack("<I", fh.read(4))[0]
            actual_data = size - _HEADER_SIZE
            if riff_size == size - 8 and data_size == actual_data:
                return False
            fh.seek(4)
            fh.write(struct.pack("<I", size - 8))
            fh.seek(40)
            fh.write(struct.pack("<I", actual_data))
        return True
    except (OSError, struct.error):
        return False


class _ChannelQueue:
    """FIFO of float32 blocks supporting exact-size reads."""

    def __init__(self) -> None:
        self._chunks: collections.deque[np.ndarray] = collections.deque()
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def push(self, data: np.ndarray) -> None:
        if data.size:
            self._chunks.append(data)
            self._size += data.size

    def take(self, n: int) -> np.ndarray:
        out = np.empty(n, dtype=np.float32)
        filled = 0
        while filled < n and self._chunks:
            head = self._chunks[0]
            need = n - filled
            if head.size <= need:
                out[filled : filled + head.size] = head
                filled += head.size
                self._chunks.popleft()
            else:
                out[filled:] = head[:need]
                self._chunks[0] = head[need:]
                filled = n
        if filled < n:
            out[filled:] = 0.0
        self._size = max(0, self._size - n)
        return out


@dataclass
class RecorderStats:
    bytes_written: int = 0
    duration_s: float = 0.0
    error: str = ""


class SessionRecorder:
    """Multiplexes per-channel audio into one WAV file for playback.

    ``mix`` downmixes all channels to mono (≈115 MB/hour) and ``stereo`` keeps
    the microphone on the left and system audio on the right (≈230 MB/hour) so
    the two sides stay separable on replay.
    """

    def __init__(
        self,
        path: Path,
        channels: list[str],
        sample_rate: int,
        mode: RecordMode = "mix",
        *,
        flush_samples: int = 8_000,
    ) -> None:
        self.path = Path(path)
        self.sample_rate = sample_rate
        self.mode: RecordMode = mode
        self.channels = list(channels) or ["mic"]
        self.out_channels = 2 if mode == "stereo" and len(self.channels) > 1 else 1
        self.stats = RecorderStats()

        self._flush_samples = flush_samples
        self._queues = {name: _ChannelQueue() for name in self.channels}
        self._end = {name: 0 for name in self.channels}
        self._cursor = 0
        self._lock = threading.Lock()
        self._fh: BinaryIO | None = None
        self._closed = False

        if mode != "off":
            self._open()

    @property
    def active(self) -> bool:
        return self._fh is not None and not self._closed

    def _open(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = self.path.open("wb")
            _write_header(self._fh, self.out_channels, self.sample_rate, 0)
            self._fh.flush()
        except OSError as exc:
            self._fh = None
            self.stats.error = f"녹음 파일을 열 수 없습니다: {exc}"

    def write(self, channel: str, position: int, frame: np.ndarray) -> None:
        """Queue one frame at its absolute sample index. Non-blocking, lossless."""
        if not self.active or channel not in self._queues:
            return
        with self._lock:
            end = self._end[channel]
            data = np.asarray(frame, dtype=np.float32).reshape(-1)
            if position < end:  # overlap: keep only the genuinely new tail
                skip = end - position
                if skip >= data.size:
                    return
                data = data[skip:]
                position = end
            elif position > end:  # gap: this stream stalled, pad its lane
                self._queues[channel].push(np.zeros(position - end, dtype=np.float32))
            self._queues[channel].push(data)
            self._end[channel] = position + data.size

            if min(self._end.values()) - self._cursor >= self._flush_samples:
                self._flush_locked()

    def _flush_locked(self) -> None:
        if self._fh is None:
            return
        upto = min(self._end.values())
        count = upto - self._cursor
        if count <= 0:
            return

        lanes = [self._queues[name].take(count) for name in self.channels]
        if self.out_channels == 1:
            block = lanes[0] if len(lanes) == 1 else np.sum(lanes, axis=0) / len(lanes)
            interleaved = block
        else:
            left = lanes[0]
            right = lanes[1] if len(lanes) > 1 else lanes[0]
            interleaved = np.empty(count * 2, dtype=np.float32)
            interleaved[0::2] = left
            interleaved[1::2] = right

        pcm = np.clip(interleaved, -1.0, 1.0)
        pcm = (pcm * 32767.0).astype("<i2")
        try:
            self._fh.write(pcm.tobytes())
            self.stats.bytes_written += pcm.nbytes
        except OSError as exc:
            # Out of disk or a vanished volume: stop recording, keep transcribing.
            self.stats.error = f"녹음 중단 (디스크 오류): {exc}"
            try:
                self._fh.close()
            except OSError:
                pass
            self._fh = None
            return
        self._cursor = upto
        self.stats.duration_s = self._cursor / float(self.sample_rate)

    def flush(self) -> None:
        with self._lock:
            self._flush_locked()
            if self._fh is not None:
                try:
                    self._fh.flush()
                except OSError:
                    pass

    def close(self) -> float:
        """Finalize the header and return the recorded duration in seconds."""
        with self._lock:
            if self._closed:
                return self.stats.duration_s
            self._closed = True
            self._flush_locked()
            fh, self._fh = self._fh, None
            if fh is None:
                return self.stats.duration_s
            try:
                data_bytes = fh.tell() - _HEADER_SIZE
                fh.seek(0)
                _write_header(fh, self.out_channels, self.sample_rate, max(0, data_bytes))
                fh.close()
            except OSError as exc:
                self.stats.error = f"녹음 마무리 실패: {exc}"
            return self.stats.duration_s
