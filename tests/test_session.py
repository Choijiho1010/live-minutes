"""세션 상태 + 증분 커서 — 같은 이벤트를 두 번 주지도, 빠뜨리지도 않는지."""

from __future__ import annotations

import numpy as np

from liveminutes.audio.ring import SAMPLE_RATE
from liveminutes.session import SessionStore


def test_started_event_and_cursor(store: SessionStore) -> None:
    s = store.create()
    assert s.cursor == 1
    assert s.events[0].type == "session.started"
    assert s.events[0].seq == 1


def test_events_since_is_incremental(store: SessionStore) -> None:
    s = store.create()
    cursor = s.cursor
    s.emit("audio.stats", duration_sec=1.0)
    s.emit("audio.stats", duration_sec=2.0)

    fresh = s.events_since(cursor)
    assert [e.seq for e in fresh] == [2, 3]
    # 같은 커서로 다시 물어보면 같은 것을 준다(재요청 안전)
    assert [e.seq for e in s.events_since(cursor)] == [2, 3]
    # 갱신된 커서로는 아무것도 없다
    assert s.events_since(s.cursor) == []


def test_events_since_zero_returns_all(store: SessionStore) -> None:
    s = store.create()
    s.emit("audio.stats")
    assert len(s.events_since(0)) == 2


def test_feed_writes_both_sinks(store: SessionStore) -> None:
    s = store.create()
    s.feed(np.zeros(SAMPLE_RATE // 2, dtype=np.float32))
    assert s.duration_sec == 0.5
    assert len(s.ring) == SAMPLE_RATE // 2


def test_close_is_idempotent(store: SessionStore) -> None:
    s = store.create()
    s.feed(np.zeros(SAMPLE_RATE, dtype=np.float32))
    s.close()
    cursor = s.cursor
    s.close()
    assert s.cursor == cursor
    assert s.is_closed
    assert s.events[-1].type == "session.closed"
    assert s.events[-1].data["duration_sec"] == 1.0
    assert s.wav_path.exists()


def test_store_lists_newest_first(store: SessionStore) -> None:
    a = store.create()
    b = store.create()
    assert [s.id for s in store.list()][0] in {a.id, b.id}
    assert len(store.list()) == 2
