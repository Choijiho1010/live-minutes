"""세션 오디오를 wav 로 흘려 쓴다.

전량 메모리에 들고 있다가 마지막에 저장하면 1시간 회의에서 수백 MB 를 잡는다.
받는 즉시 파일로 밀어내고, 메모리에는 링버퍼 몫만 남긴다.
"""

from __future__ import annotations

from pathlib import Path
from types import TracebackType

import numpy as np
import soundfile as sf
from numpy.typing import NDArray

from liveminutes.audio.ring import SAMPLE_RATE


class WavWriter:
    """16kHz mono PCM16 wav 를 이어 쓴다. 컨텍스트 매니저로 쓴다."""

    def __init__(self, path: Path, sample_rate: int = SAMPLE_RATE) -> None:
        self.path = path
        self.sample_rate = sample_rate
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._sf = sf.SoundFile(
            str(self.path),
            mode="w",
            samplerate=sample_rate,
            channels=1,
            subtype="PCM_16",
        )
        self._frames = 0

    @property
    def frames(self) -> int:
        """지금까지 쓴 샘플 수."""
        return self._frames

    @property
    def duration_sec(self) -> float:
        """지금까지 쓴 길이(초)."""
        return self._frames / self.sample_rate

    def write(self, chunk: NDArray[np.float32]) -> None:
        data = np.asarray(chunk, dtype=np.float32).ravel()
        self._sf.write(data)
        self._frames += data.size

    def close(self) -> None:
        if not self._sf.closed:
            self._sf.close()

    def __enter__(self) -> WavWriter:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


def pcm16_to_float32(raw: bytes) -> NDArray[np.float32]:
    """WebSocket 으로 온 little-endian int16 바이트를 -1.0..1.0 float32 로 바꾼다.

    홀수 바이트(청크 경계에서 잘린 프레임)는 버린다. 한 샘플 손실은 들리지 않지만
    정렬이 밀리면 이후 전부가 잡음이 된다.
    """
    usable = len(raw) - (len(raw) % 2)
    ints = np.frombuffer(raw[:usable], dtype="<i2")
    return (ints.astype(np.float32) / 32768.0).copy()
