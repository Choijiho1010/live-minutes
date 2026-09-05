"""Streamlit 데모 UI.

화면만 그린다. 상태와 모델은 전부 FastAPI 가 든다(§7 설계판단 ①·③).
녹음 창은 이 앱 안에 심지 않는다 — rerun 때마다 마이크 연결이 끊긴다(§7 ②).
새 탭으로 여는 링크만 둔다.

Phase 1 은 배관만이다. 자막·화자 카드는 Phase 2-3 에서 이 자리에 붙는다.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import streamlit as st

API = "http://127.0.0.1:8000"
TIMEOUT = 5.0


def api_get(path: str, **params: Any) -> dict[str, Any] | None:
    try:
        res = httpx.get(f"{API}{path}", params=params, timeout=TIMEOUT)
        res.raise_for_status()
        data: dict[str, Any] = res.json()
        return data
    except httpx.HTTPError as err:
        st.session_state["api_error"] = str(err)
        return None


def api_post(path: str) -> dict[str, Any] | None:
    try:
        res = httpx.post(f"{API}{path}", timeout=TIMEOUT)
        res.raise_for_status()
        data: dict[str, Any] = res.json()
        return data
    except httpx.HTTPError as err:
        st.session_state["api_error"] = str(err)
        return None


def main() -> None:
    st.set_page_config(page_title="live-minutes", page_icon="🎙", layout="wide")
    st.session_state.setdefault("session_id", None)
    st.session_state.setdefault("cursor", 0)
    st.session_state.setdefault("events", [])
    st.session_state.setdefault("api_error", None)

    with st.sidebar:
        st.header("회의")
        if st.session_state["session_id"] is None:
            if st.button("회의 시작", type="primary", use_container_width=True):
                created = api_post("/sessions")
                if created:
                    st.session_state.update(session_id=created["id"], cursor=0, events=[])
                    st.rerun()
        else:
            sid = st.session_state["session_id"]
            st.caption(f"세션 `{sid}`")
            st.link_button(
                "🎙 녹음 창 열기", f"{API}/capture?session_id={sid}", use_container_width=True
            )
            if st.button("회의 종료", use_container_width=True):
                api_post(f"/sessions/{sid}/close")
                st.session_state["session_id"] = None
                st.rerun()

        st.divider()
        auto = st.checkbox("1초마다 갱신", value=True)
        st.caption("화자 카드는 Phase 3 에서 이 자리에 붙는다.")

    st.title("live-minutes")
    if st.session_state["api_error"]:
        st.error(f"API 연결 실패 — `make api` 가 떠 있나? ({st.session_state['api_error']})")

    sid = st.session_state["session_id"]
    if sid is None:
        st.info("사이드바에서 회의를 시작해라.")
        return

    summary = api_get(f"/sessions/{sid}")
    if summary:
        cols = st.columns(4)
        cols[0].metric("녹음 길이", f"{summary['duration_sec']:.1f} 초")
        cols[1].metric("마이크", "연결됨" if summary["capture_connected"] else "대기")
        cols[2].metric("수신", f"{summary['bytes_received'] / 1024:.0f} KB")
        cols[3].metric("버린 청크", summary["dropped_chunks"])

    incoming = api_get(f"/sessions/{sid}/events", cursor=st.session_state["cursor"])
    if incoming:
        st.session_state["cursor"] = incoming["cursor"]
        st.session_state["events"].extend(incoming["events"])

    st.subheader("이벤트")
    st.caption("Phase 1 은 배관 확인용이다. 여기에 Phase 2 부터 자막이 흐른다.")
    for event in reversed(st.session_state["events"][-40:]):
        st.text(f"[{event['seq']:>4}] {event['type']:<16} {event['data']}")

    if auto:
        time.sleep(1.0)
        st.rerun()


main()
