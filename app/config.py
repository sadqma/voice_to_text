"""Настройки приложения."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

APP_NAME = "Voice to Text"
DEFAULT_HOTKEY = "ctrl+shift+r"
DEFAULT_MODEL = "base"
DEFAULT_LANGUAGE = "ru"


def _default_output_dir() -> Path:
    docs = Path.home() / "Documents" / "Dialogs"
    docs.mkdir(parents=True, exist_ok=True)
    return docs


def _config_path() -> Path:
    cfg_dir = Path.home() / ".voice_to_text"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "config.json"


DEFAULTS: dict[str, Any] = {
    "output_dir": str(_default_output_dir()),
    "hotkey": DEFAULT_HOTKEY,
    "whisper_model": DEFAULT_MODEL,
    "language": DEFAULT_LANGUAGE,
    "device_index": None,  # None = устройство по умолчанию
    "sample_rate": 16000,
    "auto_open_folder": False,
    "copy_to_clipboard": True,
}


class Config:
    def __init__(self) -> None:
        self._path = _config_path()
        self._data = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        if self._path.exists():
            try:
                loaded = json.loads(self._path.read_text(encoding="utf-8"))
                self._data.update({k: v for k, v in loaded.items() if k in DEFAULTS})
            except (json.JSONDecodeError, OSError):
                pass
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def save(self) -> None:
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get(self, key: str) -> Any:
        return self._data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    @property
    def output_dir(self) -> str:
        return self._data["output_dir"]

    @output_dir.setter
    def output_dir(self, value: str) -> None:
        self.set("output_dir", value)

    @property
    def hotkey(self) -> str:
        return self._data["hotkey"]

    @hotkey.setter
    def hotkey(self, value: str) -> None:
        self.set("hotkey", value)

    @property
    def whisper_model(self) -> str:
        return self._data["whisper_model"]

    @whisper_model.setter
    def whisper_model(self, value: str) -> None:
        self.set("whisper_model", value)

    @property
    def language(self) -> str:
        return self._data["language"]

    @language.setter
    def language(self, value: str) -> None:
        self.set("language", value)

    @property
    def device_index(self) -> int | None:
        return self._data["device_index"]

    @device_index.setter
    def device_index(self, value: int | None) -> None:
        self.set("device_index", value)

    @property
    def sample_rate(self) -> int:
        return int(self._data["sample_rate"])

    @property
    def auto_open_folder(self) -> bool:
        return bool(self._data["auto_open_folder"])

    @auto_open_folder.setter
    def auto_open_folder(self, value: bool) -> None:
        self.set("auto_open_folder", value)

    @property
    def copy_to_clipboard(self) -> bool:
        return bool(self._data["copy_to_clipboard"])

    @copy_to_clipboard.setter
    def copy_to_clipboard(self, value: bool) -> None:
        self.set("copy_to_clipboard", value)
