"""SQLite persistence for sessions, segments, speakers, and minutes.

Finalized segments are committed the moment they are transcribed, so a crash
loses at most the utterance in flight. WAL journaling keeps those writes from
blocking readers (the history browser reads the same file while a meeting runs).

One connection is shared behind a lock rather than one per thread: writes here
are small and infrequent relative to inference, and a single connection keeps
WAL checkpointing predictable.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

TranslationStatus = Literal["none", "pending", "done", "failed"]
SessionStatus = Literal["recording", "finished", "aborted"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    title          TEXT    NOT NULL DEFAULT '',
    started_at     REAL    NOT NULL,
    ended_at       REAL,
    status         TEXT    NOT NULL DEFAULT 'recording',
    duration_s     REAL    NOT NULL DEFAULT 0,
    audio_path     TEXT    NOT NULL DEFAULT '',
    audio_channels INTEGER NOT NULL DEFAULT 1,
    stt_engine     TEXT    NOT NULL DEFAULT '',
    synthetic      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS speakers (
    session_id INTEGER NOT NULL,
    key        TEXT    NOT NULL,
    label      TEXT    NOT NULL,
    kind       TEXT    NOT NULL DEFAULT 'unknown',
    PRIMARY KEY (session_id, key)
);

CREATE TABLE IF NOT EXISTS segments (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id         INTEGER NOT NULL,
    seq                INTEGER NOT NULL,
    speaker_key        TEXT    NOT NULL,
    channel            TEXT    NOT NULL DEFAULT '',
    start_ms           INTEGER NOT NULL,
    end_ms             INTEGER NOT NULL,
    text               TEXT    NOT NULL,
    language           TEXT    NOT NULL DEFAULT '',
    language_prob      REAL    NOT NULL DEFAULT 0,
    lang_inherited     INTEGER NOT NULL DEFAULT 0,
    en_ratio           REAL    NOT NULL DEFAULT 0,
    bilingual          INTEGER NOT NULL DEFAULT 0,
    translation        TEXT    NOT NULL DEFAULT '',
    target_lang        TEXT    NOT NULL DEFAULT '',
    translation_status TEXT    NOT NULL DEFAULT 'none',
    synthetic          INTEGER NOT NULL DEFAULT 0,
    created_at         REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS minutes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    kind       TEXT    NOT NULL,
    content    TEXT    NOT NULL,
    created_at REAL    NOT NULL,
    covers_until_ms INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_segments_session ON segments (session_id, seq);
CREATE INDEX IF NOT EXISTS idx_segments_pending ON segments (translation_status);
CREATE INDEX IF NOT EXISTS idx_minutes_session ON minutes (session_id, kind, created_at);
"""


@dataclass
class Segment:
    """A finalized utterance as stored and rendered."""

    id: int = 0
    session_id: int = 0
    seq: int = 0
    speaker_key: str = "S1"
    channel: str = ""
    start_ms: int = 0
    end_ms: int = 0
    text: str = ""
    language: str = ""
    language_prob: float = 0.0
    lang_inherited: bool = False
    en_ratio: float = 0.0
    bilingual: bool = False
    translation: str = ""
    #: Language the translation is *into*: 'ko' for English speech, 'en' for the
    #: optional Korean-to-English companion line. Empty when no translation applies.
    target_lang: str = ""
    translation_status: TranslationStatus = "none"
    synthetic: bool = False
    created_at: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["lang_inherited"] = bool(self.lang_inherited)
        data["bilingual"] = bool(self.bilingual)
        data["synthetic"] = bool(self.synthetic)
        return data


@dataclass
class Session:
    """A meeting, live or finished."""

    id: int = 0
    title: str = ""
    started_at: float = 0.0
    ended_at: float | None = None
    status: SessionStatus = "recording"
    duration_s: float = 0.0
    audio_path: str = ""
    audio_channels: int = 1
    stt_engine: str = ""
    synthetic: bool = False
    speakers: dict[str, str] = field(default_factory=dict)
    segment_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["synthetic"] = bool(self.synthetic)
        data["has_audio"] = bool(self.audio_path)
        return data


def _row_to_segment(row: sqlite3.Row) -> Segment:
    return Segment(
        id=row["id"],
        session_id=row["session_id"],
        seq=row["seq"],
        speaker_key=row["speaker_key"],
        channel=row["channel"],
        start_ms=row["start_ms"],
        end_ms=row["end_ms"],
        text=row["text"],
        language=row["language"],
        language_prob=row["language_prob"],
        lang_inherited=bool(row["lang_inherited"]),
        en_ratio=row["en_ratio"],
        bilingual=bool(row["bilingual"]),
        translation=row["translation"],
        target_lang=row["target_lang"],
        translation_status=row["translation_status"],
        synthetic=bool(row["synthetic"]),
        created_at=row["created_at"],
    )


