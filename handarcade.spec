# handarcade.spec
#
# Build with:  pyinstaller handarcade.spec
# Output lands in dist/HandArcade/ (onedir build -- MUCH more reliable than
# --onefile for apps using mediapipe/opencv, since those bundle native
# libs + data files that --onefile's runtime unpacking often trips over).
#
# NOTE: update the `datas` list below to match your actual asset folder
# names (sprite PNGs, sound .wav files, any per-game config/data files).
# Anything a game loads via a relative path (e.g. "assets/apple.png")
# needs an entry here, or it'll be missing in the packaged app.

import mediapipe
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# MediaPipe ships model files (.tflite etc.) as package data -- these are
# NOT picked up automatically and the app will crash on HandTracker init
# without them.
mediapipe_datas = collect_data_files("mediapipe")

datas = mediapipe_datas + [
    # (source, destination-folder-in-bundle)
    ("assets", "assets"),                      # top-level shared assets, if any
    ("games/fruit_slice/assets", "games/fruit_slice/assets"),
    ("games/dodge/assets", "games/dodge/assets"),
    ("games/catch/assets", "games/catch/assets"),
    ("games/pinch_pop/assets", "games/pinch_pop/assets"),
]

hidden_imports = [
    "cv2",
    "mediapipe",
    "pygame",
    "numpy",
]

a = Analysis(
    ["main.py"],
    pathex=[],
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
    upx=True,
    console=False,  # no terminal window; set True temporarily if you need
                     # to see print()/error output while debugging the build
    icon=None,       # e.g. "assets/icon.ico" if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="HandArcade",
)
