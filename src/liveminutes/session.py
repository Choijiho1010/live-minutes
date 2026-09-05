"""세션 상태 + 증분 커서.

FastAPI 가 유일한 진실의 출처다(§7 설계판단 ③). Streamlit 은 1초마다
"지난번 이후 새로 나온 것"만 물어본다 — 매번 전체를 보내면 1시간 회의에서
초당 수 MB 가 오간다. 그래서 모든 산출물을 단조 증가 `seq` 가 붙은 이벤트로 쌓고,
클라이언트는 마지막으로 받은 seq 만 들고 다시 물어본다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from liveminutes.audio.ring import SAMPLE_RATE, RingBuffer
from liveminutes.audio.wav import WavWriter
from liveminutes.config import settings

EventType = Literal[
    "session.started",
    "audio.stats",
    "audio.dropped",
    "session.closed",
]

RING_SECONDS = 30.0
"""링버퍼 길이. Phase 2 의 재추론 창(LocalAgreement-2)이 이 안에 들어와야 한다."""


@dataclass(frozen=True, slots=True)
class Event:
    """클라이언트가 증분으로 받아가는 한 건."""

    seq: int
    type: EventType
    at: datetime
    data: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "type": self.type,
            "at": self.at.isoformat(),
            "data": self.data,
        }


@dataclass
class Session:
    """회의 하나. 오디오 싱크와 이벤트 로그를 들고 있다."""

    id: str
    started_at: datetime
    wav_path: Path
    writer: WavWriter
    ring: RingBuffer
    events: list[Event] = field(default_factory=list)
    dropped_chunks: int = 0
    bytes_received: int = 0
    closed_at: datetime | None = None
    _capture_connected: bool = False

    @property
    def is_closed(self) -> bool:
        return self.closed_at is not None

    @property
    def duration_sec(self) -> float:
        return self.writer.duration_sec

    @property
    def capture_connected(self) -> bool:
        """녹음 창이 지금 붙어 있는지. UI 가 '마이크 연결됨'을 표시하는 근거."""
        return self._capture_connected

    def set_capture_connected(self, connected: bool) -> None:
        self._capture_connected = connected

    def emit(self, type_: EventType, **data: Any) -> Event:
        """이벤트를 하나 쌓고 돌려준다. seq 는 1부터 단조 증가한다."""
        event = Event(seq=len(self.events) + 1, type=type_, at=datetime.now(UTC), data=data)
        self.events.append(event)
        return event

    def events_since(self, cursor: int) -> list[Event]:
        """`cursor` 보다 큰 seq 만. cursor 가 0 이면 처음부터."""
        if cursor <= 0:
            return list(self.events)
        return self.events[cursor:] if cursor < len(self.events) else []

    @property
    def cursor(self) -> int:
        """지금까지 발행된 마지막 seq."""
        return len(self.events)

    def feed(self, samples: NDArray[np.float32]) -> None:
        """오디오 청크를 링버퍼와 wav 양쪽에 넣는다."""
        self.ring.write(samples)
        self.writer.write(samples)

    def close(self) -> None:
        """wav 를 닫고 종료 이벤트를 남긴다. 두 번 불러도 안전하다."""
        if self.is_closed:
            return
        self.writer.close()
        self.closed_at = datetime.now(UTC)
        self._capture_connected = False
        self.emit(
            "session.closed",
            duration_sec=round(self.duration_sec, 2),
            wav=str(self.wav_path),
            dropped_chunks=self.dropped_chunks,
        )

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "started_at": self.started_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "duration_sec": round(self.duration_sec, 2),
            "sample_rate": SAMPLE_RATE,
            "wav": str(self.wav_path),
            "bytes_received": self.bytes_received,
            "dropped_chunks": self.dropped_chunks,
            "capture_connected": self.capture_connected,
            "cursor": self.cursor,
        }


class SessionStore:
    """세션 보관소. 프로세스 메모리에만 둔다 — FastAPI 가 상태를 전부 든다(§7)."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (settings.data_dir / "sessions")
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        """새 세션을 열고 wav 싱크를 준비한다."""
        session_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        wav_path = self.root / session_id / "audio.wav"
        session = Session(
            id=session_id,
            started_at=datetime.now(UTC),
            wav_path=wav_path,
            writer=WavWriter(wav_path),
            ring=RingBuffer(RING_SECONDS),
        )
        session.emit("session.started", sample_rate=SAMPLE_RATE)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def list(self) -> list[Session]:
        """최근 시작한 것부터."""
        return sorted(self._sessions.values(), key=lambda s: s.started_at, reverse=True)

    def close(self, session_id: str) -> Session | None:
        session = self.get(session_id)
        if session is not None:
            session.close()
        return session

    def close_all(self) -> None:
        for session in list(self._sessions.values()):
            session.close()


store = SessionStore()
"""프로세스 전역 보관소. 테스트는 자신의 `SessionStore` 를 만들어 주입한다."""
