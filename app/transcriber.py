"""Расшифровка аудио в текст через faster-whisper. Аудио после этого удаляется."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from faster_whisper import WhisperModel


class Transcriber:
    """Ленивая загрузка модели Whisper."""

    MODEL_CHOICES = ("tiny", "base", "small", "medium")

    def __init__(self, model_size: str = "base", language: str = "ru") -> None:
        self.model_size = model_size
        self.language = language
        self._model: WhisperModel | None = None

    def _ensure_model(self) -> WhisperModel:
        if self._model is None or getattr(self, "_loaded_size", None) != self.model_size:
            # CPU: int8 — быстрее и меньше памяти на обычных ПК
            self._model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
            )
            self._loaded_size = self.model_size
        return self._model

    def preload(self) -> None:
        self._ensure_model()

    def set_model(self, model_size: str) -> None:
        if model_size != self.model_size:
            self.model_size = model_size
            self._model = None

    def set_language(self, language: str) -> None:
        self.language = language

    def transcribe(self, wav_path: Path) -> str:
        model = self._ensure_model()
        segments, info = model.transcribe(
            str(wav_path),
            language=self.language if self.language != "auto" else None,
            vad_filter=True,
            beam_size=5,
        )
        lines: list[str] = []
        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue
            # Метка времени удобна при разборе длинного звонка
            start = _fmt_ts(seg.start)
            lines.append(f"[{start}] {text}")
        body = "\n".join(lines).strip()
        if not body:
            return "(Речь не распознана. Проверьте микрофон и громкость.)"
        lang = info.language or self.language
        header = (
            f"Диалог\n"
            f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            f"Язык: {lang}\n"
            f"{'=' * 40}\n\n"
        )
        return header + body + "\n"


def save_transcript(text: str, output_dir: Path, prefix: str = "dialog") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = output_dir / f"{prefix}_{stamp}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def delete_audio(path: Path | None) -> None:
    if path is None:
        return
    try:
        if path.exists():
            os.remove(path)
    except OSError:
        pass


def _fmt_ts(seconds: float) -> str:
    total = int(seconds)
    m, s = divmod(total, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
