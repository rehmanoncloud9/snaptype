"""
SnapType — Build Script
========================
Packages snaptype.py into a standalone Windows .exe using PyInstaller.

Usage:
    pip install pyinstaller
    python build.py

Output: dist/SnapType.exe  (~15-25 MB, no Python install required)
"""

import os, sys, subprocess, shutil
from pathlib import Path

HERE = Path(__file__).parent
DIST = HERE / "dist"
BUILD = HERE / "build"

def run(cmd):
    print(f"\n▶  {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"\n❌  Command failed with code {result.returncode}")
        sys.exit(result.returncode)

def main():
    print("=" * 54)
    print("  SnapType Build Script")
    print("=" * 54)

    # Check PyInstaller
    try:
        import PyInstaller
        print(f"✅  PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("Installing PyInstaller...")
        run("pip install pyinstaller")

    # Clean previous build
    for d in [DIST, BUILD]:
        if d.exists():
            shutil.rmtree(d)
            print(f"🗑  Cleaned: {d}")

    # Build command
    cmd = (
        "pyinstaller "
        "--onefile "                           # single .exe
        "--windowed "                          # no console window
        "--name SnapType "
        "--clean "
        "--hidden-import pystray._win32 "      # pystray backend
        "--hidden-import PIL._tkinter_finder " # Pillow + Tk
        "snaptype.py"
    )

    run(cmd)

    exe = DIST / "SnapType.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / 1_048_576
        print(f"\n{'='*54}")
        print(f"  ✅  Build successful!")
        print(f"  📦  {exe}")
        print(f"  📏  {size_mb:.1f} MB")
        print(f"{'='*54}")
        print("\nTo distribute: share just SnapType.exe")
        print("Users need no Python, pip, or dependencies.")
    else:
        print("❌  Build failed — exe not found")
        sys.exit(1)

if __name__ == "__main__":
    main()
