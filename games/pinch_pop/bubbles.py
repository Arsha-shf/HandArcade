"""
Bubble kinds (this is the "fun" knob -- add more here later for the
harder difficulty tiers mentioned in the ticket):
    normal  - slow, safe, worth a little
    fast    - quicker + smaller, worth more, harder to land a pinch on
    golden  - rare, big score bonus, extra sparkle
    bomb    - rare "gotcha" bubble -- popping it costs points and resets
              your combo, so players have to actually look before they
              pinch instead of just clawing at everything on screen
"""

import math
import random

import cv2

_KIND_WEIGHTS = {
    "normal": 62,
    "fast": 23,
    "golden": 7,
    "bomb": 8,
}

_KIND_SPEC = {
    "normal": dict(radius=(30, 44), speed=(70, 120), points=10, wobble=(8, 18), freq=(1.0, 2.0)),
    "fast":   dict(radius=(18, 28), speed=(160, 240), points=20, wobble=(14, 26), freq=(2.5, 4.0)),
    "golden": dict(radius=(32, 40), speed=(90, 140), points=60, wobble=(6, 14), freq=(1.0, 1.8)),
    "bomb":   dict(radius=(26, 36), speed=(80, 130), points=-15, wobble=(10, 20), freq=(1.5, 2.5)),
}

_KIND_COLOR = {
    "normal": ((230, 160, 90), (150, 90, 40)),
    "fast": ((50, 130, 255), (20, 70, 200)),
    "golden": ((0, 215, 255), (0, 150, 210)),
    "bomb": ((45, 45, 45), (0, 0, 190)),
}

_GROW_IN_SECONDS = 0.15
_GRAVITY = 260.0 


class Bubble:
    __slots__ = (
        "base_x", "x", "y", "radius", "vy", "kind", "points",
        "fill_color", "border_color", "wobble_amp", "wobble_freq",
        "phase", "age",
    )

    def __init__(self, base_x, y, kind):
        spec = _KIND_SPEC[kind]
        self.base_x = base_x
        self.x = base_x
        self.y = y
        self.radius = random.uniform(*spec["radius"])
        self.vy = random.uniform(*spec["speed"])
        self.kind = kind
        self.points = spec["points"]
        self.fill_color, self.border_color = _KIND_COLOR[kind]
        self.wobble_amp = random.uniform(*spec["wobble"])
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

    def contains_point(self, px, py):
        r = self.display_radius
        if r <= 0:
            return False
        return (px - self.x) ** 2 + (py - self.y) ** 2 <= r * r

    def draw(self, frame):
        r = int(self.display_radius)
        if r <= 0:
            return
        x, y = int(self.x), int(self.y)

        cv2.circle(frame, (x, y), r, self.fill_color, -1, lineType=cv2.LINE_AA)
        cv2.circle(frame, (x, y), r, self.border_color, 2, lineType=cv2.LINE_AA)

        hl_r = max(2, int(r * 0.35))
        hl_x, hl_y = x - int(r * 0.35), y - int(r * 0.35)
        cv2.circle(frame, (hl_x, hl_y), hl_r, (255, 255, 255), -1, lineType=cv2.LINE_AA)

        self._draw_face(frame, x, y, r)

    def _draw_face(self, frame, x, y, r):
        eye_dx = max(2, int(r * 0.32))
        eye_y = y - int(r * 0.05)
        eye_r = max(1, int(r * 0.11))

        if self.kind == "bomb":
            for ex in (x - eye_dx, x + eye_dx):
                s = eye_r
                cv2.line(frame, (ex - s, eye_y - s), (ex + s, eye_y + s), (0, 0, 0), 2, cv2.LINE_AA)
                cv2.line(frame, (ex - s, eye_y + s), (ex + s, eye_y - s), (0, 0, 0), 2, cv2.LINE_AA)
            cv2.line(frame, (x - eye_dx, y + int(r * 0.4)), (x + eye_dx, y + int(r * 0.4)), (0, 0, 0), 2, cv2.LINE_AA)
            fuse_top = (x, y - r - int(r * 0.4))
            cv2.line(frame, (x, y - r), fuse_top, (60, 60, 60), 2, cv2.LINE_AA)
            spark_color = (0, 255, 255) if int(self.age * 8) % 2 == 0 else (0, 140, 255)
            cv2.circle(frame, fuse_top, max(2, int(r * 0.14)), spark_color, -1, cv2.LINE_AA)
            return

        for ex in (x - eye_dx, x + eye_dx):
            cv2.circle(frame, (ex, eye_y), eye_r, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, (ex, eye_y), max(1, int(eye_r * 0.5)), (20, 20, 20), -1, cv2.LINE_AA)

        mouth_y = y + int(r * 0.25)
        if self.kind == "fast":
            cv2.circle(frame, (x, mouth_y), max(2, int(r * 0.16)), (20, 20, 20), -1, cv2.LINE_AA)
        else:
            axes = (max(2, int(r * 0.35)), max(2, int(r * 0.22)))
            cv2.ellipse(frame, (x, mouth_y), axes, 0, 20, 160, (20, 20, 20), 2, cv2.LINE_AA)

        if self.kind == "golden":
            for sx, sy, s in ((x + r * 0.55, y - r * 0.55, 6), (x - r * 0.6, y + r * 0.1, 4)):
                sx, sy = int(sx), int(sy)
                cv2.line(frame, (sx - s, sy), (sx + s, sy), (255, 255, 255), 2, cv2.LINE_AA)
                cv2.line(frame, (sx, sy - s), (sx, sy + s), (255, 255, 255), 2, cv2.LINE_AA)


