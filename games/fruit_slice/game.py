"""
games/fruit_slice/game.py

Main loop. This is the piece engine/menu.py actually calls.

Contract with engine/menu.py:
    run_fruit_slice(cap, tracker) is called with the already-open cv2.VideoCapture
    and HandTracker (opened once in the menu, shared across games).
    - Runs its own loop reading frames from `cap`.
    - Returns "quit" to exit the whole app.
    - Returns "menu" (or anything else) to go back to the menu screen.
"""

import time

import cv2

from engine.camera import show
from engine.tracking import get_fingertip_position

from .hud import draw_game_over, draw_hud
from .spawner import next_spawn_interval, spawn_fruit

WINDOW_NAME = "HandArcade"

MAX_MISSES = 3
TRAIL_LEN = 6  # fingertip positions kept for swipe-through-slice detection


def run_fruit_slice(cap, tracker):
    print("Fruit Slice - press ESC to return to menu, 'q' to quit")

    fruits = []
    score = 0
    misses = 0
    game_over = False

    start_time = time.time()
    last_frame_time = start_time
    next_spawn_time = start_time + 0.5

    trail = []  # recent fingertip pixel positions, most recent last

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to read frame from webcam.")
            return "quit"

        frame = cv2.flip(frame, 1)
        frame_h, frame_w = frame.shape[:2]

        now = time.time()
        dt = min(now - last_frame_time, 0.05)  # clamp in case of a stall/hiccup
        last_frame_time = now

        results = tracker.process(frame)

        fingertip = None
        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            fingertip = get_fingertip_position(hand_landmarks, frame.shape)
            tracker.draw_landmarks(frame, hand_landmarks)

        if not game_over:
            fruits, score, misses, game_over, trail, next_spawn_time = _advance_round(
                dt, now, start_time, frame_w, frame_h, fingertip, trail,
                fruits, score, misses, next_spawn_time,
            )

        for fruit in fruits:
            fruit.draw(frame)

        if len(trail) >= 2:
            for i in range(1, len(trail)):
                cv2.line(frame, trail[i - 1], trail[i], (255, 255, 255), 3)

        if game_over:
            draw_game_over(frame, score)
        else:
            draw_hud(frame, score, misses, MAX_MISSES)

        show(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            return "quit"
        if game_over:
            if key != 255:  # any key press
                return "menu"
        elif key == 27:  # ESC
            return "menu"


def _advance_round(dt, now, start_time, frame_w, frame_h, fingertip, trail,
                    fruits, score, misses, next_spawn_time):
    """One frame's worth of gameplay state update. Returns the updated state tuple."""

    # --- update fingertip trail ---------------------------------------------
    if fingertip is not None:
        trail.append(fingertip)
        if len(trail) > TRAIL_LEN:
            trail.pop(0)
    else:
        trail = []

    # --- spawn ----------------------------------------------------------------
    if now >= next_spawn_time:
        fruits.append(spawn_fruit(frame_w, frame_h))
        elapsed = now - start_time
        next_spawn_time = now + next_spawn_interval(elapsed)

    # --- physics + slice detection --------------------------------------------
    for fruit in fruits:
        fruit.update(dt)

        if fruit.sliced or not fruit.alive:
            continue

        sliced_this_frame = False
        if len(trail) >= 2:
            (px, py), (cx, cy) = trail[-2], trail[-1]
            if fruit.segment_intersects(px, py, cx, cy):
                sliced_this_frame = True
        elif fingertip is not None:
            if fruit.contains_point(*fingertip):
                sliced_this_frame = True

        if sliced_this_frame:
            fruit.slice()
            if fruit.is_bomb:
                misses += 1  # slicing a bomb costs one life, same as a missed fruit
            else:
                score += fruit.points

        if fruit.offscreen_bottom_uncollected() and not fruit.is_bomb:
            fruit.alive = False  # falls off the bottom with no penalty

    fruits = [f for f in fruits if f.alive]

    game_over = misses >= MAX_MISSES
    return fruits, score, misses, game_over, trail, next_spawn_time