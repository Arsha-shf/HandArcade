"""
games/fruit_slice/spawner.py

Decides when and where fruit are launched. Parameters come from
difficulty.get_difficulty(), which changes continuously over the round.

Launch design:
  - Bottom launches are aimed at a chosen APEX height (somewhere between the
    top and the middle of the screen), so fruit always peaks on screen at
    every resolution and speed. (Plain random velocities could send fruit
    off the top.)
  - A launch can be a burst of several fruit from the same edge.
  - At most one bomb per burst, and none in the first few seconds.
"""

import math
import random

from .fruit import GRAVITY, Fruit

BOMB_GRACE_SECONDS = 5.0
EDGE_MARGIN = 40          # px @720p outside the frame


def _pick_edge(edge_weights):
    edges = list(edge_weights.keys())
    weights = list(edge_weights.values())
    return random.choices(edges, weights=weights, k=1)[0]


def _launch(edge, frame_w, frame_h, ui, speed_mult):
    """Returns (x, y, vx, vy) for a launch from `edge`."""
    m = speed_mult * ui
    margin = EDGE_MARGIN * ui
    gravity = GRAVITY * ui * speed_mult * speed_mult

    if edge == "bottom":
        x = random.uniform(frame_w * 0.1, frame_w * 0.9)
        y = frame_h + margin
        apex_y = random.uniform(0.08, 0.50) * frame_h
        vy = -math.sqrt(2 * gravity * (y - apex_y))
        vx = random.uniform(-150, 150) * m

    elif edge == "top":
        x = random.uniform(frame_w * 0.1, frame_w * 0.9)
        y = -margin
        vx = random.uniform(-150, 150) * m
        vy = random.uniform(150, 350) * m

    elif edge == "left":
        x = -margin
        y = random.uniform(frame_h * 0.15, frame_h * 0.85)
        vx = random.uniform(500, 750) * m
        vy = random.uniform(-500, -200) * m

    else:  # right
        x = frame_w + margin
        y = random.uniform(frame_h * 0.15, frame_h * 0.85)
        vx = random.uniform(-750, -500) * m
        vy = random.uniform(-500, -200) * m

    return x, y, vx, vy


def spawn_burst(frame_w, frame_h, params, ui, elapsed, free_slots):
    """Launch 1..burst_max fruit (limited by free_slots). Returns a list."""
    if free_slots <= 0:
        return []

    edge = _pick_edge(params["edge_weights"])
    count = 1
    while count < params["burst_max"] and random.random() < params["burst_chance"]:
        count += 1
    count = min(count, free_slots)

    allow_bomb = elapsed >= BOMB_GRACE_SECONDS
    bomb_used = False
    fruits = []
    for _ in range(count):
        is_bomb = allow_bomb and not bomb_used and random.random() < params["bomb_chance"]
        bomb_used = bomb_used or is_bomb
        x, y, vx, vy = _launch(edge, frame_w, frame_h, ui, params["speed_mult"])
        fruits.append(Fruit(x, y, vx, vy, frame_w, frame_h, ui=ui,
                            speed_mult=params["speed_mult"], is_bomb=is_bomb))
    return fruits


def next_spawn_interval(params, burst_size=1):
    """Seconds until the next launch. Bigger bursts buy a longer breather, so
    the fruit-per-second rate stays close to what the preset intends."""
    base = params["spawn_interval"] * (0.6 + 0.4 * burst_size)
    return base * random.uniform(0.7, 1.3)