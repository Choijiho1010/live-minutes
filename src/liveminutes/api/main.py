"""FastAPI 진입점.

Phase 0 에서는 헬스체크만. 오디오 WebSocket 은 Phase 1 에서 `ws.py` 로 붙인다.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from liveminutes import __version__

app = FastAPI(title="live-minutes API", version=__version__)


@app.get("/health")
def health() -> dict[str, Any]:
    """기동 확인용. 의존성·모델 로드 없이 즉시 응답한다."""
    return {"status": "ok", "version": __version__}
