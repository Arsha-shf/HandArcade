COMBO_WINDOW = 1.2
MAX_MULTIPLIER = 5
MULTIPLIER_STEP = 2


def multiplier_for(combo):
    """Score multiplier for a combo of this length."""
    if combo <= 0:
        return 1
    return min(MAX_MULTIPLIER, 1 + (combo - 1) // MULTIPLIER_STEP)


class Score:
    def __init__(self):
        self.total = 0
        self.combo = 0
        self.best_combo = 0
        self.pops = 0
        self.bombs_hit = 0
        self._last_pop_time = None

    def combo_time_left(self, now):
        """Seconds until the current combo expires (0 if there is none)."""
        if self.combo <= 0 or self._last_pop_time is None:
            return 0.0
        return max(0.0, COMBO_WINDOW - (now - self._last_pop_time))

    def is_combo_active(self, now):
        return self.combo_time_left(now) > 0

    def current_multiplier(self):
        return multiplier_for(self.combo)

    def best_multiplier(self):
        """Multiplier reached by the best combo of the round (not the current one)."""
        return multiplier_for(self.best_combo)

    def register_pop(self, points, kind, now):
        if kind == "bomb":
            self.combo = 0
            self.bombs_hit += 1
            self.total = max(0, self.total + points)
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