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

from engine.sprites import draw_sprite, get_sprite_size

ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")

# (sprite filename, fallback color BGR, points, fallback radius px)
FRUIT_TYPES = [
    ("apple.png", (60, 60, 220), 10, 45),
    ("orange.png", (0, 150, 255), 10, 45),
    ("watermelon.png", (60, 180, 60), 15, 55),
    ("lemon.png", (40, 220, 230), 10, 40),
]

BOMB_SPRITE = "bomb.png"
BOMB_COLOR = (40, 40, 40)
BOMB_RADIUS = 45
BOMB_CHANCE = 0.15

GRAVITY = 900.0  # px/s^2

_missing_sprite_warned = set()


def _sprite_path(filename):
    return os.path.join(ASSET_DIR, filename)


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
            self.color = BOMB_COLOR
            self.points = 0
            self.fallback_radius = BOMB_RADIUS
        else:
            self.sprite, self.color, self.points, self.fallback_radius = random.choice(FRUIT_TYPES)

        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.scale = random.uniform(0.85, 1.2)
        self.angle = random.uniform(0, 360)
        self.spin_speed = random.uniform(-120, 120)  # deg/sec, purely visual

        self.sliced = False
        self.slice_time = None
        self.alive = True  # False once it should be removed from the list

        self.radius = _sprite_radius(self.sprite, self.scale, self.fallback_radius)

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
        scale = self.scale
        if self.sliced:
            # cheap slice effect: draw two offset halves fading via extra spin
            elapsed = time.time() - self.slice_time
            offset = elapsed * 160
            _draw_fruit_sprite(frame, self.sprite, self.x - offset, self.y, scale * 0.5,
                                self.angle - 20, self.color, self.fallback_radius)
            _draw_fruit_sprite(frame, self.sprite, self.x + offset, self.y, scale * 0.5,
                                self.angle + 20, self.color, self.fallback_radius)
        else:
            _draw_fruit_sprite(frame, self.sprite, self.x, self.y, scale, self.angle,
                                self.color, self.fallback_radius)