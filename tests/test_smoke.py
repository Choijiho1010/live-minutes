"""Phase 0 스모크 — 패키지가 임포트되고 API 가 뜬다."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from liveminutes import __version__
from liveminutes.api.main import app
from liveminutes.config import MountError, Settings, require_t7


def test_health() -> None:
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "version": __version__}


def test_default_ports() -> None:
    """8501 은 다른 앱이 점유 중이라 UI 기본값은 8502 여야 한다."""
    s = Settings()
    assert s.ui_port == 8502
    assert s.api_port == 8000
    assert s.api_host == "127.0.0.1"


def test_require_t7_raises_when_absent(tmp_path: Path) -> None:
    with pytest.raises(MountError):
        require_t7(tmp_path / "없는볼륨")


def test_require_t7_returns_path(tmp_path: Path) -> None:
    assert require_t7(tmp_path) == tmp_path
