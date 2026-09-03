import cv2

_FONT = cv2.FONT_HERSHEY_SIMPLEX



class Popup:
    __slots__ = ("text", "x", "y", "life", "max_life", "color", "scale")

    def __init__(self, text, x, y, color, scale, lifetime):
        self.text = text
        self.x = x
        self.y = y
        self.life = lifetime
        self.max_life = lifetime
        self.color = color
        self.scale = scale


def spawn_popup(popups, text, x, y, color=(255, 255, 255), scale=0.8, lifetime=0.8):
    popups.append(Popup(text, x, y, color, scale, lifetime))


def update_popups(popups, dt):
    for p in popups:
        p.y -= 40 * dt  
        p.life -= dt
    popups[:] = [p for p in popups if p.life > 0]


def draw_popups(frame, popups):
    for p in popups:
        t = max(0.0, p.life / p.max_life)
        thickness = 2 if t > 0.35 else 1
        scale = p.scale * (0.85 + 0.15 * t)
        size, _ = cv2.getTextSize(p.text, _FONT, scale, thickness + 1)
        origin = (int(p.x - size[0] / 2), int(p.y))
        cv2.putText(frame, p.text, origin, _FONT, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
        cv2.putText(frame, p.text, origin, _FONT, scale, p.color, thickness, cv2.LINE_AA)



def draw_hud(frame, score, time_left, pulse=0.0):
    h, w = frame.shape[:2]

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 60), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)

    score_scale = 1.0 + 0.35 * pulse
    cv2.putText(frame, f"Score: {score.total}", (20, 40), _FONT, score_scale,
                (255, 255, 255), 2, cv2.LINE_AA)

    if score.combo >= 2:
        combo_text = f"Combo x{score.current_multiplier()}  ({score.combo} in a row)"
        cv2.putText(frame, combo_text, (20, h - 20), _FONT, 0.7,
                    (0, 200, 255), 2, cv2.LINE_AA)

    timer_color = (0, 0, 255) if time_left <= 10 else (255, 255, 255)
    timer_text = f"Time: {int(time_left) + 1}s" if time_left > 0 else "Time: 0s"
    size, _ = cv2.getTextSize(timer_text, _FONT, 1.0, 2)
    cv2.putText(frame, timer_text, (w - size[0] - 20, 40), _FONT, 1.0,
                timer_color, 2, cv2.LINE_AA)

    cv2.putText(frame, "Pinch a bubble to pop it  -  watch out for bombs!",
                (20, 80), _FONT, 0.55, (200, 200, 200), 1, cv2.LINE_AA)


def draw_ready_countdown(frame, seconds_left):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)

    label = str(max(1, int(seconds_left) + 1)) if seconds_left > 0 else "POP!"
    size, _ = cv2.getTextSize(label, _FONT, 3.0, 6)
    origin = (w // 2 - size[0] // 2, h // 2 + size[1] // 2)
    cv2.putText(frame, label, origin, _FONT, 3.0, (0, 255, 255), 6, cv2.LINE_AA)

    sub = "Get your fingers ready..."
    sub_size, _ = cv2.getTextSize(sub, _FONT, 0.8, 2)
    cv2.putText(frame, sub, (w // 2 - sub_size[0] // 2, h // 2 + size[1] + 40),
                _FONT, 0.8, (255, 255, 255), 2, cv2.LINE_AA)


def draw_game_over(frame, score):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    def centered(text, y, scale, color, thickness):
        size, _ = cv2.getTextSize(text, _FONT, scale, thickness)
        cv2.putText(frame, text, (w // 2 - size[0] // 2, y), _FONT, scale,
                    color, thickness, cv2.LINE_AA)

    centered("GAME OVER", h // 2 - 100, 1.6, (255, 255, 255), 3)
    centered(f"Score: {score.total}", h // 2 - 40, 1.1, (0, 255, 255), 2)
    centered(f"Best combo: x{max(1, score.current_multiplier() if score.combo else 1)}"
              f"  ({score.best_combo} in a row)", h // 2, 0.7, (200, 200, 200), 1)

    bomb_line = "Didn't touch a single bomb. Show-off." if score.bombs_hit == 0 else \
        f"Bombs popped: {score.bombs_hit} (ouch)"
    centered(bomb_line, h // 2 + 35, 0.65, (170, 170, 255), 1)

    centered("R = play again    ESC = menu    Q = quit", h // 2 + 90, 0.7, (255, 255, 255), 2)