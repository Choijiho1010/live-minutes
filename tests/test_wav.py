"""PCM 변환과 wav 기록 — 들어간 소리가 그대로 나오는지."""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
import soundfile as sf

from liveminutes.audio.ring import SAMPLE_RATE
from liveminutes.audio.wav import WavWriter, pcm16_to_float32


def test_pcm16_roundtrip() -> None:
    raw = struct.pack("<4h", 0, 32767, -32768, -16384)
    out = pcm16_to_float32(raw)
    assert out.dtype == np.float32
    assert out[0] == 0.0
    assert out[1] == 32767 / 32768
    assert out[2] == -1.0
    assert out[3] == -0.5


def test_pcm16_drops_dangling_byte() -> None:
    """청크 경계에서 잘린 반쪽 프레임은 버린다 — 정렬이 밀리면 이후 전부 잡음이 된다."""
    assert pcm16_to_float32(struct.pack("<2h", 1, 2) + b"\x7f").size == 2


def test_writer_appends_and_reads_back(tmp_path: Path) -> None:
    path = tmp_path / "s" / "audio.wav"
    tone = np.sin(2 * np.pi * 440 * np.arange(SAMPLE_RATE) / SAMPLE_RATE).astype(np.float32)
    with WavWriter(path) as w:
        w.write(tone[: SAMPLE_RATE // 2])
        w.write(tone[SAMPLE_RATE // 2 :])
        assert w.frames == SAMPLE_RATE
        assert w.duration_sec == 1.0

    data, rate = sf.read(str(path), dtype="float32")
    assert rate == SAMPLE_RATE
    assert data.shape == (SAMPLE_RATE,)
    # PCM16 양자화 오차 한도 안에서 원본과 같아야 한다.
    assert float(np.max(np.abs(data - tone))) < 1e-4
