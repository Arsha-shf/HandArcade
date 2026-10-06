"""
engine/sprites.py

PNG overlay system shared by every HandArcade game.

Loads transparent PNGs and draws them onto a live BGR camera frame with
proper alpha blending.

Usage:
    from engine.sprites import draw_sprite

    draw_sprite(frame, "assets/apple.png", x=300, y=150, scale=1.0)
    draw_sprite(frame, "assets/apple.png", x=300, y=150, scale=1.5, angle=30)

Implementation notes
--------------------
* Two caches. `_base_cache` holds each PNG once (decoded from disk once,
  ever). `_sprite_cache` holds resized+rotated variants and is an LRU.
  Before, every new (scale, angle) variant re-read the PNG from disk.
* Sprites are stored PREMULTIPLIED (color already multiplied by alpha).
  Resizing/rotating premultiplied pixels is the mathematically correct way
  to filter transparent images; it removes the dark halo that appears on
  rotated edges. Blending then needs one multiply instead of two.
* Blend runs in float32 (not float64): half the memory traffic.
* angle is CLOCKWISE degrees, as documented.
"""

from collections import OrderedDict

import cv2
import numpy as np

from engine.paths import resolve

# Rotation is snapped to this many degrees so a continuously spinning sprite
# reuses cached rotations. 5 deg -> 72 variants per (sprite, scale): looks
# continuous, and 72 x 3 sprites x a few scales stays well under the cap.
ANGLE_BUCKET_DEG = 5
_MAX_CACHE_ENTRIES = 800

_base_cache = {}                 # path -> premultiplied BGRA uint8
_sprite_cache = OrderedDict()    # (path, scale, angle) -> premultiplied BGRA uint8


def _load_sprite(path):
    """
    Load a PNG once and return it as premultiplied BGRA uint8.
    Raises FileNotFoundError if the path is bad: a silently-missing sprite is
    worse than a loud crash while developing.
    """
    cached = _base_cache.get(path)
    if cached is not None:
        return cached

    image = cv2.imread(resolve(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise FileNotFoundError(f"Could not load sprite: {path}")

    if image.dtype != np.uint8:  # e.g. 16-bit PNG
        image = cv2.convertScaleAbs(image, alpha=255.0 / np.iinfo(image.dtype).max)

    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGRA)
    elif image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)  # adds opaque alpha

    alpha = image[:, :, 3:4].astype(np.float32) * (1.0 / 255.0)
    premult = image.copy()
    premult[:, :, :3] = (image[:, :, :3].astype(np.float32) * alpha + 0.5).astype(np.uint8)

    _base_cache[path] = premult
    return premult


def _quantize_angle(angle):
    return (round(angle / ANGLE_BUCKET_DEG) * ANGLE_BUCKET_DEG) % 360


def _rotate_sprite(sprite, angle_cw):
    """Rotate a BGRA sprite clockwise around its center, expanding the canvas
    so nothing gets cropped. (cv2's positive angle is counter-clockwise, hence
    the minus.)"""
    h, w = sprite.shape[:2]
    center = (w / 2, h / 2)

    matrix = cv2.getRotationMatrix2D(center, -angle_cw, 1.0)

    cos = abs(matrix[0, 0])
    sin = abs(matrix[0, 1])
    new_w = int(h * sin + w * cos)
    new_h = int(h * cos + w * sin)

    matrix[0, 2] += (new_w / 2) - center[0]
    matrix[1, 2] += (new_h / 2) - center[1]

    return cv2.warpAffine(
        sprite,
        matrix,
        (new_w, new_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )


def _get_cached_sprite(path, scale, angle):
    """Return a (possibly cached) resized + rotated premultiplied BGRA sprite."""
    angle_q = _quantize_angle(angle)
    key = (path, round(scale, 3), angle_q)

    sprite = _sprite_cache.get(key)
    if sprite is not None:
        _sprite_cache.move_to_end(key)
        return sprite

    sprite = _load_sprite(path)

    if scale != 1.0:
        new_w = max(1, int(sprite.shape[1] * scale))
        new_h = max(1, int(sprite.shape[0] * scale))
        interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
        sprite = cv2.resize(sprite, (new_w, new_h), interpolation=interp)

    if angle_q != 0:
        sprite = _rotate_sprite(sprite, angle_q)

    _sprite_cache[key] = sprite
    if len(_sprite_cache) > _MAX_CACHE_ENTRIES:
        _sprite_cache.popitem(last=False)

    return sprite


def draw_sprite(frame, png_path, x, y, scale=1.0, angle=0.0, anchor="center"):
    """
    Draw a transparent PNG onto a BGR frame at (x, y) with alpha blending.

    Args:
        frame: BGR uint8 camera frame, modified in place.
        png_path: path to a transparent PNG (relative = project root).
        x, y: position in pixels on the frame.
        scale: resize multiplier (1.0 = original size).
        angle: rotation in degrees, CLOCKWISE.
        anchor: "center" or "topleft".

    Sprites partially or fully outside the frame are clipped safely.
    """
    sprite = _get_cached_sprite(png_path, scale, angle)
    sprite_h, sprite_w = sprite.shape[:2]

    if anchor == "center":
        x = int(x - sprite_w / 2)
        y = int(y - sprite_h / 2)
    elif anchor == "topleft":
        x, y = int(x), int(y)
    else:
        raise ValueError(f"Unknown anchor '{anchor}', expected 'center' or 'topleft'")

    frame_h, frame_w = frame.shape[:2]

    fx1, fy1 = max(x, 0), max(y, 0)
    fx2, fy2 = min(x + sprite_w, frame_w), min(y + sprite_h, frame_h)
    if fx1 >= fx2 or fy1 >= fy2:
        return

    sx1, sy1 = fx1 - x, fy1 - y
    sx2, sy2 = sx1 + (fx2 - fx1), sy1 + (fy2 - fy1)

    region = sprite[sy1:sy2, sx1:sx2]
    dst = frame[fy1:fy2, fx1:fx2]

    # premultiplied "over":  out = src_premult + dst * (1 - alpha)
    inv_alpha = 1.0 - region[:, :, 3:4].astype(np.float32) * (1.0 / 255.0)
    out = dst.astype(np.float32) * inv_alpha + region[:, :, :3]
    dst[:] = out.astype(np.uint8)


def get_sprite_size(png_path, scale=1.0):
    """(width, height) in pixels of the unrotated sprite at a given scale."""
    sprite = _get_cached_sprite(png_path, scale, 0.0)
    h, w = sprite.shape[:2]
    return w, h


def clear_sprite_cache():
    """Free all cached sprites (variants and decoded originals)."""
    _sprite_cache.clear()
    _base_cache.clear()


def preload_variants(png_path, scales, angle_step=ANGLE_BUCKET_DEG):
    """
    Precompute every (scale, angle-bucket) variant up front so nothing in the
    render loop ever resizes/rotates. Call once at game load, not per frame.
    Pass the exact scale values you will use in draw_sprite. Silently no-ops
    if the file doesn't exist (the game falls back to its placeholder).
    """
    try:
        for angle in range(0, 360, angle_step):
            for scale in scales:
                _get_cached_sprite(png_path, scale, float(angle))
    except FileNotFoundError:
        pass