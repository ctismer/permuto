"""Starting the viewer -- the two entry points, and where everything went.

The widgets themselves live next door and are documented there:

* :mod:`permuto.ui.base_view` -- the window, the frame timer, a paint that
  cannot crash Qt
* :mod:`permuto.ui.permutograph_view` -- the main viewer
* :mod:`permuto.ui.iridium_view` -- the ``/I`` mode, SIMONE
* :mod:`permuto.ui.keys` -- Qt key codes, translated once
* :mod:`permuto.menus` -- which key does what, and how the line reads: UI-free

This module keeps the names the rest of the program imports, so ``from
permuto.ui import viewer`` still reaches the views, their modes and the two
``run`` functions.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ..menus import (FileAction, IridiumAction, Key, MainAction, ProgramAction)
from ..session import PromptKind, Selection, UiMode
from .base_view import ViewBase
from .iridium_view import IridiumView, IriPhase
from .keys import exit_confirmed, feed_prompt
from .permutograph_view import PermutographView, load_note
from .prompt import PromptResult

__all__ = ["run", "run_iridium",
           "ViewBase", "PermutographView", "IridiumView",
           "UiMode", "PromptKind", "Selection", "IriPhase",
           "Key", "MainAction", "FileAction", "ProgramAction", "IridiumAction",
           "PromptResult", "feed_prompt", "exit_confirmed", "load_note"]


def _exec(app, view, _drive) -> int:
    """Show *view* and run it -- the Qt loop, or a test driver instead."""
    view.show()
    if _drive is not None:          # tests drive the real widget, no event loop
        _drive(view)
        return 0
    return app.exec()


def run(name_or_path, seed: int = 1, operators=None, _drive=None) -> int:
    app = QApplication.instance() or QApplication([])
    return _exec(app, PermutographView(name_or_path, seed=seed,
                                       operators=operators), _drive)


def run_iridium(seed: int = 1, _drive=None) -> int:
    app = QApplication.instance() or QApplication([])
    return _exec(app, IridiumView(seed=seed), _drive)
