"""
games/catch/game.py

Main loop for the Catch game. Wires spawner.py (what's falling) and
hud.py (what's drawn on top) together with engine.tracking (where the
hand is), and owns the one thing neither of those should: catch
detection and score/miss state.

Contract with engine/menu.py (unchanged from the old catch.py stub):
    run_catch(cap, tracker) -> "menu" | "quit"
"""

import math

import cv2

from engine.tracking import get_palm_center

from .hud import draw_catch_flash, draw_game_over, draw_hud
from .spawner import Spawner

WINDOW_NAME = "HandArcade"

MAX_MISSES = 5
PALM_CATCH_RADIUS = 55     # px. The hand's effective "paw" -- tune per camera FOV/resolution
FLASH_FRAMES = 18          # how long a "+N" popup lingers, in frames


class _State:
    PLAYING = "playing"
    GAME_OVER = "game_over"


def run_catch(cap, tracker):
    print("Catch - press ESC to return to menu, 'q' to quit")

    success, first_frame = cap.read()
    if not success:
        print("Failed to read frame from webcam.")
        return "quit"
    frame_h, frame_w = first_frame.shape[:2]

    spawner = Spawner(frame_w, frame_h)
    score = 0
    misses = 0
    combo = 0
    state = _State.PLAYING
    flashes = []  # each entry: [x, y, points, ttl]

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to read frame from webcam.")
            return "quit"

        frame = cv2.flip(frame, 1)
        results = tracker.process(frame)

        palm_points = []
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                px, py = get_palm_center(hand_landmarks, frame.shape)
                palm_points.append((px, py))
                # Draw the actual catch hitbox so the player can see exactly
                # what counts as a "paw" -- this is the cat-catching feel:
                # the circle is the claw range, not just a dot.
                cv2.circle(frame, (px, py), PALM_CATCH_RADIUS, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.circle(frame, (px, py), 6, (255, 255, 255), -1, cv2.LINE_AA)

        if state == _State.PLAYING:
            # 1. advance the world, collect anything that just fell off the bottom
            dropped = spawner.update()
            for obj in dropped:
                if not obj.obj_type.is_bad:
                    # a missed bomb costs nothing -- you're not punished for
                    # letting a bomb fall past you, only for catching one
                    misses += 1
                    combo = 0

            # 2. catch detection against everything still on screen
            for obj in spawner.objects:
                if obj.caught:
                    continue
                for (px, py) in palm_points:
                    dist = math.hypot(obj.x - px, obj.y - py)
                    if dist <= PALM_CATCH_RADIUS + obj.radius_px():
                        obj.caught = True
                        score = max(0, score + obj.obj_type.points)
                        if obj.obj_type.is_bad:
                            combo = 0
                            misses += 1  # catching a bomb counts as a miss
                        else:
                            combo += 1
                        flashes.append([obj.x, obj.y, obj.obj_type.points, FLASH_FRAMES])
                        break

            spawner.objects = [o for o in spawner.objects if not o.caught]

            # 3. draw
            for obj in spawner.objects:
                obj.draw(frame)

            for flash in flashes:
                flash[3] -= 1
            flashes = [f for f in flashes if f[3] > 0]
            for flash in flashes:
                draw_catch_flash(frame, flash[0], flash[1], flash[2])

            draw_hud(frame, score, misses, MAX_MISSES, combo)

            if misses >= MAX_MISSES:
                state = _State.GAME_OVER

        else:  # GAME_OVER -- freeze the falling objects where they are, just render
            for obj in spawner.objects:
                obj.draw(frame)
            draw_game_over(frame, score)

        cv2.imshow(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            return "menu"
        if key == ord("q"):
            return "quit"
        if key == ord("r") and state == _State.GAME_OVER:
            score, misses, combo = 0, 0, 0
            spawner.reset()
            flashes = []
            state = _State.PLAYING