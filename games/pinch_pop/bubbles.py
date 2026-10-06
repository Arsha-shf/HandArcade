"""
Bubble kinds:
    normal  - slow, safe, worth a little
    fast    - quicker + smaller, worth more, harder to land a pinch on
    golden  - rare, big score bonus, extra sparkle
    bomb    - popping it costs points and resets your combo
    chain   - popping it also sweeps up every non-bomb bubble nearby
    shield  - a one-time bomb insurance policy

Difficulty ramps over the round (`progress` 0 -> 1):
    - bubbles rise up to 35% faster
    - bombs get more common (and never appear in the first seconds)
    - fast bubbles get more common
    - spawn interval shrinks (see BubbleManager._spawn_interval)

Pixel values are for a 720px-tall frame; `ui` (engine.layout.ui_scale)
scales them to the real frame.
"""

import math
import random

import cv2
import numpy as np

_KIND_WEIGHTS = {
    "normal": 54,
    "fast": 16,
    "golden": 6,
    "bomb": 6,
    "chain": 6,
    "shield": 6,
}

BOMB_GRACE_SECONDS = 4.0
MAX_ACTIVE = 14
MAX_ACTIVE_FRENZY = 22

_KIND_SPEC = {
    "normal": dict(radius=(30, 44), speed=(70, 120), points=10, wobble=(8, 18), freq=(1.0, 2.0)),
    "fast":   dict(radius=(18, 28), speed=(160, 240), points=20, wobble=(14, 26), freq=(2.5, 4.0)),
    "golden": dict(radius=(32, 40), speed=(90, 140), points=60, wobble=(6, 14), freq=(1.0, 1.8)),
    "bomb":   dict(radius=(26, 36), speed=(80, 130), points=-15, wobble=(10, 20), freq=(1.5, 2.5)),
    "chain":  dict(radius=(34, 42), speed=(90, 130), points=25, wobble=(8, 16), freq=(1.2, 2.0)),
    "shield": dict(radius=(30, 38), speed=(90, 130), points=15, wobble=(8, 16), freq=(1.0, 1.8)),
}

_KIND_COLOR = {
    "normal": ((230, 160, 90), (150, 90, 40)),
    "fast": ((50, 130, 255), (20, 70, 200)),
    "golden": ((0, 215, 255), (0, 150, 210)),
    "bomb": ((45, 45, 45), (0, 0, 190)),
    "chain": ((230, 60, 210), (150, 10, 130)),
    "shield": ((255, 235, 210), (210, 160, 90)),
}

_GROW_IN_SECONDS = 0.15
_GRAVITY = 260.0
_CHAIN_RADIUS = 235.0
_MAX_PARTICLES = 260

PINCH_PADDING = 10   # px @720p: extra reach around a bubble when pinching


def _distance(x1, y1, x2, y2):
    return math.hypot(x1 - x2, y1 - y2)


