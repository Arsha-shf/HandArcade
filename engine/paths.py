"""
engine/paths.py

One place that answers "where is this file?" so the game works the same
when run from source and when packaged with PyInstaller.

  - resolve("assets/sounds/hit.wav")  -> absolute path to a READ-ONLY
    bundled file (assets, models). Relative paths are resolved against the
    project root, NOT the current working directory, so it doesn't matter
    where you launch the app from.
  - user_data_dir()                   -> a WRITABLE per-user folder for
    settings. Under PyInstaller the bundle folder is a temp dir that is
    deleted on exit, so settings must never be written there.
"""

import contextlib
import os
import sys


def project_root():
    if getattr(sys, "frozen", False):
        # PyInstaller one-file: _MEIPASS. One-folder: next to the exe.
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(*parts):
    return os.path.join(project_root(), *parts)


def resolve(path):
    """Absolute paths pass through; relative ones are anchored to the project root."""
    if os.path.isabs(path):
        return path
    return os.path.join(project_root(), path)


def user_data_dir(app_name="HandArcade"):
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")

    folder = os.path.join(base, app_name)
    with contextlib.suppress(OSError):
        os.makedirs(folder, exist_ok=True)
    return folder