# Changelog

## v1.5.0 (visual redesign and UX hardening)

### Redesign
- New **Obsidian Cyber-Glass** interface implementing `DESIGN.md`: dark obsidian surfaces, glass
  panels, electric cyan and amethyst accents, sidebar with an active-indicator bar, status pill,
  keycap chips, toasts. Colours are pre-blended (Tk has no `rgba()`), and a unit test checks every text/background
  pair against WCAG AA contrast.
- One brand mark everywhere: the app icon, sidebar, About page and tray share a single bolt and tile; the tray
  icon is the logo recoloured by state (cyan active, amethyst snoozed, grey paused).
- Emoji icons replaced by a drawn icon set (consistent on every Windows build).
- **High-DPI:** every pixel size now scales with the display (previously only fonts did).
- Dark title bar on Windows 10/11 for the main window and dialogs.
- The 2,700-line `snaptype.py` is now a small entry point; the UI lives in the `snapui` package.

### New
- **Snippets** is a master-detail screen: list on the left, editor always visible on the right, with live
  validation, a character counter, one-click variable chips, a preview using real values, an "unsaved
  changes" guard, rename-in-place, and delete with **Undo**.
- **Try it here** box on the Dashboard to confirm expansion works without leaving the app.
- Stats: 14-day activity chart and an estimate of typing time saved.
- **Shortcut recorder** (press the keys instead of typing `ctrl+shift+s`); shortcuts that would fire while
  typing normally (`a`, `shift+a`) are rejected, in the UI and when loading an old config.
- App Rules in plain language, with a live "last active window" panel and a suggested rule; removals offer Undo.
- First-run welcome (one flow, replacing four message boxes) ending in the privacy acknowledgement; explicit Quit.
- **Quit SnapType** in Settings, `Ctrl+Q`, and a first-close choice (keep in tray or quit).
- Tray menu reflects state (Pause / Resume / Start) and offers Snooze; the snooze countdown shows in the status pill.
- Keyboard shortcuts: `Ctrl+1`-`6` pages, `Ctrl+F`, `Ctrl+N`, `Ctrl+Enter`.
- Settings: "Start expanding when SnapType opens" (on by default).

### Fixed
- Windows CSV imports normalize multiline snippets to consistent line endings.
- Dialogs handle being closed during display setup, and onboarding cannot open twice.
- **The toggle hotkey changed the UI from the keyboard thread** (could hang or crash Tk). It now goes through the UI queue.
- **Snooze while stopped** would switch expansion *on* when the timer ended. Snooze is only available while active.
- **Resuming during a snooze** left the old timer armed, which later fired a spurious "Snooze ended".
- **Tooltips replaced hover handlers** on Start/Stop/Snooze (missing `add="+"`).
- **Placeholder text swallowed clicks**, so clicking the greyed text didn't focus the field.
- **Double-clicking an app rule deleted it** before the edit was confirmed.
- **Launch at login opened the window and left expansion off.** It now starts hidden in the tray and expanding;
  existing startup entries are upgraded automatically.
- Emoji titles were mangled by `title[0]` slicing for multi-code-point emoji.
- Hovering a list stole keyboard focus (the old scroll workaround); one pointer-based wheel handler replaces it.
- Stacked `after()` timers cleared newer status messages early; messages are now toasts with one timer.
- Quick-add chips saved placeholder data (`you@example.com`); they now prefill the editor instead.
- Errors inside Tk callbacks were invisible in the windowed .exe; they are now logged and surfaced.
- Closing the window with no tray available hid the app with no way back; it now quits.
- Snippet "enable" switch that silently reset on every launch was removed (Start/Stop covers it).
- `ruff check` would have failed CI on bare `except:`; the new code is clean.

### Engine and core
- Starting manually cancels a pending snooze timer; the snooze timer is cleared once fired.
- `Stats` keeps a per-day history (format v2, legacy files load unchanged).
- New `snapcore.hotkeys` module (normalise / validate / capture), 60 new tests (107 in total) plus 21 UI smoke tests that build the real window and drive every page.

## v1.4.0 (production-readiness release)

### Fixed
- **Snippets could be wiped by a corrupt file.** A bad `snippets.json` used to
  be silently replaced with the defaults. Saves are now atomic (temp file +
  fsync + replace), the last good copy is kept as `.bak`, and an unreadable
  file is moved aside as `*.corrupt-<time>` and recovered from the backup.
