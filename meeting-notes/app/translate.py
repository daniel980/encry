"""Bilingual display rules and the asynchronous translation queue.

Two responsibilities:

1. **Language rules** — decide a segment's language (inheriting when Whisper is
   unsure), measure how much of it is English, and from that decide whether the
   segment gets the two-line EN/KO treatment.
2. **Translation queue** — a background worker that batches segments and calls
   the Anthropic API. It is deliberately decoupled from transcription: a slow or
   unreachable API delays translations only, never the transcript itself. Work
   survives network outages in the queue and in SQLite, and is retried with
   capped exponential backoff until it succeeds.
"""

from __future__ import annotations

import json
import queue
import re
import threading
import time
import unicodedata
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .config import Config, LanguageConfig, SttConfig
from .store import Segment, Store

#: Runs of Latin letters, used to measure the English share of a segment.
_LATIN_RUN = re.compile(r"[A-Za-z]+")
_HANGUL = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")


def latin_ratio(text: str, min_token_len: int = 3) -> float:
    """Share of meaningful characters that are Latin letters.

    Punctuation, digits, and whitespace are excluded from both sides, and Latin
    runs shorter than ``min_token_len`` are ignored entirely so that acronyms and
    loanwords embedded in Korean ("AI", "PR", "OK") do not inflate the ratio.
    """
    if not text:
        return 0.0

    meaningful = [ch for ch in text if unicodedata.category(ch)[0] == "L"]
    if not meaningful:
        return 0.0

    latin_total = 0
    for run in _LATIN_RUN.findall(text):
        if len(run) >= min_token_len:
            latin_total += len(run)

    # Short Latin runs are excluded from the denominator too, so a Korean
    # sentence with one "AI" is measured against its Korean letters alone.
    short_latin = sum(len(r) for r in _LATIN_RUN.findall(text) if len(r) < min_token_len)
    denominator = len(meaningful) - short_latin
    if denominator <= 0:
        return 0.0
    return min(1.0, latin_total / denominator)


def has_hangul(text: str) -> bool:
    return bool(_HANGUL.search(text))


@dataclass(frozen=True)
class LanguageDecision:
    """How one segment should be labelled and displayed."""

    language: str
    inherited: bool
    en_ratio: float
    bilingual: bool
    #: Language to translate *into*; empty when the segment needs no translation.
    target_lang: str


def decide_language(
    *,
    text: str,
    detected: str,
    detected_prob: float,
    duration_s: float,
    previous_language: str,
    lang_cfg: LanguageConfig,
    stt_cfg: SttConfig,
    show_english_for_korean: bool = False,
) -> LanguageDecision:
    """Apply the bilingual display rules to one finalized segment.

    * English speech is always shown as EN原문 + KO translation.
    * Korean speech is Korean-only unless the English-companion toggle is on.
    * A Korean-labelled segment whose Latin share reaches the threshold is
      treated as code-switched and gets the bilingual treatment as well.
    * Short or low-confidence detections inherit the previous segment's language
      rather than trusting a coin-flip guess.
    """
    language = (detected or "").lower()
    inherited = False

    unreliable = (
        not language
        or detected_prob < stt_cfg.lang_prob_floor
        or duration_s < stt_cfg.lang_min_duration_s
    )
    if unreliable and previous_language:
        language = previous_language
        inherited = True
    elif unreliable and not language:
        # Nothing to inherit: fall back to the script actually present.
        language = "ko" if has_hangul(text) else "en"
        inherited = True

    ratio = latin_ratio(text, lang_cfg.min_latin_token_len)

    if language == "en":
        return LanguageDecision(language, inherited, ratio, True, "ko")

    code_switched = ratio >= lang_cfg.en_ratio_threshold
    if code_switched:
        # Mixed speech: the original line carries the English, and the second
        # line is a fully Korean rendering of the same utterance.
        return LanguageDecision(language, inherited, ratio, True, "ko")

    if language == "ko" and show_english_for_korean:
        return LanguageDecision(language, inherited, ratio, True, "en")

    return LanguageDecision(language, inherited, ratio, False, "")


_TRANSLATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "translations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "text": {"type": "string"},
                },
                "required": ["id", "text"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["translations"],
    "additionalProperties": False,
}

