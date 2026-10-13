# Voice to Text

Records a conversation and saves the transcript as **TXT**. Audio is not kept.

## Run (Windows)

1. Install [Python 3.11+](https://www.python.org/downloads/) (check **Add to PATH**)  
   or in cmd: `winget install Python.Python.3.12`
2. Run `VoiceToText.exe`

Fallback: `scripts\run.bat`

## Usage

1. **Start recording** or press **Ctrl+Shift+R**
2. Do the same to stop
3. A TXT file appears in `Documents\Dialogs` (also copied to the clipboard)

## Layout

```
VoiceToText.exe
requirements.txt
app/          — app code
scripts/      — run.bat, build scripts
launcher/     — exe launcher source
```
