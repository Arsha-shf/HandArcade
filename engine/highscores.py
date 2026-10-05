"""
engine/highscores.py

Persistent best scores, one per key (e.g. "catch", "dodge_hard").
Stored in the per-user data folder, so they survive packaging.

    from engine import highscores
    best = highscores.get_best("catch")
    if highscores.submit("catch", score):   # True only for a new best
        ...
"""

import json
import os

from engine.paths import user_data_dir

_PATH = os.path.join(user_data_dir(), "highscores.json")
_scores = None


def _load():
    global _scores
    if _scores is not None:
        return _scores

    _scores = {}
    try:
        with open(_PATH, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, int) and not isinstance(value, bool):
                    _scores[str(key)] = value
    except (OSError, ValueError):
        pass
    return _scores


def _save():
    try:
        tmp = _PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(_scores, f)
        os.replace(tmp, _PATH)
    except OSError as e:
        print(f"[highscores] Could not save: {e}")


def get_best(key):
    return _load().get(key, 0)


def submit(key, score):
    """Record `score`. Returns True if it is a new best (and > 0)."""
    scores = _load()
    score = int(score)
    if score > 0 and score > scores.get(key, 0):
        scores[key] = score
        _save()
        return True
    return False