class Store:
    """Thread-safe CRUD over the session database."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.commit()
            finally:
                self._conn.close()

    # ---------------------------------------------------------------- sessions

    def create_session(
        self,
        title: str,
        *,
        audio_path: str = "",
        audio_channels: int = 1,
        stt_engine: str = "",
        synthetic: bool = False,
    ) -> Session:
        now = time.time()
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO sessions (title, started_at, status, audio_path, "
                "audio_channels, stt_engine, synthetic) VALUES (?,?,?,?,?,?,?)",
                (title, now, "recording", audio_path, audio_channels, stt_engine, int(synthetic)),
            )
            self._conn.commit()
            session_id = int(cur.lastrowid or 0)
        return Session(
            id=session_id,
            title=title,
            started_at=now,
            status="recording",
            audio_path=audio_path,
            audio_channels=audio_channels,
            stt_engine=stt_engine,
            synthetic=synthetic,
        )

    def finish_session(
        self, session_id: int, duration_s: float, status: SessionStatus = "finished"
    ) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE sessions SET ended_at=?, duration_s=?, status=? WHERE id=?",
                (time.time(), duration_s, status, session_id),
            )
            self._conn.commit()

    def update_session_title(self, session_id: int, title: str) -> None:
        with self._lock:
            self._conn.execute("UPDATE sessions SET title=? WHERE id=?", (title, session_id))
            self._conn.commit()

    def set_session_audio(self, session_id: int, audio_path: str, channels: int) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE sessions SET audio_path=?, audio_channels=? WHERE id=?",
                (audio_path, channels, session_id),
            )
            self._conn.commit()

    def get_session(self, session_id: int) -> Session | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM sessions WHERE id=?", (session_id,)
            ).fetchone()
            if row is None:
                return None
            count = self._conn.execute(
                "SELECT COUNT(*) AS c FROM segments WHERE session_id=?", (session_id,)
            ).fetchone()["c"]
        session = self._session_from_row(row)
        session.segment_count = int(count)
        session.speakers = self.get_speakers(session_id)
        return session

    def list_sessions(self, limit: int = 100) -> list[Session]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT s.*, (SELECT COUNT(*) FROM segments g WHERE g.session_id = s.id) "
                "AS segment_count FROM sessions s ORDER BY s.started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        sessions: list[Session] = []
        for row in rows:
            session = self._session_from_row(row)
            session.segment_count = int(row["segment_count"])
            sessions.append(session)
        return sessions

    def delete_session(self, session_id: int) -> str:
        """Remove a session and its rows; returns the audio path for cleanup."""
        with self._lock:
            row = self._conn.execute(
                "SELECT audio_path FROM sessions WHERE id=?", (session_id,)
            ).fetchone()
            audio_path = str(row["audio_path"]) if row else ""
            self._conn.execute("DELETE FROM segments WHERE session_id=?", (session_id,))
            self._conn.execute("DELETE FROM speakers WHERE session_id=?", (session_id,))
            self._conn.execute("DELETE FROM minutes WHERE session_id=?", (session_id,))
            self._conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
            self._conn.commit()
        return audio_path

    def recover_stale_sessions(self) -> list[int]:
        """Mark sessions left in 'recording' by a crash as aborted.

        Their segments and audio remain intact and browsable — this only stops
        the history list from showing a meeting that is no longer running.
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT id FROM sessions WHERE status='recording'"
            ).fetchall()
            ids = [int(r["id"]) for r in rows]
            if ids:
                self._conn.execute(
                    "UPDATE sessions SET status='aborted', ended_at=COALESCE(ended_at, ?), "
                    "duration_s = COALESCE((SELECT MAX(end_ms)/1000.0 FROM segments "
                    "WHERE segments.session_id = sessions.id), duration_s) "
                    "WHERE status='recording'",
                    (time.time(),),
                )
                self._conn.commit()
        return ids

    def _session_from_row(self, row: sqlite3.Row) -> Session:
        return Session(
            id=row["id"],
            title=row["title"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            status=row["status"],
            duration_s=row["duration_s"],
            audio_path=row["audio_path"],
            audio_channels=row["audio_channels"],
            stt_engine=row["stt_engine"],
            synthetic=bool(row["synthetic"]),
        )

    # ---------------------------------------------------------------- speakers

    def upsert_speaker(self, session_id: int, key: str, label: str, kind: str = "unknown") -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO speakers (session_id, key, label, kind) VALUES (?,?,?,?) "
                "ON CONFLICT(session_id, key) DO UPDATE SET label=excluded.label",
                (session_id, key, label, kind),
            )
            self._conn.commit()

    def get_speakers(self, session_id: int) -> dict[str, str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT key, label FROM speakers WHERE session_id=? ORDER BY key", (session_id,)
            ).fetchall()
        return {row["key"]: row["label"] for row in rows}

    def get_speaker_kinds(self, session_id: int) -> dict[str, str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT key, kind FROM speakers WHERE session_id=?", (session_id,)
            ).fetchall()
        return {row["key"]: row["kind"] for row in rows}

    # ---------------------------------------------------------------- segments

    def add_segment(self, segment: Segment) -> Segment:
        segment.created_at = segment.created_at or time.time()
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO segments (session_id, seq, speaker_key, channel, start_ms, end_ms, "
                "text, language, language_prob, lang_inherited, en_ratio, bilingual, translation, "
                "target_lang, translation_status, synthetic, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    segment.session_id,
                    segment.seq,
                    segment.speaker_key,
                    segment.channel,
                    segment.start_ms,
                    segment.end_ms,
                    segment.text,
                    segment.language,
                    segment.language_prob,
                    int(segment.lang_inherited),
                    segment.en_ratio,
                    int(segment.bilingual),
                    segment.translation,
                    segment.target_lang,
                    segment.translation_status,
                    int(segment.synthetic),
                    segment.created_at,
                ),
            )
            self._conn.commit()
            segment.id = int(cur.lastrowid or 0)
        return segment

    def list_segments(self, session_id: int, after_seq: int = -1) -> list[Segment]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM segments WHERE session_id=? AND seq>? ORDER BY seq",
                (session_id, after_seq),
            ).fetchall()
        return [_row_to_segment(row) for row in rows]

    def update_segment_text(self, segment_id: int, text: str) -> None:
        with self._lock:
            self._conn.execute("UPDATE segments SET text=? WHERE id=?", (text, segment_id))
            self._conn.commit()

    def set_translation(
        self, segment_id: int, translation: str, status: TranslationStatus = "done"
    ) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE segments SET translation=?, translation_status=? WHERE id=?",
                (translation, status, segment_id),
            )
            self._conn.commit()

    def set_translation_status(self, segment_ids: Iterable[int], status: TranslationStatus) -> None:
        ids = list(segment_ids)
        if not ids:
            return
        with self._lock:
            self._conn.executemany(
                "UPDATE segments SET translation_status=? WHERE id=?",
                [(status, sid) for sid in ids],
            )
            self._conn.commit()

    def pending_translations(self, session_id: int | None = None) -> list[Segment]:
        """Segments that still need a translation.

        Called on startup and on network recovery so that work queued while the
        API was unreachable is retried instead of silently lost.
        """
        query = (
            "SELECT * FROM segments WHERE bilingual=1 AND translation_status IN "
            "('pending','failed')"
        )
        params: tuple[Any, ...] = ()
        if session_id is not None:
            query += " AND session_id=?"
            params = (session_id,)
        query += " ORDER BY session_id, seq"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [_row_to_segment(row) for row in rows]

    def request_translations(self, session_id: int, source_lang: str, target_lang: str) -> list[Segment]:
        """Mark segments of ``source_lang`` as needing a ``target_lang`` translation.

        Backs the "영어 병기" toggle: turning it on asks for Korean segments to be
        rendered in English too, without re-running any of the transcription.
        """
        with self._lock:
            self._conn.execute(
                "UPDATE segments SET bilingual=1, target_lang=?, translation_status='pending' "
                "WHERE session_id=? AND language=? AND translation_status='none'",
                (target_lang, session_id, source_lang),
            )
            self._conn.commit()
            rows = self._conn.execute(
                "SELECT * FROM segments WHERE session_id=? AND language=? AND target_lang=? "
                "AND translation_status='pending' ORDER BY seq",
                (session_id, source_lang, target_lang),
            ).fetchall()
        return [_row_to_segment(row) for row in rows]

    def rename_speaker_everywhere(self, session_id: int, key: str, label: str) -> int:
        """Rename a speaker; segments reference the key, so history follows."""
        self.upsert_speaker(session_id, key, label)
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS c FROM segments WHERE session_id=? AND speaker_key=?",
                (session_id, key),
            ).fetchone()
        return int(row["c"])

    # ----------------------------------------------------------------- minutes

    def add_minutes(
        self, session_id: int, kind: str, content: str, covers_until_ms: int = 0
    ) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO minutes (session_id, kind, content, created_at, covers_until_ms) "
                "VALUES (?,?,?,?,?)",
                (session_id, kind, content, time.time(), covers_until_ms),
            )
            self._conn.commit()
            return int(cur.lastrowid or 0)

    def latest_minutes(self, session_id: int, kind: str) -> str:
        with self._lock:
            row = self._conn.execute(
                "SELECT content FROM minutes WHERE session_id=? AND kind=? "
                "ORDER BY created_at DESC LIMIT 1",
                (session_id, kind),
            ).fetchone()
        return str(row["content"]) if row else ""
