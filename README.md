# live-minutes

**회의 중 마이크를 켜두면 자막이 실시간으로 흐르고, 누가 말했는지 이름이 붙고, 끝나면 근거가 달린 회의록이 나온다. 전부 맥미니 안에서 돈다 — 음성은 기기 밖으로 나가지 않는다.**

## 구성

| 층 | 하는 일 |
|---|---|
| **오디오 배관** | 브라우저 마이크 → 16kHz 리샘플 → WebSocket → FastAPI |
| **실시간 자막** | mlx-whisper(Apple Silicon 전용) + LocalAgreement-2 확정 정책 |
| **실시간 화자분리** | 목소리 임베딩 → 온라인 클러스터링 → 등록 DB 로 실명 매핑 |
| **AI 회의록** | LangGraph 6단계. 모든 결정에 "누가 언제 뭐라고 말했는지" 근거를 단다 |
| **합의 검증** | 서로 다른 소속의 화자 2명 이상 + 수락 발화가 있을 때만 확정으로 올린다 |

실시간 엔진은 직접 구현한다. `diart` 는 성능 비교 기준으로만 별도 환경(`.venv-diart`)에 격리 설치한다.

프로세스는 둘로 나뉜다 — **API 8000**, **UI 8502**. 둘 다 `127.0.0.1` 에만 바인딩한다(8501 은 다른 앱이 점유 중).

## 빠른 시작

전제: macOS(Apple Silicon), Python 3.12, [uv](https://docs.astral.sh/uv/), 그리고 **T7 외장 SSD 마운트**(모델 캐시가 거기 있다).

```bash
make sync-all          # 의존성 설치 (ML·UI 포함)
cp .env.example .env   # 경로·포트 설정
make api               # API  → http://127.0.0.1:8000/health
make ui                # UI   → http://127.0.0.1:8502
```

`make api` / `make ui` 는 실행 전 T7 마운트를 확인하고, 없으면 즉시 멈춘다.

### 녹음 확인 (Phase 1)

UI 사이드바에서 **회의 시작** → **🎙 녹음 창 열기** → 새 탭에서 **녹음 시작**. 10초쯤 말하고 **회의 종료**를 누른 뒤:

```bash
afplay var/debug.wav
```

`var/debug.wav` 는 마지막 세션 오디오를 가리키는 심볼릭 링크다. 오디오 본체는 `LM_DATA_DIR` 하위(T7)에 세션별로 쌓인다.

## 개발

```bash
make hooks       # 최초 1회 — pre-commit 훅 설치
make lint        # ruff 린트 + 포맷 검사
make typecheck   # mypy strict
make test        # pytest (모델·오디오 장치 불요)
make help        # 전체 타겟
```

`make sync` 는 코어 + dev 만 설치한다(CI 와 동일). 무거운 ML 스택은 `make sync-all`.

### 커밋 규율

이 레포는 **public** 이다. 실제 클라이언트 회의 오디오·회의록(`benchmark/gold/`), 목소리 임베딩(`data/`), 내부 계획서는 커밋하지 않는다. `.gitignore` 와 pre-commit 훅(`scripts/block_sensitive.sh`)이 이중으로 막는다.

## 라이선스

MIT
