"""
games/fruit_slice/game.py

Main loop. This is the piece engine/menu.py actually calls.

Contract with engine/menu.py:
    run_fruit_slice(cap, tracker, difficulty="medium") is called with the
    already-open cv2.VideoCapture and HandTracker (opened once in the menu,
    shared across games), plus an optional difficulty string
    ("easy" / "medium" / "hard" — see difficulty.py).
    - Runs its own loop reading frames from `cap`.
    - Returns "quit" to exit the whole app.
    - Returns "menu" (or anything else) to go back to the menu screen.
"""

import math
import random
import time

import cv2

from engine.audio import play_sound
from engine.camera import show
from engine.tracking import get_fingertip_position

from .difficulty import DIFFICULTY_SETTINGS
from .hud import draw_game_over, draw_hud
from .spawner import next_spawn_interval, spawn_fruit

WINDOW_NAME = "HandArcade"

MAX_MISSES = 3
TRAIL_LEN = 6  # fingertip positions kept for swipe-through-slice detection

TARGET_FPS = 60
FRAME_BUDGET = 1.0 / TARGET_FPS
FPS_SAMPLE_COUNT = 30  # rolling average window so the FPS readout doesn't jitter

SOUND_SLICE = "assets/sounds/slice.wav"
SOUND_BOMB = "assets/sounds/hit.wav"

# slice particle burst
PARTICLE_LIFETIME = 0.4
PARTICLE_COUNT = 14
PARTICLE_GRAVITY = 500.0

# fingertip cursor (replaces the hand-skeleton overlay)
CURSOR_RADIUS = 12
CURSOR_COLOR_IDLE = (255, 255, 255)
CURSOR_COLOR_SLICE = (0, 255, 255)

# red flash punch when a bomb is sliced
FLASH_DURATION = 0.15


