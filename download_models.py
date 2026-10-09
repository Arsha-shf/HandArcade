"""
download_models.py

Downloads the MediaPipe hand-tracking model into engine/models/ if it is
not already there. Run once after cloning:

    python download_models.py            # skip files that already exist
    python download_models.py --force    # re-download

Works on Windows, macOS and Linux (no wget/curl needed).
"""

import argparse
import sys
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent / "engine" / "models"

MODELS = {
    "hand_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
        "hand_landmarker/float16/1/hand_landmarker.task"
    ),
}


def download(name, url, force=False):
    """Returns True if the file is present afterwards."""
    dest = MODELS_DIR / name
    if dest.exists() and not force:
        print(f"Already have {dest}")
        return True

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"Downloading {name} ...")
    try:
        with urllib.request.urlopen(url, timeout=30) as response, open(tmp, "wb") as out:
            while chunk := response.read(1 << 16):
                out.write(chunk)
        tmp.replace(dest)   # only appears under its real name once complete
    except OSError as e:
        tmp.unlink(missing_ok=True)
        print(f"Failed to download {name}: {e}", file=sys.stderr)
        return False

    print(f"Saved {dest} ({dest.stat().st_size / 1e6:.1f} MB)")
    return True


def main():
    parser = argparse.ArgumentParser(description="Download MediaPipe model files.")
    parser.add_argument("--force", action="store_true", help="re-download existing files")
    args = parser.parse_args()

    ok = all([download(name, url, args.force) for name, url in MODELS.items()])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()