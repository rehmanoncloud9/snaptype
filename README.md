# SnapType

Instant text expander for Windows. Type a short abbreviation, get the full phrase — everywhere on your system.

Fully local. No cloud, no account, no subscription.

---

## What it does

You type normally. SnapType watches in the background and expands short abbreviations into full phrases the instant you hit space, enter, or punctuation. Type `omw` and it becomes `on my way`. Type `ily` and it becomes `i love you`. Works in any app — Discord, WhatsApp, Notepad, your browser, anywhere you can type.

---

## Features

- **Real-time expansion** — fires the instant you finish typing a shortcut
- **~40 built-in shortcuts** out of the box (`gm`, `brb`, `ty`, `omw`, `idk`, and more)
- **Fully customizable** — add, edit, or delete your own abbreviation → phrase pairs
- **Undo** — Ctrl+Z instantly reverses the last expansion
- **Stats** — see which shortcuts you use most
- **Per-app rules** — whitelist or blacklist specific apps (so it never fires in a password manager, for example)
- **Snooze** — pause expansion for a set number of minutes, auto-resumes
- **Launch on startup** — runs silently in the background on Windows boot
- **System tray** — lives in the tray, out of your way
- **Import/export** — back up or share your shortcut list as a CSV

---

## A note on window tracking

SnapType checks which application is currently focused so that App Rules (whitelist/blacklist) can work. This check happens entirely on your device — nothing is logged externally, nothing is sent anywhere. You'll see a short explanation of this the first time you launch the app.

---

## Installation

**Requirements:** Python 3.10+

```bash
pip install keyboard pystray Pillow
python snaptype.py
```

> **Windows note:** The `keyboard` library requires administrator privileges for global key hooks. Right-click and run as Administrator if expansions are not firing.

---

## Build a standalone .exe

No Python required on the target machine.

```bash
pip install pyinstaller
python build.py
```

Output: `dist/SnapType.exe`

---

## How to use

1. Launch the app
2. Go to **Snippets** → add your own abbreviation → phrase pairs, or use the built-in defaults
3. Toggle SnapType on from the tray or press your hotkey
4. Type anywhere — expansions happen automatically

### Hotkeys

| Action | Default |
|--------|---------|
| Toggle on/off | `Ctrl+Shift+S` (Customizable) |
| Undo last expansion | `Ctrl+Z` |

---

## App Rules

Control which apps SnapType works in:

- **All Apps** — active everywhere (default)
- **Whitelist** — only active in apps you list
- **Blacklist** — active everywhere except listed apps

Switch to your target app, come back to SnapType, click **Capture** — it auto-detects the window title.

---

## Data and Privacy

Everything is stored locally in `~/.snaptype/`. No data leaves your machine. No analytics. No cloud.

---

## Project structure

```
snaptype.py       — single-file application
requirements.txt  — pip dependencies
build.py          — PyInstaller build helper
README.md         — this file
```

---

## Why I built this

I wanted a faster way to type common phrases across every app I use, without paying for a subscription tool. SnapType is my own take on the text-expander category (in the spirit of tools like TextExpander, aText, or Espanso), built from scratch.

---

## Built by

**Abdul Rehman**

- LinkedIn: [linkedin.com/in/arehman-builds](https://www.linkedin.com/in/arehman-builds)
- Instagram: [@rehmanoncloud9](https://instagram.com/rehmanoncloud9)
- Email: relentlessrehman@gmail.com

---

## License

MIT — do whatever you want with it.