- **Expansions could re-trigger themselves.** SnapType's own injected
  keystrokes were fed back into its buffer, so a snippet whose text contained
  its own abbreviation could loop. Injected input is now ignored.
- **Wrong text could be deleted.** If you kept typing between the trigger key
  and the replacement, the backspaces removed the wrong characters. The
  expansion is now aborted instead.
- **Undo double-fired.** `Ctrl+Z` also reached the app and undid your own
  text. Undo is now **Backspace right after an expansion** (restores the
  abbreviation and won't re-expand it); the hotkey default is `Ctrl+Shift+U`
  (old `Ctrl+Z` configs are migrated automatically).
- **Launch-at-startup was broken in the .exe** (it appended a script path that
  does not exist) and opened a console window from source. Fixed.
- **Stale half-typed words** combined with later text (type `o`, click
  elsewhere, type `mw `). The buffer now resets after 4 s idle.
- **Typing inside SnapType's own fields** could trigger expansions. Blocked.
- **`{{clipboard}}`** used default ctypes signatures that truncate 64-bit
  handles. Rewritten with explicit signatures and retry.
- Abbreviations that can never fire (spaces/symbols) or that are ordinary
  words (`the`, `and`) are now rejected with an explanation.
- Snooze spinbox ignored typed values and could raise on partial input.
- Several bare `except:` blocks hid real errors; failures are now logged.

### Added
- **Safety:** skips windows whose title mentions password / sign-in /
  verification code or a password manager (toggle in Settings).
- **Single-instance guard** (two copies would double every expansion).
- **Rotating log** at `%APPDATA%\SnapType\snaptype.log` (events and errors
  only, never typed text) and a friendly crash dialog.
- New variables: `{{datetime}}`, `{{day}}`.
- Data now lives in `%APPDATA%\SnapType` (v1.2 data is migrated once).
- CSV import skips invalid rows and tells you how many; handles Excel BOM.
- Tray hint the first time the window is closed.
- Tests (pytest, 47 cases), ruff config, GitHub Actions CI + release
  workflow, PyInstaller build with icon + version info + SHA-256, Inno Setup
  installer script.

### Changed
- Core logic moved out of the 3,000-line UI file into the `snapcore/`
  package (no GUI dependencies, fully unit-tested via a fake keyboard).
- Thread-safe UI updates (keyboard/tray/timer threads queue work for Tk).

## v1.3.0 (UI/UX polish + performance pass)

### Fixed
- **Live Activity feed was showing expansions oldest-first.** The refresh
  logic looped newest→oldest while repeatedly inserting each one at
  position 0, which reversed the list — the newest expansion ended up at
  the *bottom* of a feed that's supposed to read top-down like a log.

### Added
- **Live preview in the snippet form.** As you type an abbreviation and
  expansion, a line beneath the form shows exactly what will happen —
  `Preview: type "omw" + space → "on my way"` — so mistakes are visible
  before you save, not after.
- **Clear "Adding" vs "Editing" mode indicator** above the snippet form,
  with the action button itself relabeling to Add/Update to match.
- **Overwrite confirmation** when saving a new abbreviation that collides
  with a different, already-saved snippet — shows old vs. new expansion
  side by side before it replaces anything.
- **Full keyboard accessibility for every button in the app.** The custom
  pill-style buttons (Start/Stop, Delete, Import, Save, etc.) are all built
  from one shared function; they're now Tab-focusable with a visible focus
  ring and activate on Enter/Space, not mouse-only.
- **Escape clears the snippet form** from any of its fields, or the list.
- **Zebra-striped rows** in the Snippets table for easier scanning of long
  lists.
- **Delete key removes the selected App Rule** (parity with the Snippets
  table), and double-clicking one loads it back into the text field for
  editing instead of just sitting there.
- Snippets search box auto-focuses when you navigate to the page.
- Hover tooltips on Start/Stop and Snooze showing the actual configured
  hotkey/duration, computed live so they can't go stale after a Settings
  change.

### Performance
- **Config writes are now debounced.** Dragging the typing-speed slider
  used to write the entire config file to disk on every intermediate
  value; rapid-fire `set()` calls now coalesce into one write shortly
  after things settle (same pattern already used for Stats).
- **Background window-title polling now pauses while App Rules is in its
  default "All Apps" mode**, instead of polling the OS every 0.6s forever
  regardless of whether the feature is in use.
- **CSV import writes `snippets.json` once**, at the end, instead of once
  per imported row.
- **Snippet search is debounced** (120ms) instead of fully clearing and
  re-sorting the Treeview on every keystroke.
- **Live Activity feed updates incrementally** (insert newest + trim
  oldest) instead of clearing and re-rendering the whole list on every
  single expansion.

## v1.2.0 (default snippets + discoverability)

### Changed
- **Default snippet library cut from 64 down to 20**, each tagged with a
  category (Greetings, Affection, Gratitude, Status, Opinion, Info) that now
  shows in the Tags column. Removed:
  - The whole "casual word → formal word" set (`gonna`→"going to",
    `lol`→"laughing out loud", `omg`→"oh my god", `bc`→"because", etc.) —
    these silently rewrote words people are very often typing on purpose in
    casual chat, which is the single most common complaint against text
    expanders.
  - Near-duplicates that added nothing on top of a shorter, more common
    equivalent already in the set (`otw` next to `omw`, `bbl`/`bbs` next to
    `brb`, `ttys` next to `ttyl`, `thx`/`nw` next to `ty`/`np`).
  - A couple of collision-prone entries: `def` (definitely) is a keyword in
    several programming languages, `bc` (because) is a common abbreviation
    for "before Christ".
  - README and the PRD both still said "~40 built-in shortcuts" even though
    the actual list had grown to 64 — now both correctly say 20.
- **Snippets tree shows the whole list at once.** Height bumped from 12 to
  20 rows, so the full default set (and most personal lists) needs no
  internal scrolling to see everything — you'll still scroll the page to
  reach the edit form below, but the list itself is fully visible.
- **Column headers are now clickable to sort** — Abbreviation, Expands to,
  or Tags (click Tags to group the whole list by category), with a ▲/▼
  indicator showing the active sort and direction. Click a header again to
  reverse it.
- **Quick Add Examples chips replaced.** All five previous examples (`ily`,
  `omw`, `hru`, `asap`, `lmk`) are now already in the default set, so
  clicking them was a confusing no-op. New chips show things that aren't
  pre-loaded — an address/signature/email placeholder and one demonstrating
  the `{{date}}` dynamic variable, which most users won't otherwise discover.

## v1.2.0 (UX follow-up)

### Added
- **Notifications are now real.** `notify_enabled` existed in `Config`'s
  defaults but was never read anywhere and had no UI control — a dead
  setting. It now has a toggle on the Settings page and drives actual tray
  notifications for the events with the least other feedback: toggling
  active/inactive (often done via the global hotkey while the window is
  hidden in the tray) and a snooze auto-resuming (previously silent).
- **Empty states.** The Live Activity feed, App Rules list, Stats table, and
  a Snippets search with no matches now show a short explanatory line
  instead of an unexplained blank box — including a heads-up that an empty
  whitelist/blacklist has no effect yet.
- **Enter submits the snippet form** from the Abbreviation and Tags fields
  (not the Expansion textarea, where Enter correctly still means "new
  line"), instead of requiring a click on "Add / Update" every time.
- **Onboarding tour has a real skip.** The welcome step is now a Yes/No
  opt-in instead of a plain OK dialog, so a new user can decline the tour
  immediately instead of being forced through all four popups with no way
  out.

### Fixed
- **Invalid hotkeys failed silently.** A malformed or duplicate Toggle/Undo
  hotkey used to fail deep inside `Engine` (`add_hotkey()` wrapped in a bare
  `try/except: pass`), while the Settings page still showed a green
  "Hotkeys saved!" message — leaving a hotkey that quietly did nothing and
  no clue why. Both hotkeys are now validated with `keyboard.parse_hotkey`
  (the same parser the engine itself uses) before anything is saved, and a
  duplicate Toggle/Undo combo is rejected with a clear message.
- **Snippet count while searching was misleading.** The Snippets page always
  showed the total snippet count even while a search had filtered the tree
  down to a handful of rows (e.g. "91 snippets" above a tree showing 2). It
  now shows "N of 91 snippets" while a search is active.
- **Dead tour-copy variable.** The onboarding tour computed a `btn_text` of
  "Next"/"Finish" every step but never displayed it anywhere — the dialogs
  only ever have a single OK button. Copy now honestly says "Click OK to
  continue/finish".

## v1.2.0 (audit follow-up)

### Fixed
- **Version string mismatch.** The `VERSION` constant (shown in the title bar
  and About page) still read `1.1.0` while the docstring, in-code comments,
  and this changelog all describe the running build as `1.2.0`.

### Performance
- **Keyboard-hook thread was doing real work.** `_blocked()` (the App Rules
  check) and `_process_expansion()` (`{{date}}`/`{{time}}`/`{{clipboard}}`
  substitution) used to run synchronously inside `_on_key`, which is called
  directly on the `keyboard` library's low-level hook thread. A slow window
  poll or a clipboard held by another app there could stall every keystroke
  system-wide. Both now run inside the same background timer that already
  handles the delayed replace, so the hook callback itself is back to a
  cheap dict lookup.
- **App Rules re-polled the active window from scratch on every matching
  keystroke** via `_poll_window()`, instead of using the value the
  background `_window_tracker` thread already maintains. On macOS/Linux this
  meant spawning a subprocess (`osascript`/`xdotool`, up to a 0.3s timeout)
  per expansion whenever a whitelist/blacklist was active. `_blocked()` now
  reads the cached `_active_window()` value.
- **Stats wrote the entire file to disk, on a brand-new thread, on every
  single expansion.** Typing several shortcuts in quick succession fired
  several overlapping full-file writes. Saves are now debounced (coalesced
  into one write ~400ms after the last expansion), with an explicit
  `Stats.flush()` called on quit so nothing pending is lost on exit.
- **Mouse-wheel handlers leaked and stacked.** `_scrolled()`'s child-binder
  walked the *entire* widget tree and re-bound `<MouseWheel>` with `add="+"`
  on every `<Configure>` event — which fires repeatedly while a page's
  layout is settling and on every window resize. Because `add="+"` stacks
  handlers instead of replacing them, every widget accumulated a new
  duplicate scroll handler each time, so scrolling got faster and janker
  the longer the app/window had been open, with unbounded memory growth
  from the piled-up closures. Each widget is now bound exactly once
  (tracked via a marker attribute), and the tree-walk itself is debounced
  the same way the glass-surface redraw already is.

### Fixed
- **Washed-out / near-invisible UI.** The app called an undocumented Windows
  DWM API (`SetWindowCompositionAttribute` / `ACCENT_ENABLE_ACRYLICBLURBEHIND`)
  to fake a frosted window backdrop. On current Windows builds that private
  API is unreliable and frequently blends the window's *own content* toward
  transparency instead of just the backdrop behind it — producing an
  all-white, barely-legible UI. Removed entirely; the app's existing
  PIL-rendered "liquid glass" cards/buttons already give the frosted look
  reliably with zero native-API risk.
- **Crash on quit.** Closing the app from the tray menu (or normal window
  close) triggered a `RecursionError` and crashed. A helper aliased
  `inner.destroy = outer.destroy` on every glass card, which made Tkinter's
  own widget-teardown cascade recurse infinitely the moment any window
  containing a card was destroyed. Removed the alias — nothing in the
  codebase depended on it, and Tkinter's normal parent→child destroy
  cascade already handles it correctly.

### Changed
- **Logo redesign.** Replaced the old "S/T" monogram (built from thick
  straight-line strokes, which read as a jagged zigzag rather than real
  letterforms — especially once downsampled to a 16–32px tray icon) with a
  single bolt glyph. It's now generated by one shared function used
  everywhere the brand mark appears (app icon, sidebar, About page, tray
  icon) instead of two separate hand-drawn implementations.
- **Sidebar nav hover** now highlights the whole pill (background + text)
  together instead of just the button text, for a more seamless hover state.

### Performance
- The glass-card renderer (`_glass_surface`) re-rasterized a Gaussian-blurred
  PIL image on *every* `<Configure>` event, including the storm of events
  fired while a window edge is being dragged. Redraws are now debounced
  (coalesced into a single repaint ~30ms after the last resize event).
- The glass-image cache (`_GLASS_CACHE`) had no eviction, so a long session
  of window resizing (a new width/height on nearly every pixel) grew it
  without bound. It's now a capped LRU (400 entries).
- `_refresh_status()` destroyed and rebuilt the Start/Stop/Snooze button
  widgets from scratch on almost every user action (including after every
  `_flash()` toast message). `_modern_button` now exposes `.restyle()` so
  these buttons update their label/color in place instead.

No functional/behavioral changes to snippet expansion, stats, app rules, or
hotkeys — this release is UI rendering, stability, and performance only.
