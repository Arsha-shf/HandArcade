"""
generate_placeholder_sounds.py

One-off script: generates 3 short, valid .wav beep files into
assets/sounds/ so you have SOMETHING real to test playback with right
now. Swap these for real recorded/downloaded sound effects later --
same filenames, same folder, nothing else needs to change.

Run once from the project root:
    python generate_placeholder_sounds.py
"""

import math
import os
import struct
import wave

OUT_DIR = os.path.join("assets", "sounds")
SAMPLE_RATE = 44100


def _write_beep(path, freq_hz, duration_s, volume=0.5):
    n_samples = int(SAMPLE_RATE * duration_s)
    with wave.open(path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)  # 16-bit
        f.setframerate(SAMPLE_RATE)
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            # simple fade-out envelope so it doesn't click at the end
            envelope = 1.0 - (i / n_samples)
            sample = volume * envelope * math.sin(2 * math.pi * freq_hz * t)
            f.writeframes(struct.pack("<h", int(sample * 32767)))
    print(f"Wrote {path}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    _write_beep(os.path.join(OUT_DIR, "pop.wav"), freq_hz=880, duration_s=0.12)
    _write_beep(os.path.join(OUT_DIR, "slice.wav"), freq_hz=1200, duration_s=0.08)
    _write_beep(os.path.join(OUT_DIR, "hit.wav"), freq_hz=220, duration_s=0.25)
    print("Done. These are placeholder beeps -- replace with real sound effects whenever you like.")


if __name__ == "__main__":
    main()