"""
games/catch/game.py

Main loop for the Catch game. Wires spawner.py (what's falling), paw.py
(where the hand(s) are, smoothed into stateful "paws"), and hud.py (what's
drawn on top) together with engine.tracking, and owns the one thing none
of those should: catch detection and score/miss state.

Contract with engine/menu.py (unchanged from the old catch.py stub):
    run_catch(cap, tracker) -> "menu" | "quit"
"""

import math
import random
import time

import cv2
import numpy as np

from engine.audio import play_sound
from engine.camera import show
from engine.tracking import get_palm_center

from .hud import draw_catch_flash, draw_game_over, draw_hud, draw_paw, spawn_particles, update_and_draw_particles
from .paw import PawTracker
from .spawner import Spawner

WINDOW_NAME = "HandArcade"

MAX_MISSES = 5
PALM_CATCH_RADIUS = 60
FLASH_FRAMES = 18

TARGET_DT = 1.0 / 30.0
MIN_DT_SCALE = 0.2
MAX_DT_SCALE = 3.0

SHAKE_DURATION = 8
SHAKE_MAGNITUDE = 14

SOUND_CATCH_GOOD = "assets/sounds/pop.wav"
SOUND_CATCH_BAD = "assets/sounds/hit.wav"

class _State:
    PLAYING = "playing"
    GAME_OVER = "game_over"

def _point_segment_distance(px, py, ax, ay, bx, by):
    """Shortest distance from point (px,py) to the segment (ax,ay)-(bx,by).

    This is what makes a catch feel like a real paw swat instead of a
    static hitbox: instead of only checking where a paw IS this frame, we
    check the whole path it just swept through, so a fast swipe catches
    things it passed over even if it never sat exactly on top of them on
    any single frame -- "catch it from everywhere" the swipe reaches,
    not just a fixed spot.
    """
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)

def run_catch(cap, tracker):
    print("Catch - press ESC to return to menu, 'q' to quit")

    success, first_frame = cap.read()
    if not success:
        print("Failed to read frame from webcam.")
        return "quit"
    frame_h, frame_w = first_frame.shape[:2]

    spawner = Spawner(frame_w, frame_h)
    paw_tracker = PawTracker(max_paws=2)

    score = 0
    misses = 0
    combo = 0
    state = _State.PLAYING
    flashes = []
    particles = []
    shake_frames = 0

    last_time = time.perf_counter()

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to read frame from webcam.")
            return "quit"

        now = time.perf_counter()
        dt_scale = (now - last_time) / TARGET_DT
        dt_scale = max(MIN_DT_SCALE, min(MAX_DT_SCALE, dt_scale))
        last_time = now

        frame = cv2.flip(frame, 1)
        results = tracker.process(frame)

        detections = []
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                px, py = get_palm_center(hand_landmarks, frame.shape)
                detections.append((px, py))

        paws = paw_tracker.update(detections, dt_scale)

        if state == _State.PLAYING:
            dropped = spawner.update(dt_scale)
            for obj in dropped:
                if not obj.obj_type.is_bad:
                    misses += 1
                    combo = 0

            for obj in spawner.objects:
                if obj.caught:
                    continue
                for paw in paws:
                    dist = _point_segment_distance(
                        obj.x, obj.y, paw.prev_x, paw.prev_y, paw.x, paw.y
                    )
                    if dist <= PALM_CATCH_RADIUS + obj.radius_px():
                        obj.caught = True
                        paw.register_catch()
                        score = max(0, score + obj.obj_type.points)

                        if obj.obj_type.is_bad:
                            combo = 0
                            misses += 1
                            play_sound(SOUND_CATCH_BAD)
                            particles.extend(spawn_particles(obj.x, obj.y, (0, 0, 220)))
                            shake_frames = SHAKE_DURATION
                        else:
                            combo += 1
                            play_sound(SOUND_CATCH_GOOD)
                            particles.extend(spawn_particles(obj.x, obj.y, obj.obj_type.color))

                        flashes.append([obj.x, obj.y, obj.obj_type.points, FLASH_FRAMES])
                        break

            spawner.objects = [o for o in spawner.objects if not o.caught]

            for obj in spawner.objects:
                obj.draw(frame)

            for flash in flashes:
                flash[3] -= 1
            flashes = [f for f in flashes if f[3] > 0]
            for flash in flashes:
                draw_catch_flash(frame, flash[0], flash[1], flash[2])

            particles = update_and_draw_particles(frame, particles)

            for paw in paws:
                draw_paw(frame, paw, PALM_CATCH_RADIUS)

            draw_hud(frame, score, misses, MAX_MISSES, combo)

            if misses >= MAX_MISSES:
                state = _State.GAME_OVER

        else:
            for obj in spawner.objects:
                obj.draw(frame)
            for paw in paws:
                draw_paw(frame, paw, PALM_CATCH_RADIUS)
            draw_game_over(frame, score)

        if shake_frames > 0:
            mag = int(SHAKE_MAGNITUDE * (shake_frames / SHAKE_DURATION))
            dx = random.randint(-mag, mag)
            dy = random.randint(-mag, mag)
            shake_matrix = np.float32([[1, 0, dx], [0, 1, dy]])
            frame = cv2.warpAffine(frame, shake_matrix, (frame_w, frame_h), borderMode=cv2.BORDER_REFLECT)
            shake_frames -= 1

        show(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            return "menu"
        if key == ord("q"):
            return "quit"
        if key == ord("r") and state == _State.GAME_OVER:
            score, misses, combo = 0, 0, 0
            spawner.reset()
            paw_tracker.reset()
            flashes = []
            particles = []
            shake_frames = 0
            state = _State.PLAYING