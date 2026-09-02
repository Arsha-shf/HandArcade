"""
games/catch/ package.

Public interface: run_catch(cap, tracker) -> "menu" | "quit" -- identical
signature to the old games/catch.py stub, so engine/menu.py needs zero
changes. Delete the old games/catch.py file when you drop this package in;
you can't have both a catch.py and a catch/ in the same games/ directory.
"""

from .game import run_catch

__all__ = ["run_catch"]