class Particle:

    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "radius", "color")

    def __init__(self, x, y, vx, vy, life, radius, color):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = life
        self.max_life = life
        self.radius = radius
        self.color = color

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += _GRAVITY * dt
        self.life -= dt

    @property
    def alive(self):
        return self.life > 0

    def draw(self, frame):
        t = max(0.0, self.life / self.max_life)
        r = max(1, int(self.radius * t))
        cv2.circle(frame, (int(self.x), int(self.y)), r, self.color, -1, cv2.LINE_AA)


def _burst(x, y, kind):
    fill_color, border_color = _KIND_COLOR[kind]
    count = {"normal": 10, "fast": 12, "golden": 22, "bomb": 16}[kind]
    particles = []
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(60, 220 if kind != "golden" else 320)
        vx, vy = math.cos(angle) * speed, math.sin(angle) * speed
        color = fill_color if random.random() < 0.6 else border_color
        particles.append(Particle(x, y, vx, vy, life=random.uniform(0.3, 0.6),
                                   radius=random.uniform(3, 7), color=color))
    return particles


class BubbleManager:
    def __init__(self):
        self.bubbles = []
        self.particles = []
        self._spawn_timer = 0.0

    def _spawn_interval(self, elapsed):
        # Ramps from ~1.1s down to ~0.4s between spawns over the first
        # 45s. TODO(harder-difficulty ticket): make this configurable
        # per-difficulty instead of a single hardcoded curve.
        return max(0.4, 1.1 - elapsed * 0.015)

    def _pick_kind(self):
        kinds, weights = zip(*_KIND_WEIGHTS.items())
        return random.choices(kinds, weights=weights, k=1)[0]

    def _spawn(self, frame_w, frame_h):
        kind = self._pick_kind()
        margin = 50
        base_x = random.uniform(margin, max(margin + 1, frame_w - margin))
        y = frame_h + 40
        self.bubbles.append(Bubble(base_x, y, kind))

    def update(self, dt, frame_w, frame_h, elapsed):
        self._spawn_timer -= dt
        if self._spawn_timer <= 0:
            self._spawn(frame_w, frame_h)
            self._spawn_timer = self._spawn_interval(elapsed)

        for bubble in self.bubbles:
            bubble.update(dt)
        self.bubbles = [b for b in self.bubbles if not b.is_off_screen()]

        for particle in self.particles:
            particle.update(dt)
        self.particles = [p for p in self.particles if p.alive]

    def try_pop(self, px, py):
        for bubble in reversed(self.bubbles):
            if bubble.contains_point(px, py):
                self.bubbles.remove(bubble)
                self.particles.extend(_burst(bubble.x, bubble.y, bubble.kind))
                return bubble
        return None

    def draw(self, frame):
        for bubble in self.bubbles:
            bubble.draw(frame)
        for particle in self.particles:
            particle.draw(frame)

    def reset(self):
        self.bubbles.clear()
        self.particles.clear()
        self._spawn_timer = 0.0