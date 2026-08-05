"""Generate speech-like test audio with known utterance boundaries.

The pipeline needs a deterministic input to test segmentation against on machines
with no microphone. Real TTS is preferred when available (``--voice``); otherwise
this synthesizes a voiced signal — a glottal-pulse harmonic stack shaped by three
formants and modulated at a syllable rate — which silero-vad scores as speech.

The ground-truth boundaries are printed as JSON so a test can assert that the
detected segments land within tolerance.
"""

from __future__ import annotations

import argparse
import json
import struct
import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16_000


def _formant_filter(signal: np.ndarray, freq: float, bandwidth: float, rate: int) -> np.ndarray:
    """Two-pole resonator — the classic cheap formant."""
    r = np.exp(-np.pi * bandwidth / rate)
    theta = 2 * np.pi * freq / rate
    a1, a2 = -2 * r * np.cos(theta), r * r
    out = np.zeros_like(signal)
    y1 = y2 = 0.0
    for i, x in enumerate(signal):
        y = x - a1 * y1 - a2 * y2
        out[i] = y
        y2, y1 = y1, y
    return out


def synth_utterance(duration_s: float, rng: np.random.Generator, rate: int = SAMPLE_RATE) -> np.ndarray:
    """Synthesize one voiced utterance of the given length."""
    n = int(duration_s * rate)
    t = np.arange(n) / rate

    # Glottal source: a falling-intonation harmonic stack.
    f0 = 125.0 * (1.0 - 0.12 * t / max(t[-1], 1e-6)) + rng.normal(0, 1.5, n).cumsum() * 0.02
    phase = 2 * np.pi * np.cumsum(f0) / rate
    source = sum(np.sin(k * phase) / k for k in range(1, 14))
    source += rng.normal(0, 0.05, n)  # breath noise

    voiced = np.zeros(n)
    for freq, bw, gain in ((700.0, 110.0, 1.0), (1220.0, 130.0, 0.55), (2600.0, 190.0, 0.28)):
        voiced += gain * _formant_filter(source, freq, bw, rate)

    # Syllable envelope (~4.2 Hz) plus a slow phrase contour.
    syllable = 0.5 + 0.5 * np.sin(2 * np.pi * 4.2 * t - np.pi / 2) ** 2
    contour = np.clip(np.sin(np.pi * t / max(t[-1], 1e-6)) * 1.3, 0.15, 1.0)
    envelope = syllable * contour

    # Short attack/release so the boundary is not a click.
    ramp = min(int(0.02 * rate), n // 2)
    if ramp:
        envelope[:ramp] *= np.linspace(0, 1, ramp)
        envelope[-ramp:] *= np.linspace(1, 0, ramp)

    out = voiced * envelope
    peak = float(np.max(np.abs(out)) or 1.0)
    return (out / peak * 0.55).astype(np.float32)


def build(
    plan: list[tuple[float, float]],
    *,
    noise_db: float = -52.0,
    seed: int = 7,
    rate: int = SAMPLE_RATE,
) -> tuple[np.ndarray, list[dict[str, int]]]:
    """Render a (silence, speech) plan into one track plus its ground truth."""
    rng = np.random.default_rng(seed)
    chunks: list[np.ndarray] = []
    truth: list[dict[str, int]] = []
    cursor = 0

    noise_amp = 10 ** (noise_db / 20.0)
    for silence_s, speech_s in plan:
        gap = int(silence_s * rate)
        chunks.append(np.zeros(gap, dtype=np.float32))
        cursor += gap

        speech = synth_utterance(speech_s, rng, rate)
        truth.append(
            {
                "start_ms": int(1000 * cursor / rate),
                "end_ms": int(1000 * (cursor + speech.size) / rate),
            }
        )
        chunks.append(speech)
        cursor += speech.size

    chunks.append(np.zeros(int(1.2 * rate), dtype=np.float32))
    track = np.concatenate(chunks)
    track += rng.normal(0, noise_amp, track.size).astype(np.float32)
    return np.clip(track, -1.0, 1.0), truth


def write_wav(path: Path, data: np.ndarray, rate: int = SAMPLE_RATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(data, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())


DEFAULT_PLAN: list[tuple[float, float]] = [
    (0.8, 3.0),
    (1.4, 2.2),
    (1.0, 4.5),
    (2.0, 1.6),
    (1.2, 3.4),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a test WAV with known boundaries")
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--noise-db", type=float, default=-52.0)
    parser.add_argument(
        "--repeat", type=int, default=1, help="repeat the plan N times (for long-run tests)"
    )
    parser.add_argument("--truth", type=Path, help="write ground-truth boundaries as JSON")
    args = parser.parse_args()

    plan = DEFAULT_PLAN * max(1, args.repeat)
    track, truth = build(plan, noise_db=args.noise_db, seed=args.seed)
    write_wav(args.output, track)

    if args.truth:
        args.truth.write_text(json.dumps(truth, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "path": str(args.output),
                "duration_s": round(track.size / SAMPLE_RATE, 2),
                "utterances": len(truth),
                "truth": truth,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
