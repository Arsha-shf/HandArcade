"""
games/catch/game.py

Main loop for the Catch game. Wires spawner.py (what's falling), paw.py
(where the hand(s) are), and hud.py (what's drawn on top) together with
engine.tracking, and owns catch detection and score/miss state.

Contract with engine/menu.py:
    run_catch(cap, tracker) -> "menu" | "quit"
"""

import math
import random
import time

import cv2
import numpy as np

from engine import highscores
from engine import hud as engine_hud
from engine.audio import play_sound
from engine.camera import show, to_tracking_frame
from engine.layout import ui_scale
from engine.tracking import get_palm_center

from .hud import (
    draw_game_over,
    draw_hud,
    draw_paw,
    draw_popup,
    spawn_particles,
    update_and_draw_particles,
)
from .paw import PawTracker
from .spawner import Spawner

WINDOW_NAME = "HandArcade"
HIGHSCORE_KEY = "catch"

MAX_MISSES = 5
HEAL_EVERY = 10              # every N catches in a row heals one miss
PALM_CATCH_RADIUS = 60       # px at 720p; scaled by ui
POPUP_FRAMES = 18            # in 30fps-frames

TARGET_DT = 1.0 / 30.0
MIN_DT_SCALE = 0.2
MAX_DT_SCALE = 3.0

SHAKE_DURATION = 8           # in 30fps-frames
SHAKE_MAGNITUDE = 14

GAME_OVER_ANIM_DURATION = 0.5

SOUND_CATCH_GOOD = "assets/sounds/pop.wav"
SOUND_CATCH_BAD = "assets/sounds/hit.wav"

GAME_OVER_LINES = [
    "Butterfingers.",
    "The floor says thanks.",
    "Gravity wins again.",
    "Your hands had one job.",
    "Almost. Not really.",
]

COLOR_GOOD = (0, 220, 0)
COLOR_BAD = (0, 0, 255)
COLOR_HEAL = (120, 255, 120)


class _State:
    PLAYING = "playing"
    GAME_OVER = "game_over"


def _point_segment_distance(px, py, ax, ay, bx, by):
    """Shortest distance from point to the segment (a)-(b). Used so a fast
    swipe catches things along the whole path it just swept, not only where
    the paw sits on this single frame."""
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def run_catch(cap, tracker):
    print("Catch - press ESC to return to menu, 'q' to quit")

    success, first_frame = cap.read()
    if not success:
        print("Failed to read frame from webcam.")
        return "quit"
    frame_h, frame_w = first_frame.shape[:2]
    ui = ui_scale(frame_h)
    catch_radius = PALM_CATCH_RADIUS * ui

    spawner = Spawner(frame_w, frame_h, ui=ui)
    paw_tracker = PawTracker(max_paws=2, ui=ui)

    score = 0
    misses = 0
    combo = 0
    best = highscores.get_best(HIGHSCORE_KEY)
    state = _State.PLAYING
    game_over_start = None
    game_over_message = ""
    game_over_extra = None
    popups = []        # [x, y, text, color, ttl]
    particles = []
    shake_frames = 0.0

    engine_hud.reset_score_animation()
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
        results = tracker.process(to_tracking_frame(frame))

        detections = []
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                detections.append(get_palm_center(hand_landmarks, frame.shape))

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
                    if dist <= catch_radius + obj.radius_px():
                        obj.caught = True
                        paw.register_catch()
                        points = obj.obj_type.points
                        score = max(0, score + points)

                        if obj.obj_type.is_bad:
                            combo = 0
                            misses += 1
                            play_sound(SOUND_CATCH_BAD)
                            particles.extend(spawn_particles(obj.x, obj.y, (0, 0, 220), ui))
                            shake_frames = SHAKE_DURATION
                        else:
                            combo += 1
                            play_sound(SOUND_CATCH_GOOD)
                            particles.extend(spawn_particles(obj.x, obj.y, obj.obj_type.color, ui))
                            if combo % HEAL_EVERY == 0 and misses > 0:
                                misses -= 1
                                popups.append([obj.x, obj.y - 45 * ui, "MISS HEALED",
                                               COLOR_HEAL, POPUP_FRAMES * 1.6])

                        text = f"+{points}" if points > 0 else str(points)
                        popups.append([obj.x, obj.y, text,
                                       COLOR_GOOD if points > 0 else COLOR_BAD, POPUP_FRAMES])
                        break

            spawner.objects = [o for o in spawner.objects if not o.caught]

            for obj in spawner.objects:
                obj.draw(frame)

            for popup in popups:
                popup[4] -= dt_scale
            popups = [p for p in popups if p[4] > 0]
            for x, y, text, color, ttl in popups:
                draw_popup(frame, x, y, text, color, min(1.0, ttl / POPUP_FRAMES), ui)

            particles = update_and_draw_particles(frame, particles, dt_scale, ui)

            for paw in paws:
                draw_paw(frame, paw, catch_radius, ui)

            draw_hud(frame, score, misses, MAX_MISSES, combo, max(best, score))

            if misses >= MAX_MISSES:
                state = _State.GAME_OVER
                game_over_start = time.perf_counter()
                game_over_message = random.choice(GAME_OVER_LINES)
                if highscores.submit(HIGHSCORE_KEY, score):
                    best = score
                    game_over_extra = "NEW BEST!"
                else:
                    game_over_extra = f"Best: {best}"

        else:
            for obj in spawner.objects:
                obj.draw(frame)
            for paw in paws:
                draw_paw(frame, paw, catch_radius, ui)
            elapsed = time.perf_counter() - game_over_start
            progress = min(1.0, elapsed / GAME_OVER_ANIM_DURATION)
            draw_game_over(frame, score, game_over_message, progress, game_over_extra)

        if shake_frames > 0:
            mag = int(SHAKE_MAGNITUDE * ui * (shake_frames / SHAKE_DURATION))
            dx = random.randint(-mag, mag)
            dy = random.randint(-mag, mag)
            shake_matrix = np.float32([[1, 0, dx], [0, 1, dy]])
            frame = cv2.warpAffine(frame, shake_matrix, (frame_w, frame_h),
                                   borderMode=cv2.BORDER_REFLECT)
            shake_frames = max(0.0, shake_frames - dt_scale)

        show(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            return "menu"
        if key == ord("q"):
            return "quit"
        if key in (ord(" "), ord("r")) and state == _State.GAME_OVER:
            score, misses, combo = 0, 0, 0
            spawner.reset()
            paw_tracker.reset()
            popups = []
            particles = []
            shake_frames = 0.0
            state = _State.PLAYING
            game_over_start = None
            engine_hud.reset_score_animation()
            last_time = time.perf_counter()