"""
games/catch/objects.py

Defines what a "catch" actually is: object types (apple, star, gem, bomb) and
the FallingObject that spawner.py creates and game.py updates/draws.

Art: sprites live in assets/ (made by tools/build_art.py, 192px wide). If a
sprite file is missing, the object is drawn as a colored circle instead, so
the game never crashes over a missing image.

Sizes: ObjectType.radius is for a 720px-tall frame; spawner.py passes
scale = random * ui. For sprites, sprite_scale = radius / 96 turns the
192px art into a sprite whose half-width equals `radius`.
"""

import math
import os
import random
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2

from engine.paths import resolve
from engine.sprites import draw_sprite, get_sprite_size


@dataclass
class ObjectType:
    name: str
    points: int
    is_bad: bool
    radius: int
    color: Tuple[int, int, int]
    sprite_path: Optional[str] = None
    sprite_scale: float = 1.0
    weight: float = 1.0
    speed_multiplier: float = 1.0
    drift_amp: float = 0.0
    drift_freq: float = 0.08


OBJECT_TYPES = [
    ObjectType("apple", points=1, is_bad=False, radius=32, color=(60, 60, 230),
               sprite_path="assets/apple.png", sprite_scale=32 / 96, weight=5.0),
    ObjectType("star", points=3, is_bad=False, radius=30, color=(30, 210, 250),
               sprite_path="assets/star.png", sprite_scale=30 / 96, weight=1.5,
               speed_multiplier=1.3, drift_amp=42.0, drift_freq=0.10),
    ObjectType("gem", points=5, is_bad=False, radius=28, color=(236, 184, 76),
               sprite_path="assets/gem.png", sprite_scale=28 / 96, weight=0.8,
               speed_multiplier=1.5, drift_amp=30.0, drift_freq=0.12),
    ObjectType("bomb", points=-2, is_bad=True, radius=30, color=(40, 40, 40),
               sprite_path="assets/bomb.png", sprite_scale=30 / 96, weight=2.0,
               speed_multiplier=1.1, drift_amp=22.0, drift_freq=0.07),
]

_exists_cache = {}


def _sprite_exists(path):
    """Checked once per file."""
    if path not in _exists_cache:
        ok = os.path.exists(resolve(path))
        if not ok:
            print(f"[catch] Missing sprite '{path}', drawing a colored circle instead.")
        _exists_cache[path] = ok
    return _exists_cache[path]


def pick_object_type(difficulty=0.0):
    """difficulty 0..1: bombs get up to 2x as likely as the game ramps up."""
    weights = [t.weight * (1.0 + difficulty if t.is_bad else 1.0) for t in OBJECT_TYPES]
    return random.choices(OBJECT_TYPES, weights=weights, k=1)[0]


class FallingObject:
    """A single object currently falling on screen."""

    __slots__ = (
        "obj_type", "x", "y", "vy", "scale", "angle", "spin", "caught", "sprite",
        "base_x", "t", "drift_amp", "drift_freq", "drift_phase", "frame_w",
    )

    def __init__(self, obj_type, x, y, vy, frame_w, scale=1.0, spin=0.0,
                 drift_amp=0.0, drift_freq=0.08):
        self.obj_type = obj_type
        self.sprite = (obj_type.sprite_path
                       if obj_type.sprite_path and _sprite_exists(obj_type.sprite_path) else None)
        self.x = x
        self.y = y
        self.vy = vy
        self.scale = scale * obj_type.sprite_scale if self.sprite else scale
        self.angle = 0.0
        self.spin = spin
        self.caught = False

        self.base_x = x
        self.t = 0.0
        self.drift_amp = drift_amp
        self.drift_freq = drift_freq
        self.drift_phase = random.uniform(0, 2 * math.pi)
        self.frame_w = frame_w

    def update(self, dt_scale=1.0):
        """dt_scale: frame-rate normalizer (1.0 == one frame at 30fps)."""
        self.t += dt_scale
        self.y += self.vy * dt_scale
        self.angle = (self.angle + self.spin * dt_scale) % 360

        if self.drift_amp:
            r = self.radius_px()
            sway = self.drift_amp * math.sin(self.drift_freq * self.t + self.drift_phase)
            self.x = min(max(self.base_x + sway, r), self.frame_w - r)

    def radius_px(self):
        if self.sprite:
            w, h = get_sprite_size(self.sprite, self.scale)
            return max(w, h) / 2
        return self.obj_type.radius * self.scale

    def draw(self, frame):
        if self.sprite:
            draw_sprite(frame, self.sprite, int(self.x), int(self.y),
                        scale=self.scale, angle=self.angle, anchor="center")
        else:
            r = int(self.radius_px())
            cv2.circle(frame, (int(self.x), int(self.y)), r,
                       self.obj_type.color, -1, lineType=cv2.LINE_AA)
            cv2.circle(frame, (int(self.x), int(self.y)), r,
                       (255, 255, 255), 2, lineType=cv2.LINE_AA)

    def is_off_screen(self, frame_h):
        return self.y - self.radius_px() > frame_h