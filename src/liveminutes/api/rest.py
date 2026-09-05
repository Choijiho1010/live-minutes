"""REST 엔드포인트.

Streamlit 은 여기에 1초마다 "지난번 이후 새로 나온 것"만 물어본다(§7 설계판단 ③).
전체를 매번 보내면 1시간 회의에서 초당 수 MB 가 오간다.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from liveminutes.config import settings
from liveminutes.session import Session, SessionStore
from liveminutes.session import store as default_store

log = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])


def _store(request: Request) -> SessionStore:
    store: SessionStore = getattr(request.app.state, "store", default_store)
    return store


def _require(request: Request, session_id: str) -> Session:
    session = _store(request).get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없다")
    return session


@router.post("", status_code=201)
def create_session(request: Request) -> dict[str, Any]:
    """새 회의 세션을 연다. 녹음 창은 이 id 로 WebSocket 에 붙는다."""
    session = _store(request).create()
    log.info("세션 시작 (id=%s, wav=%s)", session.id, session.wav_path)
    return session.summary()


@router.get("")
def list_sessions(request: Request) -> dict[str, Any]:
    """최근 시작한 것부터."""
    return {"sessions": [s.summary() for s in _store(request).list()]}


@router.get("/{session_id}")
def get_session(request: Request, session_id: str) -> dict[str, Any]:
    return _require(request, session_id).summary()


@router.get("/{session_id}/events")
def get_events(
    request: Request,
    session_id: str,
    cursor: int = Query(0, ge=0, description="마지막으로 받은 seq. 0 이면 처음부터"),
) -> dict[str, Any]:
    """`cursor` 이후 새로 나온 이벤트만. 응답의 `cursor` 를 다음 요청에 그대로 넣는다."""
    session = _require(request, session_id)
    events = session.events_since(cursor)
    return {
        "session_id": session.id,
        "cursor": session.cursor,
        "events": [e.as_dict() for e in events],
    }


@router.post("/{session_id}/close")
def close_session(request: Request, session_id: str) -> dict[str, Any]:
    """회의 종료. wav 를 닫고 마지막 세션을 `var/debug.wav` 로 가리킨다."""
    session = _require(request, session_id)
    session.close()
    _link_debug_wav(session)
    log.info("세션 종료 (id=%s, %.1f초)", session.id, session.duration_sec)
    return session.summary()


def _link_debug_wav(session: Session) -> None:
    """검증 편의용 심볼릭 링크. 실패해도 세션 종료를 막지 않는다.

    오디오 본체는 T7 하위에 두되(내장 SSD 여유), 재생 확인은 항상 같은 경로에서 한다.
    """
    link = settings.debug_wav
    try:
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(session.wav_path)
    except OSError as err:  # noqa: BLE001 - 링크는 부가 기능이다
        log.warning("debug wav 링크 실패 (%s): %s", link, err)
