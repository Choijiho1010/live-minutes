"""WebSocket 오디오 수신.

녹음 창이 16kHz mono PCM16 을 바이너리로 밀어 넣는다. 수신 루프는 큐에 넣기만 하고,
쓰기는 별도 소비자 태스크가 맡는다.

큐에 상한이 있는 이유(§9 Phase 1 함정 4): 소비자가 밀리는데 수신을 계속 받으면
대기열이 무한히 쌓여 메모리가 터진다. 넘치면 **오래 기다리는 대신 버리고 경고한다** —
실시간 자막에서 늦게 도착한 오디오는 이미 쓸모가 없다.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from liveminutes.audio.wav import pcm16_to_float32
from liveminutes.session import Session, SessionStore
from liveminutes.session import store as default_store

log = logging.getLogger(__name__)
router = APIRouter()

QUEUE_MAXSIZE = 64
"""약 8초치(128ms 청크 기준). 이보다 밀리면 따라잡을 가망이 없다고 본다."""

STATS_EVERY_SEC = 2.0
"""이 주기로 클라이언트에 상태를 돌려주고 세션 이벤트를 남긴다."""


async def _drain(session: Session, queue: asyncio.Queue[bytes | None]) -> None:
    """큐를 비우며 링버퍼와 wav 에 쓴다. `None` 을 받으면 끝낸다."""
    while True:
        chunk = await queue.get()
        try:
            if chunk is None:
                return
            samples = pcm16_to_float32(chunk)
            # soundfile 쓰기는 블로킹이다. 이벤트 루프를 잡지 않게 스레드로 넘긴다.
            await asyncio.to_thread(session.feed, samples)
        finally:
            queue.task_done()


@router.websocket("/ws/capture")
async def capture(websocket: WebSocket) -> None:
    """녹음 창 연결. `session_id` 쿼리로 대상 세션을 지정한다."""
    store: SessionStore = getattr(websocket.app.state, "store", default_store)
    session_id = websocket.query_params.get("session_id")
    session = store.get(session_id) if session_id else None

    if session is None:
        await websocket.close(code=4404, reason="세션을 찾을 수 없다")
        return
    if session.is_closed:
        await websocket.close(code=4409, reason="이미 종료된 세션이다")
        return

    await websocket.accept()
    session.set_capture_connected(True)

    queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
    consumer = asyncio.create_task(_drain(session, queue))
    last_stats = asyncio.get_running_loop().time()

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break

            raw = message.get("bytes")
            if raw is None:
                # 텍스트 프레임은 제어용(hello). 오디오 경로와 섞지 않는다.
                _handle_control(session, message.get("text"))
                continue

            session.bytes_received += len(raw)
            try:
                queue.put_nowait(raw)
            except asyncio.QueueFull:
                session.dropped_chunks += 1
                session.emit("audio.dropped", total=session.dropped_chunks)
                log.warning(
                    "수신 큐 포화 — 청크를 버렸다 (session=%s, 누적=%d)",
                    session.id,
                    session.dropped_chunks,
                )

            now = asyncio.get_running_loop().time()
            if now - last_stats >= STATS_EVERY_SEC:
                last_stats = now
                session.emit(
                    "audio.stats",
                    duration_sec=round(session.duration_sec, 2),
                    bytes_received=session.bytes_received,
                )
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "stats",
                            "duration_sec": round(session.duration_sec, 2),
                            "server_dropped": session.dropped_chunks,
                            "cursor": session.cursor,
                        }
                    )
                )
    except WebSocketDisconnect:
        pass
    finally:
        session.set_capture_connected(False)
        await queue.put(None)
        with contextlib.suppress(asyncio.CancelledError):
            await consumer


def _handle_control(session: Session, text: str | None) -> None:
    """클라이언트 제어 프레임. 지금은 장치 샘플레이트 보고만 받는다."""
    if not text:
        return
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        log.warning("제어 프레임 파싱 실패 (session=%s)", session.id)
        return
    if payload.get("type") == "hello":
        log.info(
            "녹음 창 연결 (session=%s, 장치 %sHz → %sHz)",
            session.id,
            payload.get("deviceSampleRate"),
            payload.get("targetSampleRate"),
        )
