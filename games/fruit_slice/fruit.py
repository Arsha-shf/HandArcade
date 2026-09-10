"""
games/fruit_slice/fruit.py

The Fruit entity: falling physics, slice detection, drawing (with a
placeholder-circle fallback if the PNG asset isn't in assets/ yet).
"""

import math
import os
import random
import time

import cv2

from engine.sprites import ANGLE_BUCKET_DEG, draw_sprite, get_sprite_size, preload_variants

ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")

# (sprite filename, sliced sprite filename or None, fallback color BGR, points,
#  fallback radius px, base_scale)
#
# base_scale corrects for sprites whose native pixel size doesn't match the
# ~90px effective diameter most fruits are authored at. It's computed as
# target_diameter / native_max_dimension and is applied ONLY to the real
# sprite draw, never to the fallback circle.
FRUIT_TYPES = [
    ("apple.png", None, (60, 60, 220), 10, 45, 1.0),
    ("orange.png", None, (0, 150, 255), 10, 45, 1.0),
    ("watermelon.png", None, (60, 180, 60), 15, 55, 1.0),
    ("lemon.png", None, (40, 220, 230), 10, 40, 1.0),
    # baste/baz are 208x209 native px. Sized to match watermelon (the
    # biggest fruit, fallback_radius=55 -> target diameter 110px):
    # base_scale = 110 / 209 ≈ 0.526.
    ("baste.png", "baz.png", (90, 140, 200), 12, 55, 110 / 209),
]

BOMB_SPRITE = "bomb.png"
BOMB_COLOR = (40, 40, 40)
BOMB_RADIUS = 45
BOMB_CHANCE = 0.15

GRAVITY = 900.0  # px/s^2

# Discrete visual-variety scale multipliers, used INSTEAD OF a continuous
# random.uniform(). Continuous per-instance scale means every fruit gets a
# scale value the sprite cache has never seen, forcing a fresh resize+rotate
# right when it spawns -- that's what causes the hitch when a fruit "comes
# onto the screen". A small fixed set means every possible value gets
# preloaded once at startup (see _warmup_sprite_cache below) and gameplay
# never triggers image processing again.
SCALE_VARIANTS = (0.85, 0.95, 1.05, 1.15)

_missing_sprite_warned = set()


def _sprite_path(filename):
    return os.path.join(ASSET_DIR, filename)


def _warmup_sprite_cache():
    """
    Precompute every (sprite, scale, angle-bucket) combo this game will ever
    draw, once, at import time -- before the render loop starts. This is
    what actually kills the on-screen stutter: without it, the FIRST time a
    given scale/angle combo is needed mid-game, cv2 has to resize + rotate
    right then, on that frame, which is the hitch you're seeing.

    A short one-time delay at game launch is the tradeoff, in exchange for
    zero image-processing cost during actual gameplay frames.
    """
    all_types = list(FRUIT_TYPES) + [(BOMB_SPRITE, None, BOMB_COLOR, 0, BOMB_RADIUS, 1.0)]
    for sprite, sliced_sprite, _color, _points, _fallback_radius, base_scale in all_types:
        full_scales = [round(v * base_scale, 3) for v in SCALE_VARIANTS]
        preload_variants(sprite, full_scales, angle_step=ANGLE_BUCKET_DEG)
        if sliced_sprite:
            preload_variants(sliced_sprite, full_scales, angle_step=ANGLE_BUCKET_DEG)
        else:
            # no dedicated sliced sprite -> draw() shrinks the whole sprite to
            # half-scale for the two "halves", which is a different scale
            # value than the whole-fruit draw. Preload that too.
            half_scales = [round(s * 0.5, 3) for s in full_scales]
            preload_variants(sprite, half_scales, angle_step=ANGLE_BUCKET_DEG)


_warmup_sprite_cache()