class Bubble:
    __slots__ = (
        "base_x", "x", "y", "radius", "vy", "kind", "points",
        "fill_color", "border_color", "wobble_amp", "wobble_freq",
        "phase", "age", "ui",
    )

    def __init__(self, base_x, y, kind, ui=1.0, speed_mult=1.0):
        spec = _KIND_SPEC[kind]
        self.ui = ui
        self.base_x = base_x
        self.x = base_x
        self.y = y
        self.radius = random.uniform(*spec["radius"]) * ui
        self.vy = random.uniform(*spec["speed"]) * ui * speed_mult
        self.kind = kind
        self.points = spec["points"]
        self.fill_color, self.border_color = _KIND_COLOR[kind]
        self.wobble_amp = random.uniform(*spec["wobble"]) * ui
        self.wobble_freq = random.uniform(*spec["freq"])
        self.phase = random.uniform(0, 2 * math.pi)
        self.age = 0.0

    def update(self, dt):
        self.age += dt
        self.y -= self.vy * dt
        self.x = self.base_x + math.sin(self.age * self.wobble_freq + self.phase) * self.wobble_amp

    @property
    def display_radius(self):
        grown = min(1.0, self.age / _GROW_IN_SECONDS)
        return self.radius * grown

    def is_off_screen(self):
        return self.y + self.radius < 0

    def contains_point(self, px, py, padding=0.0):
        r = self.display_radius
        if r <= 0:
            return False
        r += padding
        return (px - self.x) ** 2 + (py - self.y) ** 2 <= r * r

    def draw(self, frame):
        r = int(self.display_radius)
        if r <= 0:
            return
        x, y = int(self.x), int(self.y)
        border = max(1, round(2 * self.ui))

        cv2.circle(frame, (x, y), r, self.fill_color, -1, lineType=cv2.LINE_AA)
        cv2.circle(frame, (x, y), r, self.border_color, border, lineType=cv2.LINE_AA)

        hl_r = max(2, int(r * 0.35))
        hl_x, hl_y = x - int(r * 0.35), y - int(r * 0.35)
        cv2.circle(frame, (hl_x, hl_y), hl_r, (255, 255, 255), -1, lineType=cv2.LINE_AA)

        self._draw_face(frame, x, y, r, border)

    def _draw_face(self, frame, x, y, r, w2):
        eye_dx = max(2, int(r * 0.32))
        eye_y = y - int(r * 0.05)
        eye_r = max(1, int(r * 0.11))

        if self.kind == "bomb":
            for ex in (x - eye_dx, x + eye_dx):
                s = eye_r
                cv2.line(frame, (ex - s, eye_y - s), (ex + s, eye_y + s), (0, 0, 0), w2, cv2.LINE_AA)
                cv2.line(frame, (ex - s, eye_y + s), (ex + s, eye_y - s), (0, 0, 0), w2, cv2.LINE_AA)
            cv2.line(frame, (x - eye_dx, y + int(r * 0.4)), (x + eye_dx, y + int(r * 0.4)),
                     (0, 0, 0), w2, cv2.LINE_AA)
            fuse_top = (x, y - r - int(r * 0.4))
            cv2.line(frame, (x, y - r), fuse_top, (60, 60, 60), w2, cv2.LINE_AA)
            spark_color = (0, 255, 255) if int(self.age * 8) % 2 == 0 else (0, 140, 255)
            cv2.circle(frame, fuse_top, max(2, int(r * 0.14)), spark_color, -1, cv2.LINE_AA)
            return

        if self.kind == "chain":
            link_r = max(3, int(r * 0.22))
            for ox in (-int(r * 0.4), 0, int(r * 0.4)):
                cv2.circle(frame, (x + ox, y), link_r, (255, 255, 255), w2, cv2.LINE_AA)
            return

        if self.kind == "shield":
            pts = np.array([
                [x, y - int(r * 0.55)],
                [x + int(r * 0.45), y - int(r * 0.25)],
                [x + int(r * 0.35), y + int(r * 0.35)],
                [x, y + int(r * 0.55)],
                [x - int(r * 0.35), y + int(r * 0.35)],
                [x - int(r * 0.45), y - int(r * 0.25)],
            ], dtype=np.int32)
            cv2.polylines(frame, [pts], True, (60, 120, 200), w2, cv2.LINE_AA)
            cv2.circle(frame, (x, y), max(2, int(r * 0.12)), (60, 120, 200), -1, cv2.LINE_AA)
            return

        for ex in (x - eye_dx, x + eye_dx):
            cv2.circle(frame, (ex, eye_y), eye_r, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, (ex, eye_y), max(1, int(eye_r * 0.5)), (20, 20, 20), -1, cv2.LINE_AA)

        mouth_y = y + int(r * 0.25)
        if self.kind == "fast":
            cv2.circle(frame, (x, mouth_y), max(2, int(r * 0.16)), (20, 20, 20), -1, cv2.LINE_AA)
        else:
            axes = (max(2, int(r * 0.35)), max(2, int(r * 0.22)))
            cv2.ellipse(frame, (x, mouth_y), axes, 0, 20, 160, (20, 20, 20), w2, cv2.LINE_AA)

        if self.kind == "golden":
            sp = max(3, int(5 * self.ui))
            for sx, sy in ((x + r * 0.55, y - r * 0.55), (x - r * 0.6, y + r * 0.1)):
                sx, sy = int(sx), int(sy)
                cv2.line(frame, (sx - sp, sy), (sx + sp, sy), (255, 255, 255), w2, cv2.LINE_AA)
                cv2.line(frame, (sx, sy - sp), (sx, sy + sp), (255, 255, 255), w2, cv2.LINE_AA)


class Particle:

    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "radius", "color", "gravity")

    def __init__(self, x, y, vx, vy, life, radius, color, gravity):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = life
        self.max_life = life
        self.radius = radius
        self.color = color
        self.gravity = gravity

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.life -= dt

    @property
    def alive(self):
        return self.life > 0

    def draw(self, frame):
        t = max(0.0, self.life / self.max_life)
        r = max(1, int(self.radius * t))
        cv2.circle(frame, (int(self.x), int(self.y)), r, self.color, -1, cv2.LINE_AA)


