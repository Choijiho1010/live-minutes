.DEFAULT_GOAL := help
.PHONY: help sync sync-all fmt lint typecheck test hooks guard api ui bench

help:  ## 타겟 목록
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n",$$1,$$2}'

sync:  ## 의존성 동기화 — 코어 + dev (CI 와 동일, ML 스택 제외)
	uv sync --dev

sync-all:  ## 의존성 동기화 — ML·UI 포함 풀셋 (로컬 전용, macOS arm64)
	uv sync --dev --extra asr --extra diar --extra ui --extra minutes

fmt:  ## 포맷
	uv run ruff format .

lint:  ## 린트 + 포맷검사 (CI 게이트와 동일)
	uv run ruff check .
	uv run ruff format --check .

typecheck:  ## 타입체크
	uv run mypy

test:  ## 단위 테스트 (오디오 장치·모델 불요, CI 대상)
	uv run pytest -m "not audio and not model"

hooks:  ## pre-commit 훅 설치 (클론 후 최초 1회)
	uv run pre-commit install

guard:  ## T7 외장 SSD 마운트 확인 (모델 캐시가 거기 있다)
	@bash scripts/check_t7.sh

api: guard  ## API 서버 (FastAPI, 127.0.0.1:8000)
	uv run uvicorn liveminutes.api.main:app --reload --host 127.0.0.1 --port 8000

ui: guard  ## 데모 UI (Streamlit, 127.0.0.1:8502 — 8501 은 점유 중)
	uv run streamlit run src/liveminutes/ui/app.py \
		--server.address 127.0.0.1 --server.port 8502

bench:  ## 평가 하네스 (Phase 5 에서 구현)
	@echo "Phase 5 에서 구현한다."
