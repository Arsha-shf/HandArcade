"""
games/catch/objects.py

Defines what a "catch" actually is: object types (good fruit, bonus star,
bad bomb) and the FallingObject that spawner.py creates and game.py
updates/draws every frame.
"""

import random
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2

from engine.sprites import draw_sprite, get_sprite_size


@dataclass
class ObjectType:
    name: str
    points: int
    is_bad: bool
    radius: int                       # collision radius in px, used when no sprite is set
    color: Tuple[int, int, int]       # BGR fallback color if sprite_path is None
    sprite_path: Optional[str] = None
    weight: float = 1.0                # relative spawn probability
    speed_multiplier: float = 1.0


# sprite_path is None on purpose -- the game is fully playable with drawn
# circles so you're not blocked waiting on iPad art. Once you export PNGs
# (transparent, via engine/sprites.py), just point sprite_path at them,
# e.g. sprite_path="assets/apple.png". Nothing else needs to change.
OBJECT_TYPES = [
    ObjectType("apple", points=1,  is_bad=False, radius=28, color=(60, 60, 230),
               sprite_path=None, weight=5.0),
    ObjectType("star",  points=3,  is_bad=False, radius=24, color=(30, 210, 250),
               sprite_path=None, weight=1.5, speed_multiplier=1.3),
    ObjectType("bomb",  points=-2, is_bad=True,  radius=26, color=(40, 40, 40),
               sprite_path=None, weight=2.0, speed_multiplier=1.1),
]


def pick_object_type():
    weights = [t.weight for t in OBJECT_TYPES]
    return random.choices(OBJECT_TYPES, weights=weights, k=1)[0]


class FallingObject:
    """A single object currently falling on screen."""

    __slots__ = ("obj_type", "x", "y", "vy", "scale", "angle", "spin", "caught")

    def __init__(self, obj_type, x, y, vy, scale=1.0, spin=0.0):
        self.obj_type = obj_type
        self.x = x
        self.y = y
        self.vy = vy
        self.scale = scale
        self.angle = 0.0
        self.spin = spin       # degrees/frame, purely cosmetic (only matters with a sprite)
        self.caught = False

    def update(self):
        self.y += self.vy
        self.angle = (self.angle + self.spin) % 360

    def radius_px(self):
        if self.obj_type.sprite_path:
            w, h = get_sprite_size(self.obj_type.sprite_path, self.scale)
            return max(w, h) / 2
        return self.obj_type.radius * self.scale

    def draw(self, frame):
        if self.obj_type.sprite_path:
            draw_sprite(frame, self.obj_type.sprite_path, int(self.x), int(self.y),
                        scale=self.scale, angle=self.angle, anchor="center")
        else:
            r = int(self.radius_px())
            cv2.circle(frame, (int(self.x), int(self.y)), r,
                       self.obj_type.color, -1, lineType=cv2.LINE_AA)
            cv2.circle(frame, (int(self.x), int(self.y)), r,
                       (255, 255, 255), 2, lineType=cv2.LINE_AA)

    def is_off_screen(self, frame_h):
        return self.y - self.radius_px() > frame_h