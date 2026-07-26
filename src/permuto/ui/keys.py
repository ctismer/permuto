"""Qt key events, translated once -- the only module that knows Qt key codes.

Everything downstream works in :class:`permuto.menus.Key` and characters, so
the menus, the editor and the prompts stay frontend-neutral: a second frontend
replaces this file and nothing else.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt

from ..editor import Move
from ..menus import Key
from ..session import confirms_exit
from .prompt import PromptResult

#: Enter on the main keyboard and Enter on the numeric pad are two key codes
ENTER_KEYS = (Qt.Key_Return, Qt.Key_Enter)

_NAMED = {Qt.Key_Escape: Key.ESCAPE,
          Qt.Key_Return: Key.ENTER,
          Qt.Key_Enter: Key.ENTER,
          Qt.Key_Space: Key.SPACE,
          Qt.Key_Backspace: Key.BACKSPACE,
          Qt.Key_Up: Key.UP,
          Qt.Key_Down: Key.DOWN,
          Qt.Key_Home: Key.HOME,
          Qt.Key_End: Key.END}

#: where the editor's cursor keys go, as :class:`permuto.editor.Move` names it
EDIT_MOVES = {Key.UP: Move.UP, Key.DOWN: Move.DOWN,
              Key.HOME: Move.FIRST, Key.END: Move.LAST}


def named(ev) -> Optional[Key]:
    """The :class:`Key` this event is, or None if it types a character."""
    return _NAMED.get(ev.key())


def char(ev) -> str:
    """The character this event types, lower-cased -- "" if it types none."""
    return ev.text().lower()


def feed_prompt(prompt, ev) -> PromptResult:
    """Map a Qt key event onto a :class:`FieldPrompt`.

    The one place key events touch a prompt, used by every view.
    """
    key = named(ev)
    if key is Key.ESCAPE:
        return PromptResult.CANCEL
    if key is Key.ENTER:
        return prompt.enter()
    if key is Key.BACKSPACE:
        prompt.backspace()
        return PromptResult.TYPING
    prompt.type_char(ev.text())
    return PromptResult.TYPING


def exit_confirmed(ev) -> bool:
    """``UserIO.UserWantsToExit`` as a keystroke -- used by every view.

    The question is asked wherever the original asked it: ESC in the main menu,
    ESC or ``Q`` in the file menu, ESC or ``Q`` in Iridium.
    """
    return confirms_exit(ev.text(), enter=named(ev) is Key.ENTER)
