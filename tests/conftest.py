"""테스트 공용 픽스처. 세션 보관소를 tmp 로 갈아끼워 T7 과 프로젝트를 건드리지 않는다."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from liveminutes.api.main import app
from liveminutes.session import SessionStore


@pytest.fixture
def store(tmp_path: Path) -> SessionStore:
    return SessionStore(root=tmp_path / "sessions")


@pytest.fixture
def client(
    store: SessionStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    from liveminutes.config import settings

    monkeypatch.setattr(settings, "debug_wav", tmp_path / "var" / "debug.wav")
    app.state.store = store
    with TestClient(app) as c:
        yield c
    store.close_all()