def _burst(x, y, kind, ui):
    fill_color, border_color = _KIND_COLOR[kind]
    count = {"normal": 10, "fast": 12, "golden": 22, "bomb": 16, "chain": 26, "shield": 14}[kind]
    particles = []
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(60, 220 if kind != "golden" else 320) * ui
        vx, vy = math.cos(angle) * speed, math.sin(angle) * speed
        color = fill_color if random.random() < 0.6 else border_color
        particles.append(Particle(x, y, vx, vy, life=random.uniform(0.3, 0.6),
                                   radius=random.uniform(3, 7) * ui, color=color,
                                   gravity=_GRAVITY * ui))
    return particles


class BubbleManager:
    def __init__(self, ui=1.0):
        self.ui = ui
        self.bubbles = []
        self.particles = []
        self._spawn_timer = 0.0
        self.spawn_rate_multiplier = 1.0

    def _spawn_interval(self, elapsed):
        return max(0.4, 1.1 - elapsed * 0.015)

    def _pick_kind(self, elapsed, progress):
        weights = dict(_KIND_WEIGHTS)
        weights["bomb"] = 0 if elapsed < BOMB_GRACE_SECONDS else 6 + 8 * progress
        weights["fast"] = 16 + 14 * progress
        kinds = list(weights)
        return random.choices(kinds, weights=[weights[k] for k in kinds], k=1)[0]

    def _pick_x(self, frame_w, frame_h):
        """Of a few random columns, take the one farthest from bubbles that
        are still near the bottom, so new bubbles don't spawn on top of each
        other."""
        margin = 50 * self.ui
        lo, hi = margin, max(margin + 1, frame_w - margin)
        low_band = [b for b in self.bubbles if b.y > frame_h * 0.7]
        best_x, best_gap = None, -1e9
        for _ in range(6):
            x = random.uniform(lo, hi)
            gap = min((abs(x - b.x) - b.radius for b in low_band), default=1e9)
            if gap > best_gap:
                best_x, best_gap = x, gap
        return best_x

    def _spawn(self, frame_w, frame_h, elapsed, progress):
        kind = self._pick_kind(elapsed, progress)
        base_x = self._pick_x(frame_w, frame_h)
        y = frame_h + 40 * self.ui
        self.bubbles.append(Bubble(base_x, y, kind, self.ui, speed_mult=1.0 + 0.35 * progress))

    def update(self, dt, frame_w, frame_h, elapsed, progress=0.0):
        self._spawn_timer -= dt
        cap = MAX_ACTIVE_FRENZY if self.spawn_rate_multiplier > 1.0 else MAX_ACTIVE
        if self._spawn_timer <= 0 and len(self.bubbles) < cap:
            self._spawn(frame_w, frame_h, elapsed, progress)
            self._spawn_timer = self._spawn_interval(elapsed) / max(0.1, self.spawn_rate_multiplier)

        for bubble in self.bubbles:
            bubble.update(dt)
        self.bubbles = [b for b in self.bubbles if not b.is_off_screen()]

        for particle in self.particles:
            particle.update(dt)
        self.particles = [p for p in self.particles if p.alive]
        if len(self.particles) > _MAX_PARTICLES:
            self.particles = self.particles[-_MAX_PARTICLES:]

    def try_pop(self, px, py):
        padding = PINCH_PADDING * self.ui
        hit = None
        for bubble in reversed(self.bubbles):
            if bubble.contains_point(px, py, padding):
                hit = bubble
                break

        if hit is None:
            return []

        self.bubbles.remove(hit)
        self.particles.extend(_burst(hit.x, hit.y, hit.kind, self.ui))
        popped = [hit]

        if hit.kind == "chain":
            chain_radius = _CHAIN_RADIUS * self.ui
            nearby = [
                b for b in self.bubbles
                if b.kind != "bomb" and _distance(b.x, b.y, hit.x, hit.y) <= chain_radius
            ]
            for b in nearby:
                self.bubbles.remove(b)
                self.particles.extend(_burst(b.x, b.y, b.kind, self.ui))
                popped.append(b)

        return popped

    def draw(self, frame):
        for bubble in self.bubbles:
            bubble.draw(frame)
        for particle in self.particles:
            particle.draw(frame)

    def reset(self):
        self.bubbles.clear()
        self.particles.clear()
        self._spawn_timer = 0.0
        self.spawn_rate_multiplier = 1.0