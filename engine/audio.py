"""
engine/audio.py

Shared audio layer for every HandArcade game: sound effects AND
background music, with persisted volume/mute settings.

Usage:
    from engine.audio import init_audio, play_sound, play_music, stop_music

    init_audio()  # call once, e.g. at app startup in engine/menu.py
    play_music("assets/music/arcade_theme.mp3")
    play_sound("assets/sounds/slice.wav")

Settings (music volume, sfx volume, mute) are persisted to
engine/audio_settings.json so they survive between runs.

Safe to call even if no audio device is available (e.g. CI, some VMs):
failures are swallowed and the game keeps running silently.
"""

import json
import os

try:
    import pygame

    _PYGAME_AVAILABLE = True
except ImportError:
    _PYGAME_AVAILABLE = False

_initialized = False
_sound_cache = {}
_current_music = None

_SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "audio_settings.json")
_DEFAULT_SETTINGS = {"music_volume": 0.5, "sfx_volume": 0.8, "muted": False}
_settings = dict(_DEFAULT_SETTINGS)


def _load_settings():
    if not os.path.exists(_SETTINGS_PATH):
        return
    try:
        with open(_SETTINGS_PATH, "r") as f:
            loaded = json.load(f)
        for key in _DEFAULT_SETTINGS:
            if key in loaded:
                _settings[key] = loaded[key]
    except Exception as e:
        print(f"[audio] Could not load settings, using defaults: {e}")


def _save_settings():
    try:
        with open(_SETTINGS_PATH, "w") as f:
            json.dump(_settings, f)
    except Exception as e:
        print(f"[audio] Could not save settings: {e}")


def init_audio():
    """
    Set up the mixer and load persisted volume/mute settings.
    Call this once before any play_sound()/play_music() call.
    Safe to call multiple times (no-ops after the first successful init).
    """
    global _initialized

    _load_settings()

    if _initialized or not _PYGAME_AVAILABLE:
        return

    try:
        pygame.mixer.init()
        _initialized = True
        pygame.mixer.music.set_volume(_effective_music_volume())
    except Exception as e:
        print(f"[audio] Could not initialize mixer, continuing without sound: {e}")


def _load_sound(path):
    if path in _sound_cache:
        return _sound_cache[path]

    if not os.path.exists(path):
        print(f"[audio] Missing sound file: {path}")
        _sound_cache[path] = None
        return None

    try:
        sound = pygame.mixer.Sound(path)
    except Exception as e:
        print(f"[audio] Could not load {path}: {e}")
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

    final_volume = max(0.0, min(1.0, volume * _effective_sfx_volume()))
    sound.set_volume(final_volume)
    try:
        sound.play()
    except Exception as e:
        print(f"[audio] Could not play sound {path}: {e}")

def play_music(path, loop=True):
    """Start looping background music. Safe no-op if audio unavailable."""
    global _current_music

    if not _PYGAME_AVAILABLE or not _initialized:
        return

    if not os.path.exists(path):
        print(f"[audio] Missing music file: {path}")
        return

    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(_effective_music_volume())
        pygame.mixer.music.play(-1 if loop else 0)
        _current_music = path
    except Exception as e:
        print(f"[audio] Could not play music {path}: {e}")


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


def set_music_volume(volume):
    _settings["music_volume"] = max(0.0, min(1.0, volume))
    if _PYGAME_AVAILABLE and _initialized:
        try:
            pygame.mixer.music.set_volume(_effective_music_volume())
        except Exception as e:
            print(f"[audio] Could not set music volume: {e}")
    _save_settings()


def get_sfx_volume():
    return _settings["sfx_volume"]


def set_sfx_volume(volume):
    _settings["sfx_volume"] = max(0.0, min(1.0, volume))
    _save_settings()


def is_muted():
    return _settings["muted"]


def toggle_mute():
    _settings["muted"] = not _settings["muted"]
    if _PYGAME_AVAILABLE and _initialized:
        try:
            pygame.mixer.music.set_volume(_effective_music_volume())
        except Exception as e:
            print(f"[audio] Could not update volume after mute toggle: {e}")
    _save_settings()
    return _settings["muted"]