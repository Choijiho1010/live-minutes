"""API 배관 — 세션 수명주기, 증분 조회, WebSocket 오디오 수신."""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from liveminutes.api.ws import QUEUE_MAXSIZE
from liveminutes.session import SessionStore


def _pcm16(samples: np.ndarray) -> bytes:
    ints = np.clip(samples, -1.0, 1.0) * 32767
    return struct.pack(f"<{samples.size}h", *ints.astype("<i2").tolist())


def test_health(client: TestClient) -> None:
    assert client.get("/health").json()["status"] == "ok"


def test_capture_page_is_served(client: TestClient) -> None:
    """녹음 창은 API 가 직접 서빙한다 — Streamlit rerun 과 격리하기 위해(§7 ②)."""
    res = client.get("/capture")
    assert res.status_code == 200
    assert "audioWorklet" in res.text
    assert "getUserMedia" in res.text


def test_session_lifecycle(client: TestClient) -> None:
    created = client.post("/sessions")
    assert created.status_code == 201
    sid = created.json()["id"]

    assert client.get(f"/sessions/{sid}").json()["id"] == sid
    assert sid in [s["id"] for s in client.get("/sessions").json()["sessions"]]

    closed = client.post(f"/sessions/{sid}/close").json()
    assert closed["closed_at"] is not None


def test_unknown_session_is_404(client: TestClient) -> None:
    assert client.get("/sessions/없는거").status_code == 404
    assert client.post("/sessions/없는거/close").status_code == 404


def test_events_endpoint_is_incremental(client: TestClient) -> None:
    sid = client.post("/sessions").json()["id"]

    first = client.get(f"/sessions/{sid}/events").json()
    assert first["events"][0]["type"] == "session.started"

    again = client.get(f"/sessions/{sid}/events", params={"cursor": first["cursor"]}).json()
    assert again["events"] == []

    client.post(f"/sessions/{sid}/close")
    after = client.get(f"/sessions/{sid}/events", params={"cursor": first["cursor"]}).json()
    assert [e["type"] for e in after["events"]] == ["session.closed"]


def test_websocket_writes_audio_to_wav(client: TestClient, store: SessionStore) -> None:
    """✅ Phase 1 — 보낸 소리가 그대로 wav 에 남는다."""
    sid = client.post("/sessions").json()["id"]
    tone = np.sin(2 * np.pi * 440 * np.arange(16000) / 16000).astype(np.float32)

    with client.websocket_connect(f"/ws/capture?session_id={sid}") as ws:
        ws.send_json({"type": "hello", "deviceSampleRate": 48000, "targetSampleRate": 16000})
        for start in range(0, tone.size, 2048):
            ws.send_bytes(_pcm16(tone[start : start + 2048]))

    session = store.get(sid)
    assert session is not None
    assert session.capture_connected is False

    summary = client.post(f"/sessions/{sid}/close").json()
    assert summary["duration_sec"] == 1.0
    assert summary["dropped_chunks"] == 0

    data, rate = sf.read(summary["wav"], dtype="float32")
    assert rate == 16000
    assert data.shape == (16000,)
    assert float(np.max(np.abs(data - tone))) < 1e-4


def test_websocket_rejects_unknown_and_closed_session(client: TestClient) -> None:
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect("/ws/capture?session_id=없는거") as ws,
    ):
        ws.receive()

    sid = client.post("/sessions").json()["id"]
    client.post(f"/sessions/{sid}/close")
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(f"/ws/capture?session_id={sid}") as ws,
    ):
        ws.receive()


def test_close_links_debug_wav(client: TestClient, tmp_path: Path) -> None:
    """§13 검증 경로 — 마지막 세션을 늘 같은 자리에서 재생한다."""
    sid = client.post("/sessions").json()["id"]
    with client.websocket_connect(f"/ws/capture?session_id={sid}") as ws:
        ws.send_bytes(_pcm16(np.zeros(1600, dtype=np.float32)))
    summary = client.post(f"/sessions/{sid}/close").json()

    link = tmp_path / "var" / "debug.wav"
    assert link.is_symlink()
    assert link.resolve() == Path(summary["wav"]).resolve()


def test_queue_bound_is_modest() -> None:
    """상한이 없으면 서버가 밀릴 때 대기열이 무한히 쌓인다(§9 Phase 1 함정 4)."""
    assert 0 < QUEUE_MAXSIZE <= 256