def _draw_fruit_sprite(frame, filename, x, y, scale, angle, fallback_color, fallback_radius):
    path = _sprite_path(filename)
    try:
        draw_sprite(frame, path, x, y, scale=scale, angle=angle, anchor="center")
    except FileNotFoundError:
        if path not in _missing_sprite_warned:
            _missing_sprite_warned.add(path)
            print(f"[fruit_slice] Missing sprite '{path}', drawing placeholder circle instead.")
        cv2.circle(frame, (int(x), int(y)), int(fallback_radius * scale), fallback_color, -1)
        cv2.circle(frame, (int(x), int(y)), int(fallback_radius * scale), (255, 255, 255), 2)


def _sprite_radius(filename, scale, fallback_radius):
    path = _sprite_path(filename)
    try:
        w, h = get_sprite_size(path, scale=scale)
        return max(w, h) / 2.0
    except FileNotFoundError:
        return fallback_radius * scale


class Fruit:
    """A single falling fruit (or bomb) with simple projectile physics."""

    def __init__(self, x, y, vx, vy, frame_w, frame_h):
        self.frame_w = frame_w
        self.frame_h = frame_h

        self.is_bomb = random.random() < BOMB_CHANCE
        if self.is_bomb:
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

        # Picked from a small fixed set (see SCALE_VARIANTS) instead of a
        # continuous random float, so every possible value was already
        # preloaded into the sprite cache at startup -- no mid-game misses.
        self.variance_scale = random.choice(SCALE_VARIANTS)
        self.scale = self.variance_scale
        self.sprite_scale = round(self.variance_scale * self.base_scale, 3)

        self.angle = random.uniform(0, 360)
        self.spin_speed = random.uniform(-120, 120)  # deg/sec, purely visual

        self.sliced = False
        self.slice_time = None
        self.alive = True  # False once it should be removed from the list

        self.radius = _sprite_radius(self.sprite, self.sprite_scale, self.fallback_radius)
        if not os.path.exists(_sprite_path(self.sprite)):
            self.radius = self.fallback_radius * self.scale

    def update(self, dt):
        self.vy += GRAVITY * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle = (self.angle + self.spin_speed * dt) % 360

        if self.sliced:
            # sliced fruit keeps falling briefly (with a bit more "pop") then disappears
            if time.time() - self.slice_time > 0.35:
                self.alive = False
            return

        if self.y - self.radius > self.frame_h:
            self.alive = False  # fell off the bottom

    def offscreen_bottom_uncollected(self):
        """True the single frame it falls past the bottom without being sliced."""
        return (not self.sliced) and (self.y - self.radius > self.frame_h) and self.alive

    def contains_point(self, px, py):
        return math.hypot(px - self.x, py - self.y) <= self.radius

    def segment_intersects(self, x1, y1, x2, y2):
        """True if the segment (x1,y1)-(x2,y2) passes within radius of the fruit."""
        dx, dy = x2 - x1, y2 - y1
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq == 0:
            return self.contains_point(x1, y1)
        t = ((self.x - x1) * dx + (self.y - y1) * dy) / seg_len_sq
        t = max(0.0, min(1.0, t))
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        return math.hypot(self.x - closest_x, self.y - closest_y) <= self.radius

    def slice(self):
        self.sliced = True
        self.slice_time = time.time()
        # give the two "halves" a little outward kick for a nicer pop
        self.vx += random.uniform(-80, 80)
        self.vy -= 120

    def draw(self, frame):
        if self.sliced:
            elapsed = time.time() - self.slice_time
            offset = elapsed * 160

            # if a dedicated sliced sprite exists (e.g. baz.png for baste.png),
            # draw two copies of THAT flying apart; otherwise fall back to the
            # old trick of drawing two shrunk halves of the whole-fruit sprite.
            draw_name = self.sliced_sprite if self.sliced_sprite else self.sprite
            half_scale = self.sprite_scale if self.sliced_sprite else round(self.sprite_scale * 0.5, 3)

            _draw_fruit_sprite(frame, draw_name, self.x - offset, self.y, half_scale,
                                self.angle - 20, self.color, self.fallback_radius)
            _draw_fruit_sprite(frame, draw_name, self.x + offset, self.y, half_scale,
                                self.angle + 20, self.color, self.fallback_radius)
        else:
            _draw_fruit_sprite(frame, self.sprite, self.x, self.y, self.sprite_scale,
                                self.angle, self.color, self.fallback_radius)