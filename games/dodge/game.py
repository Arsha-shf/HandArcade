import time

import cv2

from engine import highscores
from engine import hud as engine_hud
from engine.audio import play_sound
from engine.camera import show, to_tracking_frame
from engine.layout import ui_scale

from .collision import check_collision
from .config import (
    GRACE_SECONDS,
    HAND_LOST_PAUSE_SECONDS,
    SWARM_WARNING_SECONDS,
    WINDOW_NAME,
)
from .difficulty import get_difficulty
from .hud import (
    draw_depth_gauge,
    draw_difficulty_select,
    draw_game_over,
    draw_hud,
    draw_status,
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

GAME_OVER_ANIM_DURATION = 0.5
MAX_DT = 0.05   # a hiccup longer than this is treated as 50ms (no teleporting obstacles)


def _best_key(level):
    return f"dodge_{level}"


def _all_bests():
    return {lvl: highscores.get_best(_best_key(lvl)) for lvl in ("easy", "mid", "hard")}


def _select_difficulty(cap):
    bests = _all_bests()
    while True:
        success, frame = cap.read()
        if not success:
            return None
        frame = cv2.flip(frame, 1)
        draw_difficulty_select(frame, bests)
        show(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key in DIFFICULTY_KEYS:
            return DIFFICULTY_KEYS[key]
        if key == 27:
            return "menu"
        if key == ord("q"):
            return "quit"


def _new_run(frame_w, frame_h):
    return {
        "player": make_player_state(frame_w, frame_h),
        "obstacles": [],
        "t": 0.0,                 # seconds survived (excludes waiting/paused time)
        "spawn_timer": 0.0,
        "swarm_timer": 0.0,
        "swarm_warning": None,    # seconds left before a swarm spawns, or None
        "dodged": 0,
        "score": 0,
        "alive": True,
        "started": False,         # becomes True once a hand is first seen
        "hand_lost": 0.0,
        "over_start": None,
        "message": "",
        "extra": None,
    }


def _step(run, dt, level, frame_w, frame_h):
    """Advance the simulation by dt seconds."""
    run["t"] += dt
    t = run["t"]
    diff = get_difficulty(t, level)
    player = run["player"]
    obstacles = run["obstacles"]
    speed_px = diff["speed"] * frame_h           # screen-heights/s -> px/s
    target = (player["x"], player["y"])

    if t >= GRACE_SECONDS:
        run["spawn_timer"] += dt
        if run["spawn_timer"] >= diff["spawn_interval"] and len(obstacles) < diff["max_active"]:
            obstacles.append(spawn_obstacle(
                frame_w, frame_h, speed_px, target,
                homing_chance=diff["homing_chance"],
                turn_rate=diff["turn_rate"],
                homing_seconds=diff["homing_seconds"],
            ))
            run["spawn_timer"] = 0.0

        if diff["swarm_every"] > 0:
            if run["swarm_warning"] is None:
                run["swarm_timer"] += dt
                if run["swarm_timer"] >= diff["swarm_every"]:
                    run["swarm_warning"] = SWARM_WARNING_SECONDS   # announce first...
                    run["swarm_timer"] = 0.0
            else:
                run["swarm_warning"] -= dt
                if run["swarm_warning"] <= 0:                      # ...then spawn
                    for _ in range(diff["swarm_size"]):
                        obstacles.append(spawn_obstacle(
                            frame_w, frame_h, speed_px * 1.1, target,
                            turn_rate=diff["turn_rate"],
                            homing_seconds=diff["homing_seconds"],
                            force_homing=True,
                        ))
                    run["swarm_warning"] = None

    run["dodged"] += update_obstacles(obstacles, frame_w, frame_h, player["x"], player["y"], dt)
    run["score"] = int(t * 10) + run["dodged"] * 10


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
    ui = ui_scale(frame_h)

    run = _new_run(frame_w, frame_h)
    best = highscores.get_best(_best_key(difficulty))
    engine_hud.reset_score_animation()
    last_time = time.perf_counter()

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to read frame from webcam.")
            return "quit"

        now = time.perf_counter()
        dt = max(0.001, min(MAX_DT, now - last_time))
        last_time = now

        frame = cv2.flip(frame, 1)
        results = tracker.process(to_tracking_frame(frame))

        player = run["player"]
        update_player(player, results, frame_w, frame_h, dt)

        paused = False
        if run["alive"]:
            if not run["started"]:
                run["started"] = player["hand_visible"]      # wait for your hand
            else:
                run["hand_lost"] = 0.0 if player["hand_visible"] else run["hand_lost"] + dt
                paused = run["hand_lost"] > HAND_LOST_PAUSE_SECONDS
                if not paused:
                    _step(run, dt, difficulty, frame_w, frame_h)

                    if check_collision(player, run["obstacles"]):
                        run["alive"] = False
                        run["over_start"] = time.perf_counter()
                        run["message"] = pick_game_over_line(difficulty)
                        if highscores.submit(_best_key(difficulty), run["score"]):
                            best = run["score"]
                            run["extra"] = "NEW BEST!"
                        else:
                            run["extra"] = f"Best: {best}"
                        play_sound(SOUND_HIT)

        for obs in run["obstacles"]:
            draw_obstacle(frame, obs, player["z"], ui)
        draw_player(frame, player)
        draw_hud(frame, run["score"], run["dodged"], difficulty, max(best, run["score"]))
        draw_depth_gauge(frame, player["z"])

        if run["alive"]:
            if not run["started"]:
                draw_status(frame, "Raise your hand to start")
            elif paused:
                draw_status(frame, "Hand lost - show your hand to continue")
            if run["swarm_warning"] is not None:
                draw_swarm_warning(frame, run["swarm_warning"])
        else:
            elapsed = time.perf_counter() - run["over_start"]
            progress = min(1.0, elapsed / GAME_OVER_ANIM_DURATION)
            draw_game_over(frame, run["score"], run["message"], progress, run["extra"])

        show(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            return "menu"
        if key == ord("q"):
            return "quit"
        if key in (ord(" "), ord("r")) and not run["alive"]:
            run = _new_run(frame_w, frame_h)
            engine_hud.reset_score_animation()
            last_time = time.perf_counter()
        if key == ord("d") and not run["alive"]:
            new_difficulty = _select_difficulty(cap)
            if new_difficulty in ("menu", "quit", None):
                return new_difficulty or "quit"
            difficulty = new_difficulty
            best = highscores.get_best(_best_key(difficulty))
            run = _new_run(frame_w, frame_h)
            engine_hud.reset_score_animation()
            last_time = time.perf_counter()