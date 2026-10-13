# Voice to Text

Записывает разговор и сохраняет расшифровку в **TXT**. Аудио не хранится.

## Запуск (Windows)

1. Установите [Python 3.11+](https://www.python.org/downloads/) (галка **Add to PATH**)  
   или в cmd: `winget install Python.Python.3.12`
2. Запустите `VoiceToText.exe`

Запасной вариант: `scripts\run.bat`

## Использование

1. **Начать запись** или **Ctrl+Shift+R**
2. То же действие — остановить
3. TXT появится в `Документы\Dialogs` (и в буфере обмена)

## Структура

```
VoiceToText.exe
requirements.txt
app/          — код
scripts/      — run.bat, сборка
launcher/     — исходники exe
```
