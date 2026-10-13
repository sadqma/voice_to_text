@echo off
chcp 65001 >nul
echo Пересборка VoiceToText.exe (нужен Go)
cd /d "%~dp0..\launcher"
set GOOS=windows
set GOARCH=amd64
set CGO_ENABLED=0
go build -ldflags="-H windowsgui -s -w" -o "..\VoiceToText.exe" .
if errorlevel 1 (
  echo Не удалось собрать. Установите Go: https://go.dev/dl/
  pause
  exit /b 1
)
echo Готово: ..\VoiceToText.exe
pause
