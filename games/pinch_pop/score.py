COMBO_WINDOW = 1.2
MAX_MULTIPLIER = 5
MULTIPLIER_STEP = 2


class Score:
    def __init__(self):
        self.total = 0
        self.combo = 0
        self.best_combo = 0
        self.pops = 0
        self.bombs_hit = 0
        self._last_pop_time = None

    def is_combo_active(self, now):
        return self._last_pop_time is not None and (now - self._last_pop_time) <= COMBO_WINDOW

    def current_multiplier(self):
        if self.combo <= 0:
            return 1
        return min(MAX_MULTIPLIER, 1 + (self.combo - 1) // MULTIPLIER_STEP)

    def register_pop(self, points, kind, now):
        """
        Apply the result of popping a bubble. Returns (points_gained, multiplier)
        so the caller can build a matching "+N x M" popup.
        """
        if kind == "bomb":
            self.combo = 0
            self.bombs_hit += 1
            self.total = max(0, self.total + points)  # points is negative for bombs
            self._last_pop_time = now
            return points, 1

        if self.is_combo_active(now):
            self.combo += 1
        else:
            self.combo = 1
        self.best_combo = max(self.best_combo, self.combo)

        multiplier = self.current_multiplier()
        gained = points * multiplier
        self.total += gained
        self.pops += 1
        self._last_pop_time = now
        return gained, multiplier