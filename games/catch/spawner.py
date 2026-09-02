"""
games/catch/spawner.py

Owns spawn timing and difficulty ramp. game.py calls update() once per
frame and gets back the objects that fell off-screen this frame (so it
can score misses) -- it does NOT silently delete them, because game.py
needs to know the difference between "still falling" and "just missed".
"""

import random

from .objects import FallingObject, pick_object_type


class Spawner:
    def __init__(self, frame_w, frame_h, base_interval_frames=45, min_interval_frames=14,
                 base_fall_speed=6.0, max_fall_speed=16.0, ramp_seconds=60, fps=30):
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.base_interval = base_interval_frames
        self.min_interval = min_interval_frames
        self.base_speed = base_fall_speed
        self.max_speed = max_fall_speed
        self.ramp_frames = ramp_seconds * fps

        self.objects = []
        self._frame_count = 0
        self._frames_since_spawn = 0
        self._next_interval = self.base_interval

    def _difficulty(self):
        """0.0 at start, 1.0 once ramp_frames have passed. Linear on purpose --
        it's the easiest curve to tune by feel. Swap for something like
        1 - (1-d)**2 later if you want it to bite harder early."""
        return min(1.0, self._frame_count / self.ramp_frames)

    def _current_interval(self):
        d = self._difficulty()
        return int(self.base_interval - d * (self.base_interval - self.min_interval))

    def _current_speed_range(self):
        d = self._difficulty()
        lo = self.base_speed + d * (self.max_speed - self.base_speed) * 0.4
        hi = self.base_speed + d * (self.max_speed - self.base_speed)
        return lo, hi

    def update(self):
        """Advance timers, spawn if due, move every object, and pull off any
        that just went past the bottom edge. Returns that dropped list."""
        self._frame_count += 1
        self._frames_since_spawn += 1

        if self._frames_since_spawn >= self._next_interval:
            self._spawn_one()
            self._frames_since_spawn = 0
            self._next_interval = self._current_interval()

        for obj in self.objects:
            obj.update()

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
        self.objects.append(FallingObject(obj_type, x, y, vy, scale=scale, spin=spin))

    def reset(self):
        self.objects = []
        self._frame_count = 0
        self._frames_since_spawn = 0
        self._next_interval = self.base_interval