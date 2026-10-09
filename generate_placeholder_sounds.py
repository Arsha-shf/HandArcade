"""
generate_placeholder_sounds.py

Generates short, valid .wav sound effects into assets/sounds/ so every game
has SOMETHING to play right away. Swap them for real sound effects whenever
you like: same filenames, same folder, nothing else needs to change.

    python generate_placeholder_sounds.py            # only creates missing files
    python generate_placeholder_sounds.py --force    # overwrite existing files

By default it never overwrites a file that already exists, so running it
again can't destroy sounds you replaced with real ones.

Files: pop.wav, slice.wav, hit.wav, shield.wav
"""

import argparse
import wave
from pathlib import Path

import numpy as np

OUT_DIR = Path(__file__).resolve().parent / "assets" / "sounds"
SAMPLE_RATE = 44100
ATTACK_S = 0.004   # tiny fade-in so playback doesn't start with a click


def _tone(segments, volume=0.5):
    """
    segments: list of (start_hz, end_hz, seconds). Each segment is a sine
    sweep from start_hz to end_hz; segments play back to back. A fade-in and
    fade-out are applied to the whole sound.
    """
    parts = []
    for f0, f1, seconds in segments:
        n = int(SAMPLE_RATE * seconds)
        freq = np.linspace(f0, f1, n)
        phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
        parts.append(np.sin(phase))
    wave_data = np.concatenate(parts)

    n = len(wave_data)
    envelope = np.linspace(1.0, 0.0, n)
    attack = max(1, int(SAMPLE_RATE * ATTACK_S))
    envelope[:attack] *= np.linspace(0.0, 1.0, attack)
    return volume * envelope * wave_data


def _write_wav(path, samples):
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)   # 16-bit
        f.setframerate(SAMPLE_RATE)
        f.writeframes(pcm.tobytes())


SOUNDS = {
    "pop.wav": [(600, 1100, 0.12)],                 # quick rising blip
    "slice.wav": [(1900, 900, 0.09)],               # fast falling swish
    "hit.wav": [(240, 110, 0.25)],                  # low thud
    "shield.wav": [(660, 660, 0.08), (990, 990, 0.12)],   # two-note chime
}


def main():
    parser = argparse.ArgumentParser(description="Generate placeholder sound effects.")
    parser.add_argument("--force", action="store_true", help="overwrite existing files")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, segments in SOUNDS.items():
        path = OUT_DIR / name
        if path.exists() and not args.force:
            print(f"Skipped {path} (already exists; use --force to overwrite)")
            continue
        _write_wav(path, _tone(segments))
        print(f"Wrote {path}")

    print("Done. These are placeholder beeps; replace them with real sound effects whenever you like.")


if __name__ == "__main__":
    main()