"""
engine/sprites.py

PNG overlay system shared by every HandArcade game.

Loads transparent PNGs (e.g. art drawn on iPad) and draws them onto a live
BGR camera frame with proper alpha blending, so edges look clean instead
of boxy.

Usage:
    from engine.sprites import draw_sprite

    draw_sprite(frame, "assets/apple.png", x=300, y=150, scale=1.0)
    draw_sprite(frame, "assets/apple.png", x=300, y=150, scale=1.5, angle=30)
"""

import cv2
import numpy as np

# Cache of loaded sprite images, keyed by (path, scale, angle) so we never
# hit disk or redo a resize/rotation more than once per unique variant.
_sprite_cache = {}


def _load_sprite(path):
    """
    Load a PNG with its alpha channel intact.
    Returns a BGRA numpy array. Raises FileNotFoundError if the path is bad,
    since a silently-missing sprite is worse than a loud crash while developing.
    """
    image = cv2.imread(path, cv2.IMREAD_UNCHANGED)

    if image is None:
        raise FileNotFoundError(f"Could not load sprite: {path}")

    # If the PNG has no alpha channel (e.g. someone exported as JPG-like PNG),
    # add a fully-opaque one so the rest of the pipeline works unchanged.
    if image.shape[2] == 3:
        alpha = np.full(image.shape[:2], 255, dtype=image.dtype)
        image = cv2.merge((image[:, :, 0], image[:, :, 1], image[:, :, 2], alpha))

    return image


def _get_cached_sprite(path, scale, angle):
    """Return a (possibly cached) resized + rotated BGRA sprite."""
    cache_key = (path, round(scale, 3), round(angle, 1))

    if cache_key in _sprite_cache:
        return _sprite_cache[cache_key]

    sprite = _load_sprite(path)

    if scale != 1.0:
        new_w = max(1, int(sprite.shape[1] * scale))
        new_h = max(1, int(sprite.shape[0] * scale))
        sprite = cv2.resize(sprite, (new_w, new_h), interpolation=cv2.INTER_AREA)

    if angle != 0.0:
        sprite = _rotate_sprite(sprite, angle)

    _sprite_cache[cache_key] = sprite
    return sprite


def _rotate_sprite(sprite, angle):
    """Rotate a BGRA sprite around its center, expanding the canvas so nothing gets cropped."""
    h, w = sprite.shape[:2]
    center = (w / 2, h / 2)

    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    # Expand canvas to fit the rotated bounding box
    cos = abs(rotation_matrix[0, 0])
    sin = abs(rotation_matrix[0, 1])
    new_w = int(h * sin + w * cos)
    new_h = int(h * cos + w * sin)

    rotation_matrix[0, 2] += (new_w / 2) - center[0]
    rotation_matrix[1, 2] += (new_h / 2) - center[1]

    return cv2.warpAffine(
        sprite,
        rotation_matrix,
        (new_w, new_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )


def draw_sprite(frame, png_path, x, y, scale=1.0, angle=0.0, anchor="center"):
    """
    Draw a transparent PNG onto a BGR frame at (x, y) with alpha blending.

    Args:
        frame: the BGR camera frame (numpy array), modified in place.
        png_path: path to a transparent PNG.
        x, y: position in pixels on the frame.
        scale: resize multiplier (1.0 = original size).
        angle: rotation in degrees, clockwise.
        anchor: "center" (default) places (x, y) at the sprite's center,
                which is usually what you want for falling fruit/bubbles/etc.
                "topleft" places (x, y) at the sprite's top-left corner.

    Sprites that fall fully or partially outside the frame are clipped
    safely (no crash, no wraparound).
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

    # Clip the region so we only ever write inside the frame's bounds
    frame_x1, frame_y1 = max(x, 0), max(y, 0)
    frame_x2, frame_y2 = min(x + sprite_w, frame_w), min(y + sprite_h, frame_h)

    if frame_x1 >= frame_x2 or frame_y1 >= frame_y2:
        return  # Sprite is entirely off-frame, nothing to draw

    sprite_x1, sprite_y1 = frame_x1 - x, frame_y1 - y
    sprite_x2, sprite_y2 = sprite_x1 + (frame_x2 - frame_x1), sprite_y1 + (frame_y2 - frame_y1)

    sprite_region = sprite[sprite_y1:sprite_y2, sprite_x1:sprite_x2]
    frame_region = frame[frame_y1:frame_y2, frame_x1:frame_x2]

    alpha = sprite_region[:, :, 3:4].astype(float) / 255.0
    sprite_rgb = sprite_region[:, :, :3].astype(float)
    frame_rgb = frame_region.astype(float)

    blended = alpha * sprite_rgb + (1 - alpha) * frame_rgb
    frame[frame_y1:frame_y2, frame_x1:frame_x2] = blended.astype(np.uint8)


def get_sprite_size(png_path, scale=1.0):
    """Return (width, height) in pixels for a sprite at a given scale, useful for collision math."""
    sprite = _get_cached_sprite(png_path, scale, 0.0)
    h, w = sprite.shape[:2]
    return w, h


def clear_sprite_cache():
    """Free cached sprite images. Rarely needed, but handy for tests or hot-reloading art."""
    _sprite_cache.clear()