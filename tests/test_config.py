"""설정과 T7 마운트 가드."""

from __future__ import annotations

from pathlib import Path

import pytest

from liveminutes.config import MountError, Settings, require_t7


def test_default_ports() -> None:
    """8501 은 다른 앱이 점유 중이라 UI 기본값은 8502 여야 한다."""
    s = Settings()
    assert s.ui_port == 8502
    assert s.api_port == 8000
    assert s.api_host == "127.0.0.1"


def test_require_t7_raises_when_absent(tmp_path: Path) -> None:
    """모델 캐시가 외장에 있다. 마운트 없이 진행하면 수 GB 를 내장 SSD 로 다시 받는다."""
    with pytest.raises(MountError):
        require_t7(tmp_path / "없는볼륨")


def test_require_t7_returns_path(tmp_path: Path) -> None:
    assert require_t7(tmp_path) == tmp_path
