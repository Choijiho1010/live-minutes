"""FastAPI 진입점.

모델과 상태를 전부 이 프로세스가 든다(§7). Streamlit 은 화면만 그린다.
녹음 페이지도 여기서 직접 서빙한다 — Streamlit 안에 심으면 rerun 때마다
마이크 연결이 끊긴다(§7 설계판단 ②).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse

from liveminutes import __version__
from liveminutes.api import rest, ws
from liveminutes.session import store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    # 서버가 죽어도 wav 헤더는 온전해야 한다.
    app.state.store.close_all()


app = FastAPI(title="live-minutes API", version=__version__, lifespan=lifespan)
app.state.store = store
app.include_router(rest.router)
app.include_router(ws.router)


@app.get("/health")
def health() -> dict[str, Any]:
    """기동 확인용. 의존성·모델 로드 없이 즉시 응답한다."""
    return {"status": "ok", "version": __version__}


@app.get("/capture", include_in_schema=False)
def capture_page() -> FileResponse:
    """녹음 창. Streamlit 이 이 주소를 새 탭으로 연다."""
    return FileResponse(STATIC_DIR / "capture.html", media_type="text/html")
