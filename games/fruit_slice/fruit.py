"""
games/fruit_slice/fruit.py

The Fruit entity: projectile physics, slice detection, drawing (with a
placeholder-circle fallback if the PNG isn't in assets/ yet).

Units: all pixel values are for a 720px-tall frame and are multiplied by
`ui` (engine.layout.ui_scale). `speed_mult` is a TIME scale: velocities
scale by speed_mult and gravity by speed_mult**2, so a faster fruit follows
the exact same arc, just sooner. (Scaling velocity alone would make fast
fruit fly off the top of the screen.)
"""

import math
import os
import random

import cv2

from engine.paths import resolve
from engine.sprites import draw_sprite, get_sprite_size, preload_variants

ASSET_DIR = "assets"   # relative to the project root (engine.paths resolves it)

# (sprite filename, sliced sprite filename or None, fallback color BGR, points,
#  fallback radius px @720p, base_scale)
# base_scale corrects for sprites whose native size isn't ~90px @720p.
FRUIT_TYPES = [
    ("apple.png", None, (60, 60, 220), 10, 45, 1.0),
    ("orange.png", None, (0, 150, 255), 10, 45, 1.0),
    ("watermelon.png", None, (60, 180, 60), 15, 55, 1.0),
    ("lemon.png", None, (40, 220, 230), 10, 40, 1.0),
    # baste/baz are 208x209 native px, sized to match watermelon (110px).
    ("baste.png", "baz.png", (90, 140, 200), 12, 55, 110 / 209),
]

BOMB_SPRITE = "bomb.png"
BOMB_COLOR = (40, 40, 40)
BOMB_RADIUS = 45

GRAVITY = 900.0          # px/s^2 @720p

# A small fixed set of size variations (instead of a continuous random float)
# keeps the number of distinct sprite-cache entries small.
SCALE_VARIANTS = (0.85, 0.95, 1.05, 1.15)

SLICE_PADDING = 10       # px @720p: forgiving slice reach around fruit
BOMB_HITBOX = 0.85       # bombs are hit a little less easily than they look
SLICED_LIFETIME = 0.35   # seconds the two halves stay on screen

_exists_cache = {}


def _sprite_path(filename):
    return f"{ASSET_DIR}/{filename}"


def _has_sprite(filename):
    """Checked once per file, not once per spawned fruit."""
    if filename not in _exists_cache:
        ok = os.path.exists(resolve(_sprite_path(filename)))
        if not ok:
            print(f"[fruit_slice] Missing sprite '{_sprite_path(filename)}', "
                  "drawing a placeholder circle instead.")
        _exists_cache[filename] = ok
    return _exists_cache[filename]


def warm_up(ui):
    """
    Decode every sprite from disk once and build the unrotated scaled
    versions, BEFORE the round starts. Call at game start, not at import
    time. (engine.sprites keeps one decoded copy per PNG, so the only work
    left during play is a tiny resize/rotate the first time an angle shows
    up -- far too small to notice.)
    """
    all_types = list(FRUIT_TYPES) + [(BOMB_SPRITE, None, BOMB_COLOR, 0, BOMB_RADIUS, 1.0)]
    for sprite, sliced_sprite, _color, _points, _radius, base_scale in all_types:
        scales = [round(v * base_scale * ui, 3) for v in SCALE_VARIANTS]
        if _has_sprite(sprite):
            preload_variants(_sprite_path(sprite), scales, angle_step=360)
            if not sliced_sprite:
                preload_variants(_sprite_path(sprite), [round(s * 0.5, 3) for s in scales],
                                 angle_step=360)
        if sliced_sprite and _has_sprite(sliced_sprite):
            preload_variants(_sprite_path(sliced_sprite), scales, angle_step=360)


def _draw_placeholder(frame, x, y, radius, color, is_bomb, ui):
    r = max(2, int(radius))
    thick = max(1, round(2 * ui))
    cv2.circle(frame, (int(x), int(y)), r, color, -1, cv2.LINE_AA)
    cv2.circle(frame, (int(x), int(y)), r, (0, 0, 255) if is_bomb else (255, 255, 255),
               thick, cv2.LINE_AA)
    if not is_bomb:
        cv2.circle(frame, (int(x - r * 0.35), int(y - r * 0.35)), max(2, int(r * 0.18)),
                   (255, 255, 255), -1, cv2.LINE_AA)


