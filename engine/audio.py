"""
engine/audio.py

Tiny sound-effect player shared by every HandArcade game.

Uses pygame's mixer instead of cv2/winsound because it can play several
overlapping short sounds at once (e.g. two fruits sliced in the same
frame) without cutting each other off.

Usage:
    from engine.audio import init_audio, play_sound

    init_audio()  # call once, e.g. at app startup in engine/menu.py
    play_sound("assets/sounds/slice.wav")

Sounds are cached by path so repeated calls don't hit disk again.
Safe to call even if no audio device is available (e.g. CI, some VMs):
failures are swallowed and the game keeps running silently.
"""

import os

try:
    import pygame

    _PYGAME_AVAILABLE = True
except ImportError:
    _PYGAME_AVAILABLE = False

_initialized = False
_sound_cache = {}


def init_audio():
    """
    Set up the mixer. Call this once before any play_sound() call.
    Safe to call multiple times (no-ops after the first successful init).
    """
    global _initialized

    if _initialized or not _PYGAME_AVAILABLE:
        return

    try:
        pygame.mixer.init()
        _initialized = True
    except Exception as e:
        # No audio device, unsupported platform, etc. Games should still run.
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


def play_sound(path, volume=1.0):
    """
    Play a sound effect by file path. Fire-and-forget: doesn't block,
    doesn't return anything. No-op if audio isn't available/initialized
    or the file failed to load.
    """
    if not _PYGAME_AVAILABLE or not _initialized:
        return

    sound = _load_sound(path)
    if sound is None:
        return

    sound.set_volume(max(0.0, min(1.0, volume)))
    sound.play()


def stop_all_sounds():
    """Stop every currently-playing sound effect. Handy on game-over/menu transitions."""
    if _PYGAME_AVAILABLE and _initialized:
        pygame.mixer.stop()