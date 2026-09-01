"""
games/dodge/dodge.py

Main loop. Contract with engine/menu.py:
    run_dodge(cap, tracker) is called with the already-open cv2.VideoCapture
    and HandTracker (opened once in the menu, shared across games).
    - Runs its own loop reading frames from `cap`.
    - Returns "quit" to exit the whole app.
    - Returns "menu" to go back to the menu screen.

This file only owns state + control flow. Player/obstacle/collision/HUD
logic each live in their own module -- see player.py, obstacles.py,
collision.py, difficulty.py, hud.py.
"""

import cv2

from .config import WINDOW_NAME
from .player import make_player_state, update_player, draw_player
from .obstacles import spawn_obstacle, update_obstacles, draw_obstacle
from .collision import check_collision
from .difficulty import get_difficulty
from .hud import draw_hud, draw_game_over, pick_game_over_line


def run_dodge(cap, tracker):
    print("Dodge - press ESC to return to menu, 'q' to quit")

    success, first_frame = cap.read()
    if not success:
        print("Failed to read frame from webcam.")
        return "quit"
    frame_h, frame_w = first_frame.shape[:2]

    player = make_player_state(frame_w, frame_h)
    obstacles = []
    frame_count = 0
    frames_since_spawn = 0
    score = 0
    dodged_total = 0
    alive = True
    game_over_message = ""

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to read frame from webcam.")
            return "quit"

        frame = cv2.flip(frame, 1)
        results = tracker.process(frame)

        if alive:
            frame_count += 1
            update_player(player, results, frame_w, frame_h)

            spawn_interval, speed = get_difficulty(frame_count)
            frames_since_spawn += 1
            if frames_since_spawn >= spawn_interval:
                obstacles.append(spawn_obstacle(frame_w, speed))
                frames_since_spawn = 0

            dodged_total += update_obstacles(obstacles, frame_h)
            score = frame_count // 3 + dodged_total * 10  # survival time + dodge bonus

            if check_collision(player, obstacles):
                alive = False
                game_over_message = pick_game_over_line()

        for obs in obstacles:
            draw_obstacle(frame, obs)
        draw_player(frame, player)
        draw_hud(frame, score, dodged_total, frame_count)

        if not alive:
            draw_game_over(frame, score, game_over_message)

        cv2.imshow(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            return "menu"
        if key == ord("q"):
            return "quit"
        if key == ord(" ") and not alive:
            # Retry: reset everything and keep playing
            player = make_player_state(frame_w, frame_h)
            obstacles = []
            frame_count = 0
            frames_since_spawn = 0
            score = 0
            dodged_total = 0
            alive = True