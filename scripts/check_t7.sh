#!/usr/bin/env bash
# T7 외장 SSD 마운트 가드.
# 모델 가중치(수 GB)와 HF 캐시가 이 볼륨에 있다. 마운트 없이 실행하면
# 내장 SSD 로 전부 다시 내려받아 여유 공간을 날린다. 그래서 즉시 종료한다.
set -euo pipefail

T7_ROOT="${LM_T7_ROOT:-/Volumes/T7}"

if [ ! -d "$T7_ROOT" ]; then
  echo "✗ 외장 SSD 가 마운트되지 않았다: $T7_ROOT" >&2
  echo "  모델 캐시가 이 볼륨에 있다. 연결한 뒤 다시 실행해라." >&2
  echo "  (다른 경로를 쓰려면 LM_T7_ROOT 를 설정)" >&2
  exit 1
fi

echo "✓ T7 마운트 확인: $T7_ROOT"
