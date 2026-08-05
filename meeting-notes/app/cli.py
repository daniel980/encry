"""Console entry point for Phase 1 verification: capture → VAD → STT, no server.

Usage:
    python -m app.cli --device 2                  # live device
    python -m app.cli --file sample.wav            # replay a WAV as if live
    python -m app.cli --file sample.wav --speed 20 # compressed replay for soak tests
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .audio import DeviceSource, FileSource, enumerate_inputs, loopback_guidance
from .config import load_config
from .pipeline import Pipeline, PartialUpdate, SegmentDraft
from .stt import create_engine


def _format_ts(ms: int) -> str:
    total_s = ms // 1000
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Meeting transcription console runner")
    parser.add_argument("--device", type=int, help="input device index")
    parser.add_argument("--file", type=Path, help="WAV file to replay instead of a device")
    parser.add_argument("--speed", type=float, default=1.0, help="replay speed multiplier")
    parser.add_argument("--loop", action="store_true", help="loop the file source")
    parser.add_argument("--duration", type=float, help="stop automatically after N seconds")
    parser.add_argument("--list-devices", action="store_true")
    args = parser.parse_args()

    cfg = load_config()

    if args.list_devices:
        devices = enumerate_inputs()
        if not devices:
            print("입력 장치를 찾을 수 없습니다.")
            guidance = loopback_guidance()
            print(f"\n[{guidance['platform']}] {guidance['title']}\n{guidance['body']}")
        for dev in devices:
            print(f"[{dev.index}] {dev.name} ({dev.kind}, {dev.channels}ch)")
        return

    engine, notice = create_engine(cfg.stt)
    if notice:
        print(f"[상태] {notice}")
    print(f"[상태] STT 엔진: {engine.describe()}")

    def on_status(level: str, message: str) -> None:
        print(f"[{level}] {message}")

    def on_partial(update: PartialUpdate) -> None:
        tag = "*" if update.synthetic else " "
        sys.stdout.write(
            f"\r{_format_ts(update.start_ms)} {update.speaker_key}{tag} … {update.text[:90]:<90}"
        )
        sys.stdout.flush()

    def on_final(draft: SegmentDraft) -> None:
        tag = "[합성]" if draft.synthetic else ""
        print(
            f"\r{_format_ts(draft.start_ms)} {draft.speaker_key} "
            f"[{draft.language or '?'}]{tag} {draft.text}"
        )

    pipeline = Pipeline(cfg, engine, on_partial=on_partial, on_final=on_final, on_status=on_status)

    if args.file:
        source = FileSource(
            args.file, cfg.audio, kind="mic", speed=args.speed, loop=args.loop, name=str(args.file)
        )
    elif args.device is not None:
        devices = {d.index: d for d in enumerate_inputs()}
        dev = devices.get(args.device)
        if dev is None:
            print(f"장치 {args.device}를 찾을 수 없습니다. --list-devices로 확인하세요.")
            return
        source = DeviceSource(dev, cfg.audio)
    else:
        print("--device 또는 --file 중 하나가 필요합니다.")
        return

    pipeline.add_channel(source, "S1", "나")
    pipeline.start()
    print("[상태] 녹음 시작. Ctrl+C로 종료.\n")

    started = time.monotonic()
    try:
        while True:
            time.sleep(0.5)
            if args.file and isinstance(source, FileSource) and source.finished.is_set() and not args.loop:
                break
            if args.duration and (time.monotonic() - started) >= args.duration:
                break
    except KeyboardInterrupt:
        pass
    finally:
        print("\n[상태] 종료 중...")
        pipeline.stop()
        snapshot = pipeline.snapshot()
        print(
            f"[상태] 총 {snapshot['elapsed_s']}s, 드롭 샘플 {snapshot['dropped_samples']} "
            f"({snapshot['dropped_seconds']}s), partial 지연 p90={snapshot['partial_latency_p90']}s"
        )


if __name__ == "__main__":
    main()
