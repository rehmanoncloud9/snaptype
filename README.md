# SnapType

Instant text expander for Windows. Type a short abbreviation, get the full phrase — everywhere on your system.

Fully local. No cloud, no account, no subscription.

---

## What it does

You type normally. SnapType watches in the background and expands short abbreviations into full phrases the instant you hit space, enter, or punctuation. Type `omw` and it becomes `on my way`. Type `ily` and it becomes `i love you`. Works in any app — Discord, WhatsApp, Notepad, your browser, anywhere you can type.

---

## Features

- **Real-time expansion** — fires the instant you finish typing a shortcut
- **20 curated built-in shortcuts** out of the box, tagged by category (`gm`, `brb`, `ty`, `omw`, `idk`, and more)
- **Fully customizable** — add, edit, or delete your own abbreviation → phrase pairs
- **Undo** — press Backspace right after an expansion to get your abbreviation back (or use the undo hotkey)
- **Stats** — your most-used shortcuts, a 14-day activity chart and an estimate of the typing time you've saved
- **Per-app rules** — expand only in chosen apps, or everywhere except chosen apps
- **Safe by default** — skips password, sign-in and verification-code windows and password managers
- **Variables** — `{{date}}`, `{{time}}`, `{{datetime}}`, `{{day}}`, `{{clipboard}}`
- **Snooze** — pause expansion for a set number of minutes, auto-resumes
- **Launch on startup** — starts hidden in the tray at login and is expanding straight away
- **Try it box** — test an expansion right on the Dashboard, no other app needed
- **Shortcut recorder** — set your hotkeys by pressing them
- **Dark, high-DPI interface** — the "Obsidian Cyber-Glass" design system (see [DESIGN.md](DESIGN.md)), crisp at 100–200% scaling
- **System tray** — lives in the tray, out of your way
- **Import/export** — back up or share your shortcut list as a CSV

---

## A note on window tracking

SnapType checks which application is currently focused so that App Rules can work. This check happens entirely on your device — nothing is logged externally, nothing is sent anywhere. A short walkthrough ending in this explanation is shown the first time you launch the app.

---

## Installation

**Easiest:** [download SnapType.exe](https://github.com/rehmanoncloud9/snaptype/releases/latest/download/SnapType.exe) and run it. See the [latest release](https://github.com/rehmanoncloud9/snaptype/releases/latest) for release notes and the SHA-256 checksum.

**From source** (Python 3.10+):

```bash
pip install -r requirements.txt
python snaptype.py
```

> **Windows note:** The `keyboard` library requires administrator privileges for global key hooks. Right-click and run as Administrator if expansions are not firing.

---

## Build a standalone .exe

No Python required on the target machine.

```bash
pip install -r requirements-dev.txt
python build.py --test
```

Output: `dist/SnapType.exe` and its `.sha256`. For an installer, compile
`installer/snaptype.iss` with Inno Setup.

---

## How to use

1. Launch the app and read the short welcome
2. Open **Snippets** and add your own abbreviation → phrase pairs, or use the built-in defaults
3. SnapType starts expanding immediately (switch this off in Settings if you prefer to press **Start** yourself)
4. Type anywhere. Not sure it works? Click the **Try it here** box on the Dashboard and type `omw` + space

### Hotkeys

| Action | Default |
|--------|---------|
| Toggle on/off | `Ctrl+Shift+S` (click **Change** in Settings and press a new combination) |
| Undo last expansion | `Backspace` right after it, or `Ctrl+Shift+U` (customizable) |
| Switch page | `Ctrl+1` … `Ctrl+6` |
| Search / new snippet | `Ctrl+F` / `Ctrl+N` |
| Save snippet from the text box | `Ctrl+Enter` |
| Quit | `Ctrl+Q`, or **Quit** in Settings, or the tray menu |

Shortcuts must include `Ctrl`, `Alt` or `Win` (function keys excepted) so they can never fire while you type normally.

---

## App Rules

Control which apps SnapType works in:

- **All apps** — active everywhere (default)
- **Only in these apps** — active only in the apps on your list
- **Everywhere except these** — active everywhere but the apps on your list

A rule is a piece of text matched against the window title (capitals ignored), so `Word` matches
"Report.docx - Word". Switch to your target app and come back: the **Add an app** panel shows the
last window you used with a suggested rule. Removing a rule offers **Undo**.
(In "Only in these apps" mode an empty list means SnapType still works everywhere, and the page says so.)

---

## Data and Privacy

Everything is stored locally in `%APPDATA%\SnapType` (older versions used `~/.snaptype`; it is migrated automatically). Saves are atomic and a `.bak` of the last good file is kept. No data leaves your machine. See [SECURITY.md](SECURITY.md).

---

## Project structure

```
snaptype.py       — entry point (DPI, single instance, error reporting)
snapui/           — the Tk interface: theme tokens, icons, widgets, dialogs, pages
snapcore/         — engine, storage, config, snippets, hotkeys, stats (GUI-free, tested)
tests/            — pytest suite (core logic runs anywhere; UI smoke tests need a display)
build.py          — PyInstaller build (icon, version info, SHA-256)
installer/        — Inno Setup script
.github/          — CI and release workflows
```

## Troubleshooting

- **Nothing expands:** use the **Try it here** box on the Dashboard first. If it works there but not in another app, that app is probably running as Administrator, so run SnapType as Administrator too. Check the tray icon and status pill say *Active*; check App Rules mode; check the window isn't a sign-in/password window (Settings → Expansion).
- **Logs:** `%APPDATA%\SnapType\snaptype.log`.
- **Antivirus warning:** keyboard-hooking apps are often flagged; verify the SHA-256 or build from source.

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

---

## Fonts (optional)

The design calls for **Inter** and **Geist Mono**. They aren't part of Windows, so SnapType falls back to
Segoe UI Variable and Cascadia Mono / Consolas. To get the exact look, drop the font files into
`snapui/assets/fonts/` (see the README there); `build.py` bundles them automatically.
