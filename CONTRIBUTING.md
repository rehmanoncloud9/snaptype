# Contributing

```bash
pip install -r requirements-dev.txt
python -m pytest -q      # core tests run anywhere; UI smoke tests need a display
ruff check .
python snaptype.py       # run the app (Windows)
```

On Linux, run the UI smoke tests under a virtual display: `xvfb-run -a python -m pytest -q`.

## Where things go

- **Logic** belongs in `snapcore/` with a test. It must not import Tk.
- **Interface** belongs in `snapui/`. Colours, type and spacing come from `snapui/theme.py` and are
  never hard-coded in a page; pixel sizes go through `dp()` so the UI scales with display DPI.
- Reusable controls live in `snapui/widgets.py`; build pages from them rather than raw Tk widgets.

## Tk rules this codebase relies on

- **Threads:** Tk is single-threaded. Keyboard, tray and timer threads may only call
  `app._post(fn)`, never touch a widget.
- **Images:** Tk does not keep a Python reference to an image it displays. Store every `PhotoImage`
  on the widget (`widget.image = ph`) or it disappears.
- **Never** assign `self._w`, `self._name`, `self.master` or `self.children` on a widget subclass:
  tkinter owns them.
- Always bind with `add="+"`, otherwise you silently replace another handler.
- Colours must be plain `#rrggbb` (Tk has no `rgba()` or 8-digit hex); use `theme.blend()` for translucency.
- Don't mix `pack` and `grid` in one parent.

## Other

- Never log or persist typed text.
- Add a CHANGELOG entry for user-visible changes.
