"""오디오 링버퍼.

WebSocket 으로 들어온 16kHz mono PCM 을 고정 길이 창으로 들고 있는다.
Phase 2 의 VAD·whisper 가 "최근 N 초"를 꺼내갈 자리다. Phase 1 에서는 채우기만 한다.

부동소수(float32, -1.0..1.0) 로 보관한다. int16 원본은 wav 로 따로 흘려보내고,
여기 있는 값은 모델 입력으로 바로 쓴다.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

SAMPLE_RATE = 16_000
"""파이프라인 전체가 고정으로 쓰는 샘플레이트. whisper 가 요구하는 값이다."""


class RingBuffer:
    """최근 `capacity` 샘플만 남기는 원형 버퍼.

    스레드 안전하지 않다. 단일 소비자 태스크에서만 만진다.
    """

    def __init__(self, seconds: float, sample_rate: int = SAMPLE_RATE) -> None:
        if seconds <= 0:
            raise ValueError("seconds 는 양수여야 한다")
        self.sample_rate = sample_rate
        self.capacity = int(seconds * sample_rate)
        self._buf: NDArray[np.float32] = np.zeros(self.capacity, dtype=np.float32)
        self._write = 0
        self._filled = 0
        self._total = 0

    @property
    def total_samples(self) -> int:
        """버려진 것까지 포함해 지금까지 들어온 샘플 수. 절대 시각 계산에 쓴다."""
        return self._total

    def __len__(self) -> int:
        """현재 꺼낼 수 있는 샘플 수."""
        return self._filled

    def write(self, chunk: NDArray[np.float32]) -> None:
        """청크를 밀어 넣는다. 용량을 넘으면 오래된 것부터 덮어쓴다."""
        data = np.asarray(chunk, dtype=np.float32).ravel()
        self._total += data.size

        if data.size >= self.capacity:
            # 한 청크가 버퍼보다 크면 뒤쪽 capacity 만 남는다.
            self._buf[:] = data[-self.capacity :]
            self._write = 0
            self._filled = self.capacity
            return

        end = self._write + data.size
        if end <= self.capacity:
            self._buf[self._write : end] = data
        else:
            split = self.capacity - self._write
            self._buf[self._write :] = data[:split]
            self._buf[: end - self.capacity] = data[split:]
        self._write = end % self.capacity
        self._filled = min(self._filled + data.size, self.capacity)

    def tail(self, seconds: float) -> NDArray[np.float32]:
        """마지막 `seconds` 초를 시간 순서대로 돌려준다. 모자라면 있는 만큼."""
        want = min(int(seconds * self.sample_rate), self._filled)
        if want == 0:
            return np.zeros(0, dtype=np.float32)
        start = (self._write - want) % self.capacity
        if start + want <= self.capacity:
            return self._buf[start : start + want].copy()
        head = self._buf[start:]
        return np.concatenate([head, self._buf[: want - head.size]])