_SYSTEM_KO = (
    "You translate meeting speech. Preserve meaning, register, and technical terms "
    "exactly; do not summarize, expand, soften, or add commentary. Keep product names, "
    "acronyms, and identifiers in their original form. Output natural Korean suitable "
    "for meeting minutes (합니다체). Translate each numbered item independently and "
    "return one translation per input id."
)
_SYSTEM_EN = (
    "You translate meeting speech into natural English. Preserve meaning, register, and "
    "technical terms exactly; do not summarize, expand, or add commentary. Keep product "
    "names, acronyms, and identifiers in their original form. Translate each numbered "
    "item independently and return one translation per input id."
)


class TranslationQueue:
    """Batched, retrying background translator.

    Segments are grouped 3–5 per API call to keep request counts down. The worker
    never raises into the pipeline: transport failures are retried with capped
    exponential backoff, so a laptop that loses Wi-Fi mid-meeting resumes
    translating when it reconnects.
    """

    def __init__(
        self,
        cfg: Config,
        store: Store,
        on_translated: Callable[[Segment], None] | None = None,
        on_status: Callable[[str, str], None] | None = None,
    ) -> None:
        self.cfg = cfg
        self.store = store
        self.on_translated = on_translated
        self.on_status = on_status
        self._queue: queue.Queue[Segment | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._client: Any = None
        self._client_error = ""
        self.pending_count = 0
        self.failed_count = 0
        self.last_error = ""
        self.online = True
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ status

    @property
    def enabled(self) -> bool:
        return self.cfg.llm.enabled

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": self.enabled,
                "pending": self.pending_count,
                "failed": self.failed_count,
                "online": self.online,
                "error": self.last_error,
                "reason": self.disabled_reason(),
            }

    def disabled_reason(self) -> str:
        if self.cfg.llm.local_only:
            return "LOCAL_ONLY=1 — 외부 전송이 차단되어 번역과 회의록이 비활성화되었습니다."
        if not self.cfg.llm.api_key:
            return "ANTHROPIC_API_KEY가 없어 번역과 회의록이 비활성화되었습니다. 전사는 정상 동작합니다."
        return self._client_error

    # ----------------------------------------------------------------- control

    def start(self) -> None:
        if self._thread is not None or not self.enabled:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="translator", daemon=True)
        self._thread.start()

    def stop(self, drain_timeout: float = 5.0) -> None:
        self._stop.set()
        self._queue.put(None)
        if self._thread is not None:
            self._thread.join(timeout=drain_timeout)
            self._thread = None

    def enqueue(self, segment: Segment) -> None:
        """Queue one segment. Cheap and non-blocking; safe from any thread."""
        if not self.enabled or not segment.bilingual or not segment.target_lang:
            return
        with self._lock:
            self.pending_count += 1
        self._queue.put(segment)

    def enqueue_many(self, segments: Iterable[Segment]) -> None:
        for segment in segments:
            self.enqueue(segment)

    def resume_pending(self, session_id: int | None = None) -> int:
        """Re-queue translations left unfinished by a crash or an outage."""
        if not self.enabled:
            return 0
        pending = self.store.pending_translations(session_id)
        self.enqueue_many(pending)
        return len(pending)

    # ------------------------------------------------------------------ worker

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import anthropic  # noqa: PLC0415

            self._client = anthropic.Anthropic(
                api_key=self.cfg.llm.api_key,
                timeout=self.cfg.llm.timeout_s,
            )
            self._client_error = ""
        except Exception as exc:
            self._client_error = f"Anthropic 클라이언트를 만들 수 없습니다: {exc}"
            raise
        return self._client

    def _collect_batch(self) -> list[Segment]:
        """Block for one segment, then gather up to ``max_batch`` more."""
        first = self._queue.get()
        if first is None:
            return []
        batch = [first]
        deadline = time.monotonic() + self.cfg.llm.batch_linger_s

        while len(batch) < self.cfg.llm.max_batch:
            remaining = deadline - time.monotonic()
            if remaining <= 0 and len(batch) >= self.cfg.llm.min_batch:
                break
            try:
                item = self._queue.get(timeout=max(0.05, min(remaining, 0.5)))
            except queue.Empty:
                if time.monotonic() >= deadline:
                    break
                continue
            if item is None:
                self._queue.put(None)
                break
            batch.append(item)
        return batch

    def _run(self) -> None:
        backoff = 1.0
        while not self._stop.is_set():
            batch = self._collect_batch()
            if not batch:
                continue

            # Segments going to different target languages need different system
            # prompts, so translate them as separate calls.
            groups: dict[str, list[Segment]] = {}
            for segment in batch:
                groups.setdefault(segment.target_lang or "ko", []).append(segment)

            for target, group in groups.items():
                while not self._stop.is_set():
                    try:
                        self._translate_group(group, target)
                        backoff = 1.0
                        with self._lock:
                            self.online = True
                            self.last_error = ""
                        break
                    except _PermanentTranslationError as exc:
                        self._mark_failed(group, str(exc))
                        break
                    except Exception as exc:
                        with self._lock:
                            self.online = False
                            self.last_error = str(exc)
                        if self.on_status is not None:
                            self.on_status("translate", f"번역 재시도 대기 중: {exc}")
                        # Keep the work; sleep in slices so stop() stays responsive.
                        waited = 0.0
                        while waited < backoff and not self._stop.is_set():
                            time.sleep(0.2)
                            waited += 0.2
                        backoff = min(backoff * 2, 60.0)

            with self._lock:
                self.pending_count = max(0, self.pending_count - len(batch))

    def _translate_group(self, segments: list[Segment], target: str) -> None:
        client = self._ensure_client()
        system = _SYSTEM_KO if target == "ko" else _SYSTEM_EN
        payload = "\n".join(f"[{seg.id}] {seg.text}" for seg in segments)

        try:
            response = client.messages.create(
                model=self.cfg.llm.translation_model,
                max_tokens=4096,
                system=system,
                thinking={"type": "disabled"},
                output_config={
                    "effort": "low",
                    "format": {"type": "json_schema", "schema": _TRANSLATION_SCHEMA},
                },
                messages=[{"role": "user", "content": payload}],
            )
        except Exception as exc:
            raise _classify(exc) from exc

        if getattr(response, "stop_reason", "") == "refusal":
            raise _PermanentTranslationError("모델이 이 구간의 번역을 거부했습니다.")

        text = next((b.text for b in response.content if b.type == "text"), "")
        mapping = _parse_translations(text)

        for segment in segments:
            translated = mapping.get(segment.id, "").strip()
            if not translated:
                self.store.set_translation(segment.id, "", "failed")
                continue
            self.store.set_translation(segment.id, translated, "done")
            segment.translation = translated
            segment.translation_status = "done"
            if self.on_translated is not None:
                self.on_translated(segment)

    def _mark_failed(self, segments: list[Segment], reason: str) -> None:
        with self._lock:
            self.failed_count += len(segments)
            self.last_error = reason
        self.store.set_translation_status([s.id for s in segments], "failed")
        if self.on_status is not None:
            self.on_status("translate", f"번역 실패: {reason}")


class _PermanentTranslationError(RuntimeError):
    """A failure retrying cannot fix (bad key, bad request, refusal)."""


def _classify(exc: Exception) -> Exception:
    """Split retryable transport problems from permanent request problems."""
    try:
        import anthropic  # noqa: PLC0415
    except Exception:
        return exc

    if isinstance(exc, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        return _PermanentTranslationError(f"API 키 인증 실패: {exc}")
    if isinstance(exc, anthropic.NotFoundError):
        return _PermanentTranslationError(f"모델을 찾을 수 없습니다: {exc}")
    if isinstance(exc, anthropic.BadRequestError):
        return _PermanentTranslationError(f"잘못된 요청: {exc}")
    # RateLimitError, APIConnectionError, APIStatusError(5xx) → retry
    return exc


def _parse_translations(text: str) -> dict[int, str]:
    """Read the model's JSON reply, tolerating stray prose around it."""
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return {}
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}

    out: dict[int, str] = {}
    for item in data.get("translations", []):
        try:
            out[int(item["id"])] = str(item["text"])
        except (KeyError, TypeError, ValueError):
            continue
    return out
