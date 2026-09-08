import cv2

from engine.audio import play_sound
from engine.camera import show

from .collision import check_collision
from .config import WINDOW_NAME
from .difficulty import get_difficulty
from .hud import (
    draw_difficulty_select,
    draw_game_over,
    draw_hud,
    draw_swarm_warning,
    pick_game_over_line,
)
from .obstacles import draw_obstacle, spawn_obstacle, update_obstacles
from .player import draw_player, make_player_state, update_player

SOUND_HIT = "assets/sounds/hit.wav"

DIFFICULTY_KEYS = {
    ord("1"): "easy",
    ord("2"): "mid",
    ord("3"): "hard",
}

SWARM_WARNING_FRAMES = 20


def _select_difficulty(cap):
    while True:
        success, frame = cap.read()
        if not success:
            return None
        frame = cv2.flip(frame, 1)
        draw_difficulty_select(frame)
        show(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key in DIFFICULTY_KEYS:
            return DIFFICULTY_KEYS[key]
        if key == 27:
            return "menu"
        if key == ord("q"):
            return "quit"


def run_dodge(cap, tracker):
    print("Dodge - press ESC to return to menu, 'q' to quit")

    difficulty = _select_difficulty(cap)
    if difficulty in ("menu", "quit", None):
        return difficulty or "quit"

    success, first_frame = cap.read()
    if not success:
        print("Failed to read frame from webcam.")
        return "quit"
    frame_h, frame_w = first_frame.shape[:2]

    player = make_player_state(frame_w, frame_h)
    obstacles = []
    frame_count = 0
    frames_since_spawn = 0
    frames_since_swarm = 0
    swarm_flash = 0
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

            diff = get_difficulty(frame_count, difficulty)

            frames_since_spawn += 1
            if frames_since_spawn >= diff["spawn_interval"]:
                obstacles.append(spawn_obstacle(
                    frame_w, frame_h, diff["speed"],
                    homing_chance=diff["homing_chance"],
                    turn_rate=diff["turn_rate"],
                ))
                frames_since_spawn = 0

            if diff["swarm_interval_frames"] > 0:
                frames_since_swarm += 1
                if frames_since_swarm >= diff["swarm_interval_frames"]:
                    for _ in range(diff["swarm_size"]):
                        obstacles.append(spawn_obstacle(
                            frame_w, frame_h, diff["speed"] * 1.15,
                            turn_rate=diff["turn_rate"],
                            force_homing=True,
                        ))
                    frames_since_swarm = 0
                    swarm_flash = SWARM_WARNING_FRAMES

            dodged_total += update_obstacles(obstacles, frame_w, frame_h, player["x"], player["y"])
            score = frame_count // 3 + dodged_total * 10

            if check_collision(player, obstacles):
                alive = False
                game_over_message = pick_game_over_line(difficulty)
                play_sound(SOUND_HIT)

        for obs in obstacles:
            draw_obstacle(frame, obs)
        draw_player(frame, player)
        draw_hud(frame, score, dodged_total, frame_count, difficulty)

        if swarm_flash > 0:
            draw_swarm_warning(frame)
            swarm_flash -= 1

        if not alive:
            draw_game_over(frame, score, game_over_message)

        show(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            return "menu"
        if key == ord("q"):
            return "quit"
        if key == ord(" ") and not alive:
            player = make_player_state(frame_w, frame_h)
            obstacles = []
            frame_count = 0
            frames_since_spawn = 0
            frames_since_swarm = 0
            swarm_flash = 0
            score = 0
            dodged_total = 0
            alive = True
        if key == ord("d") and not alive:
            new_difficulty = _select_difficulty(cap)
            if new_difficulty in ("menu", "quit", None):
                return new_difficulty or "quit"
            difficulty = new_difficulty