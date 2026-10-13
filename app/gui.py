"""Главное окно приложения."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.config import APP_NAME, Config
from app.hotkeys import HotkeyManager
from app.recorder import AudioRecorder, list_input_devices
from app.transcriber import Transcriber, delete_audio, save_transcript


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("520x640")
        self.minsize(480, 560)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.config = Config()
        self.transcriber = Transcriber(
            model_size=self.config.whisper_model,
            language=self.config.language,
        )
        self.recorder = AudioRecorder(
            sample_rate=self.config.sample_rate,
            device_index=self.config.device_index,
            on_level=self._on_level,
        )
        self.hotkeys = HotkeyManager()
        self._busy = False
        self._last_txt: Path | None = None
        self._pulse = 0

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(200, self._boot)

    # ── UI ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        pad = {"padx": 20, "pady": 8}

        header = ctk.CTkLabel(
            self,
            text="Voice to Text",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        header.pack(pady=(24, 4))

        self.subtitle = ctk.CTkLabel(
            self,
            text="Разговор → TXT",
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray70"),
        )
        self.subtitle.pack(pady=(0, 12))

        self.status_label = ctk.CTkLabel(
            self,
            text="Готов к записи",
            font=ctk.CTkFont(size=15),
        )
        self.status_label.pack(**pad)

        self.level = ctk.CTkProgressBar(self, width=360, height=8)
        self.level.set(0)
        self.level.pack(pady=(0, 16))

        self.rec_btn = ctk.CTkButton(
            self,
            text="●  Начать запись",
            width=280,
            height=56,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color="#c0392b",
            hover_color="#a93226",
            command=self.toggle_recording,
        )
        self.rec_btn.pack(pady=8)

        self.hotkey_hint = ctk.CTkLabel(
            self,
            text=f"Горячая клавиша: {self.config.hotkey.upper()}",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
        )
        self.hotkey_hint.pack(pady=(0, 16))

        # Настройки
        settings = ctk.CTkFrame(self)
        settings.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(settings, text="Микрофон", anchor="w").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )
        self.device_var = ctk.StringVar(value="По умолчанию")
        self.device_menu = ctk.CTkOptionMenu(
            settings, variable=self.device_var, values=["По умолчанию"], width=340
        )
        self.device_menu.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(settings, text="Модель Whisper", anchor="w").grid(
            row=2, column=0, sticky="w", padx=12, pady=(4, 4)
        )
        self.model_var = ctk.StringVar(value=self.config.whisper_model)
        model_menu = ctk.CTkOptionMenu(
            settings,
            variable=self.model_var,
            values=list(Transcriber.MODEL_CHOICES),
            width=160,
            command=self._on_model_change,
        )
        model_menu.grid(row=3, column=0, padx=12, pady=(0, 8), sticky="w")

        ctk.CTkLabel(settings, text="Язык", anchor="w").grid(
            row=2, column=1, sticky="w", padx=12, pady=(4, 4)
        )
        self.lang_var = ctk.StringVar(value=self.config.language)
        lang_menu = ctk.CTkOptionMenu(
            settings,
            variable=self.lang_var,
            values=["ru", "en", "auto"],
            width=120,
            command=self._on_lang_change,
        )
        lang_menu.grid(row=3, column=1, padx=12, pady=(0, 8), sticky="w")

        ctk.CTkLabel(settings, text="Папка с TXT", anchor="w").grid(
            row=4, column=0, sticky="w", padx=12, pady=(4, 4)
        )
        folder_row = ctk.CTkFrame(settings, fg_color="transparent")
        folder_row.grid(row=5, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew")
        self.folder_label = ctk.CTkLabel(
            folder_row,
            text=self.config.output_dir,
            anchor="w",
            width=280,
            wraplength=280,
        )
        self.folder_label.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(folder_row, text="…", width=36, command=self._pick_folder).pack(
            side="right", padx=(8, 0)
        )

        self.copy_var = ctk.BooleanVar(value=self.config.copy_to_clipboard)
        ctk.CTkCheckBox(
            settings,
            text="Копировать текст в буфер после расшифровки",
            variable=self.copy_var,
            command=self._on_copy_toggle,
        ).grid(row=6, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 12))

        settings.grid_columnconfigure(0, weight=1)
        settings.grid_columnconfigure(1, weight=0)

        # Действия с последним файлом
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=12)
        self.open_btn = ctk.CTkButton(
            actions, text="Открыть TXT", width=140, state="disabled", command=self._open_last
        )
        self.open_btn.pack(side="left", padx=(0, 8))
        self.folder_btn = ctk.CTkButton(
            actions, text="Открыть папку", width=140, command=self._open_folder
        )
        self.folder_btn.pack(side="left", padx=8)
        self.copy_btn = ctk.CTkButton(
            actions,
            text="Копировать",
            width=120,
            state="disabled",
            command=self._copy_last,
        )
        self.copy_btn.pack(side="left", padx=8)

    # ── Boot ────────────────────────────────────────────────────────

    def _boot(self) -> None:
        self._refresh_devices()
        self._start_hotkey()
        self._set_status("Загрузка модели Whisper (первый раз может занять минуту)…")
        threading.Thread(target=self._preload_model, daemon=True).start()

    def _preload_model(self) -> None:
        try:
            self.transcriber.preload()
            self.after(0, lambda: self._set_status("Готов к записи"))
        except Exception as exc:
            self.after(
                0,
                lambda: self._set_status(f"Ошибка загрузки модели: {exc}"),
            )

    def _refresh_devices(self) -> None:
        devices = list_input_devices()
        names = ["По умолчанию"] + [d.name for d in devices]
        self._devices = devices
        self.device_menu.configure(values=names)

        current = self.config.device_index
        if current is None:
            self.device_var.set("По умолчанию")
        else:
            match = next((d for d in devices if d.index == current), None)
            self.device_var.set(match.name if match else "По умолчанию")

        self.device_menu.configure(command=self._on_device_change)

    def _start_hotkey(self) -> None:
        try:
            self.hotkeys.start(self.config.hotkey, self._hotkey_toggle)
            self.hotkey_hint.configure(text=f"Горячая клавиша: {self.config.hotkey.upper()}")
        except Exception as exc:
            self.hotkey_hint.configure(text=f"Хоткей недоступен: {exc}")

    # ── Recording ───────────────────────────────────────────────────

    def _hotkey_toggle(self) -> None:
        # Вызов из потока pynput → в UI-поток
        self.after(0, self.toggle_recording)

    def toggle_recording(self) -> None:
        if self._busy:
            return
        if self.recorder.is_recording:
            self._stop_and_transcribe()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        try:
            self.recorder.device_index = self._selected_device_index()
            self.recorder.start()
        except Exception as exc:
            messagebox.showerror("Микрофон", f"Не удалось начать запись:\n{exc}")
            return

        self.rec_btn.configure(
            text="■  Остановить",
            fg_color="#27ae60",
            hover_color="#1e8449",
        )
        self._set_status("Идёт запись…")
        self._pulse = 0
        self._animate_rec()

    def _stop_and_transcribe(self) -> None:
        self._busy = True
        self.rec_btn.configure(state="disabled", text="Расшифровка…")
        self._set_status("Остановка записи…")
        self.level.set(0)

        def worker() -> None:
            wav = None
            try:
                wav = self.recorder.stop()
                if wav is None:
                    self.after(0, lambda: self._finish_cycle("Пустая запись — ничего не сохранено"))
                    return

                self.after(0, lambda: self._set_status("Расшифровка речи…"))
                text = self.transcriber.transcribe(wav)
                out = save_transcript(text, Path(self.config.output_dir))
                self._last_txt = out

                if self.config.copy_to_clipboard:
                    # буфер обмена только из UI-потока
                    body = text
                    self.after(0, lambda: self._clipboard_set(body))

                self.after(0, lambda: self._finish_ok(out))
            except Exception as exc:
                self.after(0, lambda: self._finish_cycle(f"Ошибка: {exc}"))
            finally:
                delete_audio(wav)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_ok(self, path: Path) -> None:
        self._busy = False
        self.rec_btn.configure(
            state="normal",
            text="●  Начать запись",
            fg_color="#c0392b",
            hover_color="#a93226",
        )
        self.open_btn.configure(state="normal")
        self.copy_btn.configure(state="normal")
        self._set_status(f"Сохранено: {path.name}")

    def _finish_cycle(self, message: str) -> None:
        self._busy = False
        self.rec_btn.configure(
            state="normal",
            text="●  Начать запись",
            fg_color="#c0392b",
            hover_color="#a93226",
        )
        self._set_status(message)

    def _animate_rec(self) -> None:
        if not self.recorder.is_recording:
            return
        self._pulse = (self._pulse + 1) % 2
        dots = "." * (self._pulse + 1)
        self._set_status(f"Идёт запись{dots}")
        self.after(500, self._animate_rec)

    def _on_level(self, level: float) -> None:
        self.after(0, lambda: self.level.set(level))

    # ── Settings handlers ───────────────────────────────────────────

    def _selected_device_index(self) -> int | None:
        name = self.device_var.get()
        if name == "По умолчанию":
            return None
        for d in getattr(self, "_devices", []):
            if d.name == name:
                return d.index
        return None

    def _on_device_change(self, _value: str) -> None:
        idx = self._selected_device_index()
        self.config.device_index = idx
        self.recorder.device_index = idx

    def _on_model_change(self, value: str) -> None:
        self.config.whisper_model = value
        self.transcriber.set_model(value)
        self._set_status("Загрузка новой модели…")
        threading.Thread(target=self._preload_model, daemon=True).start()

    def _on_lang_change(self, value: str) -> None:
        self.config.language = value
        self.transcriber.set_language(value)

    def _on_copy_toggle(self) -> None:
        self.config.copy_to_clipboard = bool(self.copy_var.get())

    def _pick_folder(self) -> None:
        path = filedialog.askdirectory(initialdir=self.config.output_dir)
        if path:
            self.config.output_dir = path
            self.folder_label.configure(text=path)

    # ── File actions ────────────────────────────────────────────────

    def _clipboard_set(self, text: str) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
        except Exception:
            pass

    def _open_last(self) -> None:
        if self._last_txt and self._last_txt.exists():
            self._open_path(self._last_txt)

    def _copy_last(self) -> None:
        if self._last_txt and self._last_txt.exists():
            self._clipboard_set(self._last_txt.read_text(encoding="utf-8"))
            self._set_status("Текст скопирован в буфер")

    def _open_folder(self) -> None:
        self._open_path(Path(self.config.output_dir))

    @staticmethod
    def _open_path(path: Path) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception:
            webbrowser.open(path.as_uri())

    def _set_status(self, text: str) -> None:
        self.status_label.configure(text=text)

    def _on_close(self) -> None:
        try:
            if self.recorder.is_recording:
                wav = self.recorder.stop()
                delete_audio(wav)
        except Exception:
            pass
        self.hotkeys.stop()
        self.destroy()


def run() -> None:
    app = App()
    app.mainloop()
