"""
games/catch/paw.py

Tracks each detected hand as a persistent "paw": a smoothed position,
a velocity/direction, and a small state machine (idle / swipe / catch).

  1. game.py checks the PATH a paw just swept through, not just where it
     sits this frame, so fast swipes catch things they passed over.
  2. It drives the paw animation (see draw_paw() in hud.py).

PawTracker matches each frame's raw detections to the closest known paw,
because mediapipe doesn't keep hand order stable between frames.

Speeds/distances are in px per 30fps-frame for a 720px-tall frame and are
multiplied by `ui` (engine.layout.ui_scale). Smoothing and timers use
dt_scale so they behave the same at 30 and 60 fps.
"""

import math

SMOOTHING = 0.55
SWIPE_SPEED_THRESHOLD = 9.0
CATCH_TTL = 10          # in 30fps-frames
MATCH_MAX_DIST = 220


class Paw:
    IDLE = "idle"
    SWIPE = "swipe"
    CATCH = "catch"

    def __init__(self, paw_id, x, y, ui=1.0):
        self.id = paw_id
        self.ui = ui
        self.x = float(x)
        self.y = float(y)
        self.prev_x = float(x)
        self.prev_y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.angle = 0.0
        self.state = Paw.IDLE
        self.catch_timer = 0.0
        self.missing_frames = 0

    def update(self, raw_x, raw_y, dt_scale=1.0):
        """raw_x/raw_y: this frame's palm center. dt_scale: 1.0 == one 30fps frame."""
        self.prev_x, self.prev_y = self.x, self.y

        alpha = 1.0 - (1.0 - SMOOTHING) ** dt_scale
        self.x += (raw_x - self.x) * alpha
        self.y += (raw_y - self.y) * alpha

        # velocity in px per 30fps-frame, independent of the real frame rate
        self.vx = (self.x - self.prev_x) / dt_scale
        self.vy = (self.y - self.prev_y) / dt_scale
        speed = math.hypot(self.vx, self.vy)

        if speed > 0.5 * self.ui:
            self.angle = math.degrees(math.atan2(self.vy, self.vx))

        if self.catch_timer > 0:
            self.catch_timer = max(0.0, self.catch_timer - dt_scale)
            self.state = Paw.CATCH
        elif speed >= SWIPE_SPEED_THRESHOLD * self.ui:
            self.state = Paw.SWIPE
        else:
            self.state = Paw.IDLE

        self.missing_frames = 0

    def register_catch(self):
        self.catch_timer = float(CATCH_TTL)
        self.state = Paw.CATCH

    def speed(self):
        return math.hypot(self.vx, self.vy)


class PawTracker:
    """Keeps a small, stable set of Paw objects alive across frames."""

    def __init__(self, max_paws=2, hold_frames=6, ui=1.0):
        self.max_paws = max_paws
        self.hold_frames = hold_frames
        self.ui = ui
        self._paws = []
        self._next_id = 0

    def update(self, detections, dt_scale=1.0):
        """detections: list of (x, y) raw palm centers seen this frame.
        Returns the currently-active Paw objects."""
        unmatched = list(range(len(detections)))
        used_paws = set()
        max_dist = MATCH_MAX_DIST * self.ui

        for paw in self._paws:
            best_i, best_d = None, max_dist
            for i in unmatched:
                d = math.hypot(detections[i][0] - paw.x, detections[i][1] - paw.y)
                if d < best_d:
                    best_i, best_d = i, d
            if best_i is not None:
                paw.update(*detections[best_i], dt_scale=dt_scale)
                unmatched.remove(best_i)
                used_paws.add(id(paw))

        for i in unmatched:
            if len(self._paws) >= self.max_paws:
                break
            x, y = detections[i]
            paw = Paw(self._next_id, x, y, self.ui)
            self._next_id += 1
            self._paws.append(paw)
            used_paws.add(id(paw))

        alive = []
        for paw in self._paws:
            if id(paw) not in used_paws:
                paw.missing_frames += 1
                if paw.missing_frames <= self.hold_frames:
                    alive.append(paw)
            else:
                alive.append(paw)
        self._paws = alive

        return [p for p in self._paws if p.missing_frames == 0]

    def reset(self):
        self._paws = []
        self._next_id = 0