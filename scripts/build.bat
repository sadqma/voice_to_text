@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo === Standalone сборка (PyInstaller) ===
echo.

python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Ошибка установки зависимостей.
  pause
  exit /b 1
)

python -m PyInstaller --noconfirm --clean ^
  --name "VoiceToText_Standalone" ^
  --windowed ^
  --onefile ^
  --paths "." ^
  --collect-all faster_whisper ^
  --collect-all customtkinter ^
  --hidden-import app.gui ^
  --hidden-import app.recorder ^
  --hidden-import app.transcriber ^
  --hidden-import app.config ^
  --hidden-import app.hotkeys ^
  scripts\pyinstaller_entry.py

if errorlevel 1 (
  echo Сборка не удалась.
  pause
  exit /b 1
)

echo Готово: dist\VoiceToText_Standalone.exe
pause
