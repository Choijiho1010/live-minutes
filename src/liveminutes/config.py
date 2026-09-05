"""런타임 설정 — 포트·경로·모델 캐시 위치.

값은 `.env`(있으면) → 환경변수 → 기본값 순으로 읽는다. `.env.example` 참고.
무거운 산출물(모델 가중치·세션 오디오)은 내장 SSD 여유가 빠듯해 전부 T7 외장 SSD 하위에 둔다.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class MountError(RuntimeError):
    """모델 캐시가 있는 외장 SSD 가 마운트되지 않았다."""


class Settings(BaseSettings):
    """환경 설정. 접두사 `LM_` 를 붙인 환경변수로 덮어쓴다."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LM_",
        extra="ignore",
    )

    # 포트 — 8501 은 다른 앱이 점유 중이라 UI 는 8502 를 쓴다.
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    ui_port: int = 8502

    # 외장 SSD. 모델 가중치와 세션 오디오가 여기 있다.
    t7_root: Path = Path("/Volumes/T7")
    data_dir: Path = Path("/Volumes/T7/live-minutes/data")


settings = Settings()


def require_t7(root: Path | None = None) -> Path:
    """T7 마운트를 확인하고 경로를 돌려준다. 없으면 `MountError`.

    모델 캐시가 외장에 있어 마운트 없이 진행하면 수 GB 를 내장 SSD 로 다시 받는다.
    그 사고를 막기 위해 진입점에서 먼저 부른다.
    """
    target = root or settings.t7_root
    if not target.is_dir():
        raise MountError(
            f"외장 SSD 가 마운트되지 않았다: {target}\n"
            "모델 캐시가 이 볼륨에 있다. 연결한 뒤 다시 실행해라."
        )
    return target
