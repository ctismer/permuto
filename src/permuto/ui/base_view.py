"""What every view is: a window, a frame timer and a painter that cannot
crash Qt.

The two views draw entirely different things, but they are the same kind of
object -- a widget that gets a tick, paints itself, and reads keys.  That much
is here; everything specific is in :mod:`permuto.ui.permutograph_view` and
:mod:`permuto.ui.iridium_view`.
"""

from __future__ import annotations

import sys
import traceback

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget

from . import render


def _report_paint_error(exc: Exception) -> None:
    """Print a paint-time exception without letting it escape the Qt slot.

    An exception leaving paintEvent is stored in a traceback that keeps the
    local QPainter alive until interpreter shutdown, where destroying it on an
    already-torn-down window segfaults.  We print it here and swallow it so the
    window keeps running and the process exits cleanly.
    """
    traceback.print_exc()
    # drop any saved traceback so it cannot hold a QPainter past shutdown
    if hasattr(sys, "last_traceback"):
        sys.last_traceback = None


class ViewBase(QWidget):
    """What both views share: the window, the frame timer, a painter that
    cannot crash Qt, and the chrome font.

    Subclasses fill in :meth:`_on_timer` (one frame's worth of work) and
    :meth:`_paint` (the picture, with the background already filled).  The
    prompt flows stay with them: the two views do genuinely different things
    when one is submitted.
    """

    TICK_MS = 30

    def __init__(self, width: int, height: int):
        super().__init__()
        self.message = ""
        self._paint_error = None    # last exception in paintEvent, for tests
        self.prompt = None          # a FieldPrompt while typing
        self.setFocusPolicy(Qt.StrongFocus)   # make sure keys arrive here
        self.resize(width, height)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_timer)
        self.timer.start(self.TICK_MS)

    def _on_timer(self):
        raise NotImplementedError

    def _paint(self, p):
        raise NotImplementedError

    def paintEvent(self, _ev):
        # The painter MUST be ended even if drawing raises: an exception
        # escaping paintEvent leaves the QPainter alive in a traceback and
        # crashes at interpreter shutdown (QPainter::~QPainter on a dead
        # window).  try/finally ends it; the error is shown, not fatal.
        p = QPainter(self)
        try:
            p.fillRect(self.rect(), QColor(*render.BACKGROUND))
            self._paint(p)
        except Exception as exc:      # noqa: BLE001 -- never let paint crash Qt
            self._paint_error = exc
            _report_paint_error(exc)
            self.message = f"draw error: {exc}"
        finally:
            p.end()

    def _set_chrome_font(self, p):
        """The 9-px Menlo of the two status lines, scaled with the window."""
        font = QFont("Menlo")
        font.setPixelSize(int(render._scaled(self.height(), 9)))
        p.setFont(font)
