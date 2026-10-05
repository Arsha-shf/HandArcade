"""
engine/audio.py

Shared audio layer for every HandArcade game: sound effects AND
background music, with persisted volume/mute settings.

Usage:
    from engine.audio import init_audio, play_sound, play_music, stop_music

    init_audio()  # call once, e.g. at app startup in engine/menu.py
    play_music("assets/music/arcade_theme.mp3")
    play_sound("assets/sounds/slice.wav")

Relative paths are resolved against the project root (see engine/paths.py),
so they work from any working directory and inside a PyInstaller build.

Settings (music volume, sfx volume, mute) are saved to the per-user data
folder, so they survive between runs even when the app is packaged.

Safe to call even if no audio device is available: failures are swallowed
and the game keeps running silently.
"""

import json
import os

from engine.paths import resolve, user_data_dir

try:
    import pygame

    _PYGAME_AVAILABLE = True
except ImportError:
    _PYGAME_AVAILABLE = False

_initialized = False
_settings_loaded = False
_sound_cache = {}
_current_music = None

_SETTINGS_PATH = os.path.join(user_data_dir(), "audio_settings.json")
_DEFAULT_SETTINGS = {"music_volume": 0.5, "sfx_volume": 0.8, "muted": False}
_settings = dict(_DEFAULT_SETTINGS)


def _clamp01(value):
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return None


def _load_settings():
    """Load once per run. Re-loading on every init_audio() call would
    overwrite in-memory changes with whatever is on disk."""
    global _settings_loaded
    if _settings_loaded:
        return
    _settings_loaded = True

    if not os.path.exists(_SETTINGS_PATH):
        return
    try:
        with open(_SETTINGS_PATH, "r") as f:
            loaded = json.load(f)
        for key in ("music_volume", "sfx_volume"):
            value = _clamp01(loaded.get(key))
            if value is not None:
                _settings[key] = value
        if isinstance(loaded.get("muted"), bool):
            _settings["muted"] = loaded["muted"]
    except Exception as e:
        print(f"[audio] Could not load settings, using defaults: {e}")


def save_settings():
    """Write settings to disk. Setters call this by default; the menu's
    slider drag passes save=False while dragging and calls this once on
    mouse release, so there is no disk I/O inside the render loop."""
    try:
        tmp = _SETTINGS_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(_settings, f)
        os.replace(tmp, _SETTINGS_PATH)  # atomic: no half-written file on crash
    except Exception as e:
        print(f"[audio] Could not save settings: {e}")


def init_audio():
    """
    Set up the mixer and load persisted volume/mute settings.
    Call this once before any play_sound()/play_music() call.
    Safe to call multiple times.
    """
    global _initialized

    _load_settings()

    if _initialized or not _PYGAME_AVAILABLE:
        return

    try:
        # Small buffer = lower sound-effect latency (default is 4096 samples).
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
        _initialized = True
        pygame.mixer.music.set_volume(_effective_music_volume())
    except Exception as e:
        print(f"[audio] Could not initialize mixer, continuing without sound: {e}")


def _load_sound(path):
    if path in _sound_cache:
        return _sound_cache[path]

    full_path = resolve(path)
    if not os.path.exists(full_path):
        print(f"[audio] Missing sound file: {full_path}")
        _sound_cache[path] = None
        return None

    try:
        sound = pygame.mixer.Sound(full_path)
    except Exception as e:
        print(f"[audio] Could not load {full_path}: {e}")
        sound = None

    _sound_cache[path] = sound
    return sound


def _effective_sfx_volume():
    return 0.0 if _settings["muted"] else _settings["sfx_volume"]


def _effective_music_volume():
    return 0.0 if _settings["muted"] else _settings["music_volume"]


def play_sound(path, volume=1.0):
    """
    Play a sound effect by file path. Fire-and-forget: doesn't block,
    doesn't return anything. No-op if audio isn't available/initialized,
    the file failed to load, or the user is muted.
    """
    if not _PYGAME_AVAILABLE or not _initialized:
        return

    sound = _load_sound(path)
    if sound is None:
        return

    sound.set_volume(max(0.0, min(1.0, volume * _effective_sfx_volume())))
    try:
        sound.play()
    except Exception as e:
        print(f"[audio] Could not play sound {path}: {e}")


def play_music(path, loop=True):
    """Start looping background music. If this track is already playing,
    does nothing (so calling it again after a game returns is harmless)."""
    global _current_music

    if not _PYGAME_AVAILABLE or not _initialized:
        return

    full_path = resolve(path)

    try:
        if _current_music == full_path and pygame.mixer.music.get_busy():
            return
    except Exception:
        pass

    if not os.path.exists(full_path):
        print(f"[audio] Missing music file: {full_path}")
        return

    try:
        pygame.mixer.music.load(full_path)
        pygame.mixer.music.set_volume(_effective_music_volume())
        pygame.mixer.music.play(-1 if loop else 0)
        _current_music = full_path
    except Exception as e:
        print(f"[audio] Could not play music {full_path}: {e}")


def stop_music():
    global _current_music
    if not _PYGAME_AVAILABLE or not _initialized:
        return
    try:
        pygame.mixer.music.stop()
        _current_music = None
    except Exception as e:
        print(f"[audio] Could not stop music: {e}")


def get_music_volume():
    return _settings["music_volume"]


def set_music_volume(volume, save=True):
    _settings["music_volume"] = max(0.0, min(1.0, volume))
    if _PYGAME_AVAILABLE and _initialized:
        try:
            pygame.mixer.music.set_volume(_effective_music_volume())
        except Exception as e:
            print(f"[audio] Could not set music volume: {e}")
    if save:
        save_settings()


def get_sfx_volume():
    return _settings["sfx_volume"]


def set_sfx_volume(volume, save=True):
    _settings["sfx_volume"] = max(0.0, min(1.0, volume))
    if save:
        save_settings()


def is_muted():
    return _settings["muted"]


def toggle_mute():
    _settings["muted"] = not _settings["muted"]
    if _PYGAME_AVAILABLE and _initialized:
        try:
            pygame.mixer.music.set_volume(_effective_music_volume())
        except Exception as e:
            print(f"[audio] Could not update volume after mute toggle: {e}")
    save_settings()
    return _settings["muted"]