class Fruit:
    """A single fruit (or bomb) with projectile physics."""

    def __init__(self, x, y, vx, vy, frame_w, frame_h, ui=1.0, speed_mult=1.0, is_bomb=False):
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.ui = ui
        self.gravity = GRAVITY * ui * speed_mult * speed_mult

        self.is_bomb = is_bomb
        if is_bomb:
            self.sprite = BOMB_SPRITE
            self.sliced_sprite = None
            self.color = BOMB_COLOR
            self.points = 0
            self.fallback_radius = BOMB_RADIUS
            self.base_scale = 1.0
        else:
            (self.sprite, self.sliced_sprite, self.color, self.points,
             self.fallback_radius, self.base_scale) = random.choice(FRUIT_TYPES)

        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy

        self.variance_scale = random.choice(SCALE_VARIANTS)
        self.sprite_scale = round(self.variance_scale * self.base_scale * ui, 3)
        self.placeholder_scale = self.variance_scale * ui   # for the fallback circle

        self.angle = random.uniform(0, 360)
        self.spin_speed = random.uniform(-120, 120) * speed_mult   # deg/sec, visual only

        self.sliced = False
        self.slice_age = 0.0
        self.alive = True      # False once it should be removed from the list
        self.missed = False    # True if it left the play area without being sliced

        self.has_sprite = _has_sprite(self.sprite)
        if self.has_sprite:
            w, h = get_sprite_size(_sprite_path(self.sprite), scale=self.sprite_scale)
            self.radius = max(w, h) / 2.0
        else:
            self.radius = self.fallback_radius * self.placeholder_scale

    def update(self, dt):
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle = (self.angle + self.spin_speed * dt) % 360

        if self.sliced:
            self.slice_age += dt
            if self.slice_age > SLICED_LIFETIME:
                self.alive = False
            return

        r = self.radius
        fell_off_bottom = self.y - r > self.frame_h and self.vy > 0
        left_sideways = (self.x + r < 0 and self.vx < 0) or (self.x - r > self.frame_w and self.vx > 0)
        if fell_off_bottom or left_sideways:
            self.alive = False
            self.missed = True

    def _hit_radius(self, padding):
        if self.is_bomb:
            return self.radius * BOMB_HITBOX
        return self.radius + padding

    def contains_point(self, px, py, padding=0.0):
        return math.hypot(px - self.x, py - self.y) <= self._hit_radius(padding)

    def segment_intersects(self, x1, y1, x2, y2, padding=0.0):
        """True if the segment (x1,y1)-(x2,y2) passes within reach of the fruit."""
        dx, dy = x2 - x1, y2 - y1
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq == 0:
            return self.contains_point(x1, y1, padding)
        t = ((self.x - x1) * dx + (self.y - y1) * dy) / seg_len_sq
        t = max(0.0, min(1.0, t))
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        return math.hypot(self.x - closest_x, self.y - closest_y) <= self._hit_radius(padding)

    def slice(self):
        self.sliced = True
        self.slice_age = 0.0
        # outward kick for a nicer pop
        self.vx += random.uniform(-80, 80) * self.ui
        self.vy -= 120 * self.ui

    def _draw_one(self, frame, filename, has_sprite, x, y, scale, angle, placeholder_radius):
        if has_sprite:
            draw_sprite(frame, _sprite_path(filename), x, y, scale=scale, angle=angle,
                        anchor="center")
        else:
            _draw_placeholder(frame, x, y, placeholder_radius, self.color, self.is_bomb, self.ui)

    def draw(self, frame):
        if self.sliced:
            offset = self.slice_age * 160 * self.ui

            # dedicated sliced sprite (e.g. baz.png for baste.png) if there is
            # one, else two shrunken copies of the whole-fruit sprite.
            if self.sliced_sprite:
                name, scale = self.sliced_sprite, self.sprite_scale
                has = _has_sprite(self.sliced_sprite)
                ph_radius = self.fallback_radius * self.placeholder_scale * 0.5
            else:
                name, scale = self.sprite, round(self.sprite_scale * 0.5, 3)
                has = self.has_sprite
                ph_radius = self.fallback_radius * self.placeholder_scale * 0.5

            self._draw_one(frame, name, has, self.x - offset, self.y, scale,
                           self.angle - 20, ph_radius)
            self._draw_one(frame, name, has, self.x + offset, self.y, scale,
                           self.angle + 20, ph_radius)
        else:
            self._draw_one(frame, self.sprite, self.has_sprite, self.x, self.y,
                           self.sprite_scale, self.angle, self.radius)