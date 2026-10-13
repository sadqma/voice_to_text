"""Запись аудио во временный файл (удаляется после расшифровки)."""

from __future__ import annotations

import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import sounddevice as sd
from scipy.io import wavfile


@dataclass
class AudioDevice:
    index: int
    name: str
    channels: int
    sample_rate: float


def list_input_devices() -> list[AudioDevice]:
    devices: list[AudioDevice] = []
    try:
        hostapis = sd.query_hostapis()
        for i, info in enumerate(sd.query_devices()):
            if info["max_input_channels"] < 1:
                continue
            # На Windows предпочитаем WASAPI, но показываем все входы
            name = info["name"]
            try:
                api = hostapis[info["hostapi"]]["name"]
                name = f"{name} [{api}]"
            except (IndexError, KeyError, TypeError):
                pass
            devices.append(
                AudioDevice(
                    index=i,
                    name=name,
                    channels=int(info["max_input_channels"]),
                    sample_rate=float(info["default_samplerate"]),
                )
            )
    except Exception:
        pass
    return devices


class AudioRecorder:
    """Пишет микрофон в temp WAV. Аудио не сохраняется постоянно."""

    def __init__(
        self,
        sample_rate: int = 16000,
        device_index: int | None = None,
        on_level: Callable[[float], None] | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.device_index = device_index
        self.on_level = on_level
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._recording = False
        self._channels = 1

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        if self._recording:
            return

        device = self.device_index
        channels = 1
        if device is not None:
            info = sd.query_devices(device)
            channels = 1 if info["max_input_channels"] >= 1 else int(info["max_input_channels"])
            # Подстраиваем sample rate под устройство при необходимости
            try:
                sd.check_input_settings(
                    device=device,
                    channels=channels,
                    samplerate=self.sample_rate,
                    dtype="float32",
                )
            except Exception:
                self.sample_rate = int(info["default_samplerate"])

        self._channels = channels
        self._frames = []
        self._recording = True

        def callback(indata, frames, time_info, status) -> None:  # noqa: ARG001
            if not self._recording:
                return
            chunk = indata.copy()
            with self._lock:
                self._frames.append(chunk)
            if self.on_level is not None:
                mono = chunk.mean(axis=1) if chunk.ndim > 1 else chunk
                level = float(np.sqrt(np.mean(mono**2)))
                try:
                    self.on_level(min(1.0, level * 8))
                except Exception:
                    pass

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=channels,
            dtype="float32",
            device=device,
            callback=callback,
            blocksize=1024,
        )
        self._stream.start()

    def stop(self) -> Path | None:
        """Останавливает запись и возвращает путь к временному WAV (или None)."""
        if not self._recording:
            return None

        self._recording = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        with self._lock:
            frames = list(self._frames)
            self._frames = []

        if not frames:
            return None

        audio = np.concatenate(frames, axis=0)
        if audio.ndim > 1 and audio.shape[1] > 1:
            audio = audio.mean(axis=1)
        else:
            audio = audio.reshape(-1)

        # float32 → int16 для WAV
        audio = np.clip(audio, -1.0, 1.0)
        pcm = (audio * 32767).astype(np.int16)

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()
        wavfile.write(str(tmp_path), self.sample_rate, pcm)
        return tmp_path
