"""
games/fruit_slice/

Fruit Ninja-style game: slice falling fruit with your fingertip.

Split into a few small modules instead of one big file:
    fruit.py    - the Fruit entity (physics, slicing, drawing/fallback)
    spawner.py  - when/where new fruit are launched, difficulty ramp
    hud.py      - score/lives display + game-over overlay
    game.py     - the main loop that ties it all together

`from games.fruit_slice import run_fruit_slice` still works exactly as
before - engine/menu.py's contract with this module is unchanged:
    run_fruit_slice(cap, tracker) -> "quit" | "menu"
"""

from .game import run_fruit_slice

__all__ = ["run_fruit_slice"]