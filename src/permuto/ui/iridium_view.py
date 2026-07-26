"""The ``/I`` mode -- SIMONE, the satellite simulation.

A thin bypass reusing :mod:`permuto.core.iri`, :mod:`permuto.core.layout` and
``render.paint_iridium``, mirroring how ``polytop.mod`` "hacked it in at this
point": the network is grown one satellite at a time, left to settle, and only
then does the keyboard mean anything.
"""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from ..core import layout
from ..core.graph import Graph
from ..core.iri import Iridium
from ..errors import PermutoError
from ..session import EXIT_QUESTION, UiMode
from . import render
from .base_view import ViewBase
from .keys import exit_confirmed, feed_prompt
from .prompt import FieldPrompt

SETTLE_STEPS = 180


class IriPhase(Enum):
    """The network is grown one satellite at a time, then left to settle.

    Only in ``RUN`` do the keys mean anything but "stop waiting", which is why
    this is not the same thing as :class:`UiMode`.
    """

    BUILD = "build"
    SETTLE = "settle"
    RUN = "run"


class IriAction(Enum):
    """What the Iridium prompt is collecting -- ``PromptKind`` for the /I mode."""

    KILL = "kill"
    TRANSMIT = "transmit"


class IridiumView(ViewBase):
    """The ``/I`` mode -- a thin bypass reusing core.iri, core.layout and
    render.paint_iridium, mirroring how polytop.mod "hacked it in at this
    point".
    """

    def __init__(self, seed: int = 1):
        super().__init__(900, 820)
        self.graph = Graph()
        self.graph.set_dimensions(2)
        self.iri = Iridium(self.graph)
        self.ui_mode = UiMode.MAIN   # MAIN | PROMPT | CONFIRM, as in the viewer
        self.phase = IriPhase.BUILD
        self.settle = 0
        self.stepbuf = 0             # queued step keys (autorepeat)
        self.prompt_action = None
        self.message = ("SIMONE   building the network"
                        "   (any key skips the wait)")
        self.setWindowTitle("permuto - Iridium / SIMONE")

    def _relax(self):
        layout.backup(self.graph)
        layout.contract(self.graph, layout.Algorithm.NEW)
        layout.normalize(self.graph)

    def _on_timer(self):
        if self.phase is IriPhase.BUILD:
            if not self.iri.built:
                self.iri.new_node()
                for _ in range(5):
                    self._relax()
            else:
                self.phase = IriPhase.SETTLE
        elif self.phase is IriPhase.SETTLE:
            self._relax()
            self.settle += 1
            if self.settle >= SETTLE_STEPS:
                self.phase = IriPhase.RUN
                self.message = ""
        elif self.stepbuf > 0:      # drain queued steps, one per frame
            self.stepbuf -= 1
            self.iri.step()
        self.update()

    # -- drawing ---------------------------------------------------
    def _paint(self, p):
        render.paint_iridium(self.graph, p, self.width(), self.height())
        self._set_chrome_font(p)
        p.setPen(QColor(200, 205, 225))
        p.drawText(12, 22, "Kill  Transmit  Step  Repeat  Clear      Quit")
        p.setPen(QColor(255, 230, 140))
        if self.prompt:
            p.drawText(12, self.height() - 14, self.prompt.display())
        elif self.message:
            p.drawText(12, self.height() - 14, self.message)

    # -- input -----------------------------------------------------
    def keyPressEvent(self, ev):
        {UiMode.MAIN: self._main_key,
         UiMode.PROMPT: self._prompt_key,
         UiMode.CONFIRM: self._confirm_key}[self.ui_mode](ev)
        self.update()

    def _confirm_key(self, ev):
        """"Do You want to exit? (Y/N)" -- anything else goes back."""
        if exit_confirmed(ev):
            self.close()
        else:
            self.ui_mode = UiMode.MAIN
            self.message = ""

    def _prompt_key(self, ev):
        result = feed_prompt(self.prompt, ev)
        if result in ("typing", "more"):
            return            # still filling in -- "transmit" asks for three
        if result == "submit":
            self._run_prompt()
        self.prompt = None
        self.ui_mode = UiMode.MAIN

    def _main_key(self, ev):
        if self.phase is not IriPhase.RUN:
            # any key cuts the intro short, and still does its own job
            self.phase = IriPhase.RUN
            self.settle = SETTLE_STEPS
            self.message = ""
        k = ev.text().lower()
        if ev.key() == Qt.Key_Escape or k == "q":
            self.ui_mode = UiMode.CONFIRM
            self.message = EXIT_QUESTION
        elif k in ("s", " ") or ev.key() == Qt.Key_Space:
            self.stepbuf += 1
        elif k == "r":
            self.iri.step()
            self.update()
            self.iri.step()
            self.iri.repeat_all()
        elif k == "c":
            self.iri.reset()
        elif k == "k":
            self._begin_prompt(IriAction.KILL, ["Node"])
        elif k == "t":
            self._begin_prompt(IriAction.TRANSMIT, ["Node1", "Node2", "Repeat"])

    def _begin_prompt(self, action, fields):
        self.prompt_action = action
        self.ui_mode = UiMode.PROMPT
        if len(fields) == 1:
            self.prompt = FieldPrompt(action.value, [(f"{fields[0]}=", True)])
        else:
            self.prompt = FieldPrompt(action.value, [(f, True) for f in fields])

    def _run_prompt(self):
        nums = self.prompt.ints()
        try:
            if self.prompt_action is IriAction.KILL:
                self.iri.kill_node(Iridium.num_to_label(nums[0]))
            elif self.prompt_action is IriAction.TRANSMIT:
                self.iri.step()
                self.iri.transmit(Iridium.num_to_label(nums[0]),
                                  Iridium.num_to_label(nums[1]), nums[2])
            self.message = ""
        except PermutoError as exc:
            self.message = str(exc)
