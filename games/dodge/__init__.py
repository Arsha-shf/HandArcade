"""
games/dodge/__init__.py

Turns games/dodge.py (single file) into games/dodge/ (package) without
breaking menu.py's `from games.dodge import run_dodge`.
"""

from .game import run_dodge

__all__ = ["run_dodge"]