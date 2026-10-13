"""Глобальные горячие клавиши (работают поверх других окон)."""

from __future__ import annotations

from typing import Callable

from pynput import keyboard


def parse_hotkey(hotkey: str) -> str:
    """Нормализует строку хоткея для pynput.GlobalHotKeys."""
    parts = [p.strip().lower() for p in hotkey.replace("+", " ").split() if p.strip()]
    # Поддержка формата ctrl+shift+r
    if len(parts) == 1 and "+" in hotkey:
        parts = [p.strip().lower() for p in hotkey.split("+") if p.strip()]

    mapping = {
        "ctrl": "<ctrl>",
        "control": "<ctrl>",
        "alt": "<alt>",
        "shift": "<shift>",
        "win": "<cmd>",
        "cmd": "<cmd>",
        "super": "<cmd>",
    }
    normalized: list[str] = []
    for p in parts:
        if p in mapping:
            normalized.append(mapping[p])
        elif len(p) == 1:
            normalized.append(p)
        else:
            # f1, space и т.п.
            normalized.append(f"<{p}>" if not p.startswith("<") else p)
    return "+".join(normalized)


class HotkeyManager:
    def __init__(self) -> None:
        self._listener: keyboard.GlobalHotKeys | None = None
        self._hotkey: str | None = None

    def start(self, hotkey: str, callback: Callable[[], None]) -> None:
        self.stop()
        combo = parse_hotkey(hotkey)

        def _wrapped() -> None:
            try:
                callback()
            except Exception:
                pass

        self._hotkey = combo
        self._listener = keyboard.GlobalHotKeys({combo: _wrapped})
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
