"""
Gameplay "feel" helpers that sit alongside the core bubble/score logic:
input smoothing so pinch tracking doesn't feel jittery, a screen-shake
effect for satisfying bomb hits, a periodic "Bubble Frenzy" event for
pacing variety, and a one-charge shield power-up.
"""

import random

class HandSmoother:
    def __init__(self, alpha=0.55):
        self.alpha = alpha
        self._smoothed = {}

    def smooth(self, hand_id, point):
        prev = self._smoothed.get(hand_id)
        if prev is None:
            self._smoothed[hand_id] = (float(point[0]), float(point[1]))
            return point

        sx = prev[0] + (point[0] - prev[0]) * self.alpha
        sy = prev[1] + (point[1] - prev[1]) * self.alpha
        self._smoothed[hand_id] = (sx, sy)
        return (int(sx), int(sy))

    def forget_missing(self, seen_ids):
        for hand_id in list(self._smoothed):
            if hand_id not in seen_ids:
                del self._smoothed[hand_id]

    def reset(self):
        self._smoothed.clear()


class HandTracker:
    def __init__(self, max_distance=160.0, max_missed_seconds=0.6):
        self.max_distance = max_distance
        self.max_missed_seconds = max_missed_seconds
        self._tracks = {}
        self._next_id = 0

    def update(self, detections, dt):
        for track in self._tracks.values():
            track["missed_for"] += dt

        unmatched_tracks = set(self._tracks.keys())
        candidates = []
        for det_i, det in enumerate(detections):
            dx0, dy0 = det["point"]
            for track_id in unmatched_tracks:
                tx, ty = self._tracks[track_id]["point"]
                dist = ((dx0 - tx) ** 2 + (dy0 - ty) ** 2) ** 0.5
                if dist <= self.max_distance:
                    candidates.append((dist, det_i, track_id))
        candidates.sort(key=lambda c: c[0])

        assignments = {}
        matched_dets = set()
        for dist, det_i, track_id in candidates:
            if det_i in matched_dets or track_id not in unmatched_tracks:
                continue
            assignments[det_i] = track_id
            matched_dets.add(det_i)
            unmatched_tracks.discard(track_id)

        for det_i, det in enumerate(detections):
            track_id = assignments.get(det_i)
            if track_id is None:
                track_id = f"hand_{self._next_id}"
                self._next_id += 1
            self._tracks[track_id] = {"point": det["point"], "missed_for": 0.0}
            det["id"] = track_id

        stale = [
            track_id for track_id, track in self._tracks.items()
            if track["missed_for"] > self.max_missed_seconds
        ]
        for track_id in stale:
            del self._tracks[track_id]

        return detections

    def reset(self):
        self._tracks.clear()
        self._next_id = 0


class PinchTracker: 
    def __init__(self, enter_threshold=0.055, exit_threshold=0.075):
        self.enter_threshold = enter_threshold
        self.exit_threshold = exit_threshold
        self._state = {}

    def update(self, hand_id, distance):
        was_pinched = self._state.get(hand_id, False)
        threshold = self.exit_threshold if was_pinched else self.enter_threshold
        is_pinched = distance < threshold
        self._state[hand_id] = is_pinched
        return is_pinched

    def forget_missing(self, seen_ids):
        for hand_id in list(self._state):
            if hand_id not in seen_ids:
                del self._state[hand_id]

    def reset(self):
        self._state.clear()


class ScreenShake:
    def __init__(self, decay_per_second=2.5, max_pixels=16):
        self.trauma = 0.0
        self.decay_per_second = decay_per_second
        self.max_pixels = max_pixels

    def trigger(self, amount):
        self.trauma = min(1.0, self.trauma + amount)

    def update(self, dt):
        if self.trauma > 0:
            self.trauma = max(0.0, self.trauma - dt * self.decay_per_second)

    def offset(self):
        if self.trauma <= 0:
            return 0, 0
        power = self.trauma * self.trauma
        dx = random.uniform(-1, 1) * self.max_pixels * power
        dy = random.uniform(-1, 1) * self.max_pixels * power
        return int(dx), int(dy)


class FrenzyManager:
    def __init__(self, interval=18.0, duration=5.0, spawn_boost=2.2, score_multiplier=2):
        self.interval = interval
        self.duration = duration
        self.spawn_boost = spawn_boost
        self.score_multiplier = score_multiplier
        self.time_until_next = interval
        self.time_remaining = 0.0
        self.just_started = False
        self.just_ended = False

    def update(self, dt):
        self.just_started = False
        self.just_ended = False
        if self.time_remaining > 0:
            self.time_remaining -= dt
            if self.time_remaining <= 0:
                self.time_remaining = 0.0
                self.time_until_next = self.interval
                self.just_ended = True
        else:
            self.time_until_next -= dt
            if self.time_until_next <= 0:
                self.time_remaining = self.duration
                self.just_started = True

    @property
    def is_active(self):
        return self.time_remaining > 0

    def spawn_rate_multiplier(self):
        return self.spawn_boost if self.is_active else 1.0

    def reset(self):
        self.time_until_next = self.interval
        self.time_remaining = 0.0
        self.just_started = False
        self.just_ended = False


class ShieldStatus:
    def __init__(self, max_charges=1):
        self.max_charges = max_charges
        self.charges = 0

    def grant(self):
        self.charges = min(self.max_charges, self.charges + 1)

    def has_charge(self):
        return self.charges > 0

    def consume(self):
        if self.charges > 0:
            self.charges -= 1
            return True
        return False

    def reset(self):
        self.charges = 0