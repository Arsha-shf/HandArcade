"""
engine/smoothing.py

Exponential moving average for a single value (e.g. hand x-position).

    smoother = SmoothedValue(alpha=0.5)
    smooth_x = smoother.update(raw_x, dt_scale)

alpha is "how much of the new value to take per 30fps frame". dt_scale
(1.0 == one frame at 30fps) makes the smoothing behave the same at any
frame rate; without it, a 60fps camera would feel twice as snappy.

Lower alpha = smoother but laggier. Higher alpha = snappier but jittery.
"""


class SmoothedValue:
    __slots__ = ("alpha", "_value")

    def __init__(self, alpha=0.3):
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0.0, 1.0]")
        self.alpha = alpha
        self._value = None

    def update(self, new_value, dt_scale=1.0):
        if self._value is None:
            self._value = new_value
        else:
            a = 1.0 - (1.0 - self.alpha) ** max(0.0, dt_scale)
            self._value += (new_value - self._value) * a
        return self._value

    def reset(self):
        self._value = None