"""
games/catch/spawner.py

Owns spawn timing and difficulty ramp. game.py calls update(dt_scale) once
per frame and gets back the objects that fell off-screen this frame (so it
can score misses) -- it does NOT silently delete them, because game.py
needs to know the difference between "still falling" and "just missed".

dt_scale is a frame-rate normalizer (1.0 == one frame at the 30fps all of
this is tuned against). Passing real elapsed time in from game.py instead
of assuming a fixed frame keeps spawn rate / fall speed / difficulty ramp
consistent even when the webcam's actual frame rate wobbles.
"""

import random

from .objects import FallingObject, pick_object_type

class Spawner:
    def __init__(self, frame_w, frame_h, base_interval_frames=38, min_interval_frames=9,
                 base_fall_speed=7.5, max_fall_speed=22.0, ramp_seconds=45, fps=30):
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.base_interval = base_interval_frames
        self.min_interval = min_interval_frames
        self.base_speed = base_fall_speed
        self.max_speed = max_fall_speed
        self.ramp_frames = ramp_seconds * fps

        self.objects = []
        self._frame_count = 0.0
        self._frames_since_spawn = 0.0
        self._next_interval = self.base_interval

    def _difficulty(self):
        """0.0 at start, 1.0 once ramp_frames have passed. Eased
        (1 - (1-d)^2) rather than linear so it bites harder early --
        the game is fast and busy well before the ramp finishes, which
        is the point."""
        d = min(1.0, self._frame_count / self.ramp_frames)
        return 1 - (1 - d) ** 2

    def _current_interval(self):
        d = self._difficulty()
        return int(self.base_interval - d * (self.base_interval - self.min_interval))

    def _current_speed_range(self):
        d = self._difficulty()
        lo = self.base_speed + d * (self.max_speed - self.base_speed) * 0.4
        hi = self.base_speed + d * (self.max_speed - self.base_speed)
        return lo, hi

    def update(self, dt_scale=1.0):
        """Advance timers/objects by dt_scale, spawn if due, and pull off
        anything that just went past the bottom edge. Returns that dropped
        list."""
        self._frame_count += dt_scale
        self._frames_since_spawn += dt_scale

        if self._frames_since_spawn >= self._next_interval:
            self._spawn_one()
            self._frames_since_spawn = 0.0
            self._next_interval = self._current_interval()

            if self._difficulty() > 0.4 and random.random() < 0.15 * self._difficulty():
                self._spawn_one()

        for obj in self.objects:
            obj.update(dt_scale)

        still_alive, dropped = [], []
        for obj in self.objects:
            if obj.is_off_screen(self.frame_h):
                dropped.append(obj)
            else:
                still_alive.append(obj)
        self.objects = still_alive
        return dropped

    def _spawn_one(self):
        obj_type = pick_object_type()
        margin = 50
        x = random.randint(margin, max(margin + 1, self.frame_w - margin))
        y = -40
        lo, hi = self._current_speed_range()
        vy = random.uniform(lo, hi) * obj_type.speed_multiplier
        scale = random.uniform(0.9, 1.2)
        spin = random.uniform(-3, 3)

        drift_amp = obj_type.drift_amp * random.uniform(0.7, 1.3) if obj_type.drift_amp else 0.0
        drift_freq = obj_type.drift_freq * random.uniform(0.85, 1.15)

        self.objects.append(FallingObject(
            obj_type, x, y, vy, self.frame_w,
            scale=scale, spin=spin, drift_amp=drift_amp, drift_freq=drift_freq,
        ))

    def reset(self):
        self.objects = []
        self._frame_count = 0.0
        self._frames_since_spawn = 0.0
        self._next_interval = self.base_interval