def run_fruit_slice(cap, tracker, difficulty="medium"):
    if difficulty not in DIFFICULTY_SETTINGS:
        difficulty = "medium"
    settings = DIFFICULTY_SETTINGS[difficulty]

    print(f"Fruit Slice ({difficulty}) - press ESC to return to menu, 'q' to quit")

    fruits = []
    particles = []
    score = 0
    misses = 0
    game_over = False
    flash_timer = 0.0

    start_time = time.time()
    last_frame_time = start_time
    next_spawn_time = start_time + 0.5

    trail = []  # recent fingertip pixel positions, most recent last
    fps_samples = []

    while True:
        loop_start = time.time()

        success, frame = cap.read()
        if not success:
            print("Failed to read frame from webcam.")
            return "quit"

        frame = cv2.flip(frame, 1)
        frame_h, frame_w = frame.shape[:2]

        now = time.time()
        dt = min(now - last_frame_time, 0.05)  # clamp in case of a stall/hiccup
        last_frame_time = now

        fps_samples.append(1.0 / dt if dt > 0 else TARGET_FPS)
        if len(fps_samples) > FPS_SAMPLE_COUNT:
            fps_samples.pop(0)
        avg_fps = sum(fps_samples) / len(fps_samples)

        results = tracker.process(frame)

        fingertip = None
        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            fingertip = get_fingertip_position(hand_landmarks, frame.shape)
            # hand skeleton overlay intentionally removed — see cursor draw below

        sliced_this_frame = False
        if not game_over:
            (fruits, particles, score, misses, game_over, trail, next_spawn_time,
             sliced_this_frame, bomb_hit_this_frame) = _advance_round(
                dt, now, start_time, frame_w, frame_h, fingertip, trail,
                fruits, particles, score, misses, next_spawn_time, settings,
            )
            if bomb_hit_this_frame:
                flash_timer = FLASH_DURATION

        _update_particles(particles, dt)

        for fruit in fruits:
            fruit.draw(frame)

        _draw_particles(frame, particles)

        # fingertip trail, faded (older points thinner/dimmer)
        if len(trail) >= 2:
            for i in range(1, len(trail)):
                alpha = i / len(trail)
                thickness = max(1, int(6 * alpha))
                cv2.line(frame, trail[i - 1], trail[i], (255, 255, 255), thickness)

        # fingertip cursor — replaces tracker.draw_landmarks
        if fingertip is not None:
            color = CURSOR_COLOR_SLICE if sliced_this_frame else CURSOR_COLOR_IDLE
            cv2.circle(frame, fingertip, CURSOR_RADIUS, color, -1)
            cv2.circle(frame, fingertip, CURSOR_RADIUS, (0, 0, 0), 2)

        # bomb-hit screen flash
        if flash_timer > 0:
            alpha = flash_timer / FLASH_DURATION
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (frame_w, frame_h), (0, 0, 255), -1)
            cv2.addWeighted(overlay, alpha * 0.5, frame, 1 - alpha * 0.5, 0, frame)
            flash_timer = max(0.0, flash_timer - dt)

        if game_over:
            draw_game_over(frame, score)
        else:
            draw_hud(frame, score, misses, MAX_MISSES, avg_fps, difficulty)

        show(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            return "quit"
        if game_over:
            if key != 255:  # any key press
                return "menu"
        elif key == 27:  # ESC
            return "menu"

        # cap the loop at TARGET_FPS so we're not burning CPU faster than needed
        elapsed_this_frame = time.time() - loop_start
        if elapsed_this_frame < FRAME_BUDGET:
            time.sleep(FRAME_BUDGET - elapsed_this_frame)


def _advance_round(dt, now, start_time, frame_w, frame_h, fingertip, trail,
                    fruits, particles, score, misses, next_spawn_time, settings):
    """One frame's worth of gameplay state update. Returns the updated state tuple."""

    # --- update fingertip trail ---------------------------------------------
    if fingertip is not None:
        trail.append(fingertip)
        if len(trail) > TRAIL_LEN:
            trail.pop(0)
    else:
        trail = []

    # --- spawn (rate + concurrent cap driven by difficulty settings) ----------
    if now >= next_spawn_time and len(fruits) < settings["max_simultaneous"]:
        fruits.append(spawn_fruit(frame_w, frame_h, settings))
        elapsed = now - start_time
        next_spawn_time = now + next_spawn_interval(elapsed, settings)

    sliced_this_frame = False
    bomb_hit_this_frame = False

    # --- physics + slice detection --------------------------------------------
    for fruit in fruits:
        fruit.update(dt)

        if fruit.sliced or not fruit.alive:
            continue

        hit = False
        if len(trail) >= 2:
            (px, py), (cx, cy) = trail[-2], trail[-1]
            if fruit.segment_intersects(px, py, cx, cy):
                hit = True
        elif fingertip is not None:
            if fruit.contains_point(*fingertip):
                hit = True

        if hit:
            fruit.slice()
            sliced_this_frame = True
            _spawn_particles(particles, (fruit.x, fruit.y), fruit.color)
            if fruit.is_bomb:
                misses += 1  # slicing a bomb costs one life, same as a missed fruit
                bomb_hit_this_frame = True
                play_sound(SOUND_BOMB)
            else:
                score += fruit.points
                play_sound(SOUND_SLICE)

        if fruit.offscreen_bottom_uncollected() and not fruit.is_bomb:
            fruit.alive = False  # falls off the bottom with no penalty

    fruits = [f for f in fruits if f.alive]

    game_over = misses >= MAX_MISSES
    return (fruits, particles, score, misses, game_over, trail, next_spawn_time,
            sliced_this_frame, bomb_hit_this_frame)


def _spawn_particles(particles, pos, color, count=PARTICLE_COUNT):
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(90, 260)
        particles.append({
            "x": pos[0], "y": pos[1],
            "vx": speed * math.cos(angle),
            "vy": speed * math.sin(angle),
            "life": PARTICLE_LIFETIME,
            "max_life": PARTICLE_LIFETIME,
            "color": color,
        })


def _update_particles(particles, dt):
    for p in particles:
        p["vy"] += PARTICLE_GRAVITY * dt
        p["x"] += p["vx"] * dt
        p["y"] += p["vy"] * dt
        p["life"] -= dt
    particles[:] = [p for p in particles if p["life"] > 0]


def _draw_particles(frame, particles):
    for p in particles:
        t = p["life"] / p["max_life"]
        radius = max(1, int(5 * t))
        cv2.circle(frame, (int(p["x"]), int(p["y"])), radius, p["color"], -1)