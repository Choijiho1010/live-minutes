# benchmark

| 디렉토리 | 내용 | 커밋 |
|---|---|---|
| `gold/` | 실제 클라이언트 회의 골든셋 (DER·회의록 품질 기준) | **금지** — `.gitignore` + pre-commit 훅으로 차단 |
| `demo/` | 공개 가능한 데모 샘플 | 가능 |
| `diart_baseline/` | 비교군(diart) 실행 스크립트 — `.venv-diart` 에서 돈다 | 가능 |

`gold/` 는 로컬에만 둔다. 수치(DER·RTF)만 결과 문서에 기록하고 원본은 올리지 않는다.
