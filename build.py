"""SnapType build script: packages the app into dist/SnapType.exe.

    pip install -r requirements-dev.txt
    python build.py            # build
    python build.py --test     # run the test-suite first

Produces dist/SnapType.exe plus dist/SnapType.exe.sha256.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIST, BUILD, ASSETS = HERE / "dist", HERE / "build", HERE / "build_assets"


def run(cmd: list[str]) -> None:
    print("\n>", " ".join(cmd))
    result = subprocess.run(cmd, cwd=HERE)
    if result.returncode:
        sys.exit(f"Command failed with exit code {result.returncode}")


def make_assets(version: str) -> tuple[Path, Path]:
    """Generate the .ico (from the app's own logo) and the Windows version resource."""
    ASSETS.mkdir(exist_ok=True)
    sys.path.insert(0, str(HERE))
    from snapui import icons  # noqa: E402

    ico = ASSETS / "snaptype.ico"
    icons.make_logo(256).save(ico, sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])

    nums = (version.split(".") + ["0", "0", "0"])[:4]
    tup = ", ".join(nums)
    info = ASSETS / "version_info.txt"
    info.write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({tup}), prodvers=({tup}), mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Abdul Rehman'),
      StringStruct('FileDescription', 'SnapType text expander'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', 'SnapType'),
      StringStruct('LegalCopyright', 'MIT License'),
      StringStruct('OriginalFilename', 'SnapType.exe'),
      StringStruct('ProductName', 'SnapType'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ])
""", encoding="utf-8")
    return ico, info


def main() -> None:
    if "--test" in sys.argv:
        run([sys.executable, "-m", "pytest", "-q"])

    from snapcore import VERSION
    print(f"Building SnapType {VERSION}")

    if sys.platform == "win32":      # release the file lock if a copy is running
        subprocess.run(["taskkill", "/f", "/im", "SnapType.exe"], capture_output=True)
    for d in (DIST, BUILD, ASSETS):
        shutil.rmtree(d, ignore_errors=True)

    ico, info = make_assets(VERSION)
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
           "--windowed", "--name", "SnapType", "--icon", str(ico),
           "--version-file", str(info),
           "--hidden-import", "pystray._win32", "--hidden-import", "PIL._tkinter_finder",
           "--collect-submodules", "snapui"]             # pages are imported lazily
    fonts = HERE / "snapui" / "assets" / "fonts"
    if any(fonts.glob("*.[to]tf")):                      # Inter / Geist Mono, if you've added them
        cmd += ["--add-data", f"{fonts}{os.pathsep}snapui/assets/fonts"]
        print("Bundling fonts from", fonts)
    run(cmd + ["snaptype.py"])

    exe = DIST / "SnapType.exe"
    if not exe.exists():
        sys.exit("Build failed: dist/SnapType.exe not found")
    digest = hashlib.sha256(exe.read_bytes()).hexdigest()
    (DIST / "SnapType.exe.sha256").write_text(f"{digest}  SnapType.exe\n")
    print(f"\nBuilt {exe}  ({exe.stat().st_size / 1_048_576:.1f} MB)\nSHA-256 {digest}")


if __name__ == "__main__":
    main()
