# handarcade.spec
#
# Build with:  pyinstaller handarcade.spec
# Output lands in dist/HandArcade/ (onedir build: more reliable than
# --onefile for mediapipe/opencv).
#
# Run it from the project root (paths below are relative to this file).

import os

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# MediaPipe ships its own package data; not picked up automatically.
mediapipe_datas = collect_data_files("mediapipe")


def _require(src, dest):
    """Must exist: fail the build with a clear message instead of shipping a
    broken app."""
    if not os.path.exists(src):
        raise SystemExit(f"[spec] Required path missing: {src}")
    return (src, dest)


def _optional(src, dest):
    """Include only if it exists (PyInstaller aborts on a missing source)."""
    if os.path.exists(src):
        return [(src, dest)]
    print(f"[spec] Skipping missing optional folder: {src}")
    return []


datas = mediapipe_datas + [
    # Destinations mirror the project layout, because engine/paths.py resolves
    # relative paths against the bundle root.
    _require("engine/models", "engine/models"),   # hand_landmarker.task, face_landmarker.task
    _require("assets", "assets"),                  # sprites, sounds, music
]

# Per-game asset folders, only if they exist.
for game in ("fruit_slice", "dodge", "catch", "pinch_pop"):
    datas += _optional(f"games/{game}/assets", f"games/{game}/assets")

hidden_imports = [
    "cv2",
    "mediapipe",
    "pygame",
    "numpy",
]

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HandArcade",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,        # UPX can corrupt opencv/mediapipe native libs
    console=True,     # keep True until the build works; then switch to False
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="HandArcade",
)
