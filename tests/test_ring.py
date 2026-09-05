"""링버퍼 — 덮어쓰기와 꼬리 추출이 시간 순서를 지키는지."""

from __future__ import annotations

import numpy as np
import pytest

from liveminutes.audio.ring import RingBuffer


def test_tail_keeps_order() -> None:
    ring = RingBuffer(seconds=1.0, sample_rate=10)
    ring.write(np.arange(4, dtype=np.float32))
    assert ring.tail(1.0).tolist() == [0, 1, 2, 3]


def test_overwrites_oldest_and_wraps() -> None:
    ring = RingBuffer(seconds=1.0, sample_rate=10)
    ring.write(np.arange(8, dtype=np.float32))
    ring.write(np.arange(8, 14, dtype=np.float32))  # 랩어라운드 발생
    assert len(ring) == 10
    assert ring.tail(1.0).tolist() == list(range(4, 14))
    assert ring.total_samples == 14


def test_chunk_larger_than_capacity_keeps_newest() -> None:
    ring = RingBuffer(seconds=1.0, sample_rate=10)
    ring.write(np.arange(25, dtype=np.float32))
    assert ring.tail(1.0).tolist() == list(range(15, 25))


def test_tail_shorter_than_requested() -> None:
    ring = RingBuffer(seconds=1.0, sample_rate=10)
    ring.write(np.arange(3, dtype=np.float32))
    assert ring.tail(1.0).tolist() == [0, 1, 2]
    assert ring.tail(0.0).size == 0


def test_rejects_nonpositive_length() -> None:
    with pytest.raises(ValueError):
        RingBuffer(seconds=0)
