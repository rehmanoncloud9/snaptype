# Optional fonts

The design specifies **Inter** (interface) and **Geist Mono** (shortcuts, abbreviations, labels).
Neither ships with Windows, so SnapType falls back to *Segoe UI Variable / Segoe UI* and
*Cascadia Mono / Consolas*, which look good but are not pixel-identical to the spec.

To get the exact look, drop the static `.ttf` or `.otf` files here, for example:

    Inter-Regular.ttf   Inter-SemiBold.ttf   GeistMono-Regular.ttf   GeistMono-Bold.ttf

They are registered for SnapType's own process only (nothing is installed system-wide) and
`python build.py` bundles them into the .exe automatically. Both families are licensed under
the SIL Open Font License, so redistribution is permitted; keep their licence files alongside.
