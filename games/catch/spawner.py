"""
games/catch/spawner.py

Owns spawn timing and difficulty ramp. game.py calls update(dt_scale) once
per frame and gets back the objects that fell off-screen this frame (so it
can score misses).

dt_scale is a frame-rate normalizer (1.0 == one frame at 30fps). Speeds are
written in px per 30fps-frame for a 720px-tall frame and multiplied by `ui`
(engine.layout.ui_scale) so they scale with the real camera resolution.
"""

import random

from .objects import FallingObject, pick_object_type


class Spawner:
    def __init__(self, frame_w, frame_h, ui=1.0, base_interval_frames=38, min_interval_frames=9,
                 base_fall_speed=7.5, max_fall_speed=22.0, ramp_seconds=45, fps=30):
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.ui = ui
        self.base_interval = base_interval_frames
        self.min_interval = min_interval_frames
        self.base_speed = base_fall_speed
        self.max_speed = max_fall_speed
        self.ramp_frames = ramp_seconds * fps

        self.objects = []
        self._frame_count = 0.0
        self._frames_since_spawn = 0.0
        self._next_interval = float(self.base_interval)

    def difficulty(self):
        """0.0 at start, 1.0 once the ramp is done. Eased so it bites early."""
        d = min(1.0, self._frame_count / self.ramp_frames)
        return 1 - (1 - d) ** 2

    def _current_interval(self):
        d = self.difficulty()
        return self.base_interval - d * (self.base_interval - self.min_interval)

    def _current_speed_range(self):
        d = self.difficulty()
        lo = self.base_speed + d * (self.max_speed - self.base_speed) * 0.4
        hi = self.base_speed + d * (self.max_speed - self.base_speed)
        return lo, hi

    def update(self, dt_scale=1.0):
        """Advance by dt_scale, spawn if due. Returns objects that just fell
        off the bottom."""
        self._frame_count += dt_scale
        self._frames_since_spawn += dt_scale

        if self._frames_since_spawn >= self._next_interval:
            self._spawn_one()
            self._frames_since_spawn = 0.0
            self._next_interval = self._current_interval()

            d = self.difficulty()
            if d > 0.4 and random.random() < 0.15 * d:
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
        ui = self.ui
        obj_type = pick_object_type(self.difficulty())
        margin = int(50 * ui)
        x = random.randint(margin, max(margin + 1, self.frame_w - margin))
        y = -40 * ui
        lo, hi = self._current_speed_range()
        vy = random.uniform(lo, hi) * obj_type.speed_multiplier * ui
        scale = random.uniform(0.9, 1.2) * ui
        spin = random.uniform(-3, 3)

        drift_amp = obj_type.drift_amp * random.uniform(0.7, 1.3) * ui if obj_type.drift_amp else 0.0
        drift_freq = obj_type.drift_freq * random.uniform(0.85, 1.15)

        self.objects.append(FallingObject(
            obj_type, x, y, vy, self.frame_w,
            scale=scale, spin=spin, drift_amp=drift_amp, drift_freq=drift_freq,
        ))

    def reset(self):
        self.objects = []
        self._frame_count = 0.0
        self._frames_since_spawn = 0.0
        self._next_interval = float(self.base_interval)