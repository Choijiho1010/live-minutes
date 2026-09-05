#!/usr/bin/env bash
# public 레포에 나가면 안 되는 경로를 커밋 단계에서 차단한다.
# .gitignore 는 `git add -f` 로 우회되므로 이 훅이 마지막 방어선이다.
set -euo pipefail

blocked=0
for f in "$@"; do
  case "$f" in
    benchmark/gold/*|data/*|sessions/*|PLAN.md|FIRST-PROMPT.txt|*.wav|*.flac|*.m4a|*.mp3|.env)
      echo "✗ 커밋 금지 경로: $f" >&2
      blocked=1
      ;;
  esac
done

if [ "$blocked" -ne 0 ]; then
  echo "" >&2
  echo "  이 레포는 public 이다. 클라이언트 회의 자료·오디오·내부 계획서는 커밋하지 않는다." >&2
  echo "  스테이지에서 빼라: git restore --staged <파일>" >&2
  exit 1
fi
