"""
games/catch/paw.py

Tracks each detected hand as a persistent "paw": a smoothed position,
a velocity/direction, and a small state machine (idle / swipe / catch)
that exists for two reasons:

  1. It's what makes catching feel like a real paw swat instead of a
     static hitbox -- game.py checks the path a paw just swept through,
     not just where it happens to be sitting this frame.
  2. It's the base for the paw animation. Once real paw art exists, it
     drives entirely off Paw.state / Paw.angle / Paw.catch_timer, which
     are already computed here every frame -- see draw_paw() in hud.py
     for exactly where the sprite swap happens.

PawTracker exists on top of that because mediapipe doesn't guarantee
multi_hand_landmarks stays in the same order between frames -- without
it, "paw 0" and "paw 1" would swap identities (and animation state)
randomly, which would look broken the moment there's a two-hand sprite.
It matches each frame's raw detections to the closest known paw instead
of trusting index order.
"""

import math

SMOOTHING = 0.55
SWIPE_SPEED_THRESHOLD = 9.0
CATCH_TTL = 10
MATCH_MAX_DIST = 220

class Paw:
    IDLE = "idle"
    SWIPE = "swipe"
    CATCH = "catch"

    def __init__(self, paw_id, x, y):
        self.id = paw_id
        self.x = float(x)
        self.y = float(y)
        self.prev_x = float(x)
        self.prev_y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.angle = 0.0
        self.state = Paw.IDLE
        self.catch_timer = 0
        self.missing_frames = 0

    def update(self, raw_x, raw_y, dt_scale=1.0):
        """raw_x/raw_y: this frame's tracked palm center. dt_scale: frame-rate
        normalizer (1.0 == one frame at the 30fps this was tuned against)."""
        self.prev_x, self.prev_y = self.x, self.y

        self.x += (raw_x - self.x) * SMOOTHING
        self.y += (raw_y - self.y) * SMOOTHING

        self.vx = (self.x - self.prev_x) / dt_scale
        self.vy = (self.y - self.prev_y) / dt_scale
        speed = math.hypot(self.vx, self.vy)

        if speed > 0.5:
            self.angle = math.degrees(math.atan2(self.vy, self.vx))

        if self.catch_timer > 0:
            self.catch_timer -= 1
            self.state = Paw.CATCH
        elif speed >= SWIPE_SPEED_THRESHOLD:
            self.state = Paw.SWIPE
        else:
            self.state = Paw.IDLE

        self.missing_frames = 0

    def register_catch(self):
        self.catch_timer = CATCH_TTL
        self.state = Paw.CATCH

    def speed(self):
        return math.hypot(self.vx, self.vy)

class PawTracker:
    """Keeps a small, stable set of Paw objects alive across frames so a
    paw's identity -- and therefore its animation state -- doesn't
    flicker when mediapipe reorders multi_hand_landmarks between frames.
    """

    def __init__(self, max_paws=2, hold_frames=6):
        self.max_paws = max_paws
        self.hold_frames = hold_frames
        self._paws = []
        self._next_id = 0

    def update(self, detections, dt_scale=1.0):
        """detections: list of (x, y) raw palm centers seen this frame.
        Returns the list of currently-active Paw objects (missing_frames == 0)."""
        unmatched = list(range(len(detections)))
        used_paws = set()

        for paw in self._paws:
            best_i, best_d = None, MATCH_MAX_DIST
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
            paw = Paw(self._next_id, x, y)
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