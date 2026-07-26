"""Qt key events, translated once.

Both views ask the same questions of a key event -- does it confirm the exit
question, what does it do to a prompt, where does it move the operator cursor
-- and each answer belongs in one place rather than once per view.  This is
also the only module that has to know Qt's key codes.
"""

from __future__ import annotations

from PySide6.QtCore import Qt

from ..session import confirms_exit

#: Enter on the main keyboard and Enter on the numeric pad are two key codes
ENTER_KEYS = (Qt.Key_Return, Qt.Key_Enter)

#: the editor's cursor keys, as :meth:`OperatorEditor.move` names them
EDIT_MOVES = {Qt.Key_Up: "up", Qt.Key_Down: "down",
              Qt.Key_Home: "first", Qt.Key_End: "last"}


def feed_prompt(prompt, ev) -> str:
    """Map a Qt key event onto a :class:`FieldPrompt`.

    The one place key events touch a prompt, used by every view -- returns
    ``"cancel"``, ``"submit"``, ``"more"`` or ``"typing"``.
    """
    if ev.key() == Qt.Key_Escape:
        return "cancel"
    if ev.key() in ENTER_KEYS:
        return prompt.enter()
    if ev.key() == Qt.Key_Backspace:
        prompt.backspace()
        return "typing"
    prompt.type_char(ev.text())
    return "typing"


def exit_confirmed(ev) -> bool:
    """``UserIO.UserWantsToExit`` as a keystroke -- used by every view.

    The question is asked wherever the original asked it: ESC in the main menu,
    ESC or ``Q`` in the file menu, ESC or ``Q`` in Iridium.
    """
    return confirms_exit(ev.text(), enter=ev.key() in ENTER_KEYS)
