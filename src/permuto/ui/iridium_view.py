"""The ``/I`` mode -- SIMONE, the satellite simulation.

A thin bypass reusing :mod:`permuto.core.iri`, :mod:`permuto.core.layout` and
``render.paint_iridium``, mirroring how ``polytop.mod`` "hacked it in at this
point": the network is grown one satellite at a time, left to settle, and only
then does the keyboard mean anything.

Its keys are :data:`permuto.menus.IRIDIUM_MENU`, and what they do is the table
at the foot of this module.
"""

from __future__ import annotations

from enum import Enum

from PySide6.QtGui import QColor

from ..core import layout
from ..core.graph import Graph
from ..core.iri import Iridium
from ..errors import PermutoError
from ..menus import IRIDIUM_MENU, IridiumAction
from ..session import EXIT_QUESTION, UiMode
from . import keys, render
from .base_view import ViewBase
from .keys import exit_confirmed, feed_prompt
from .prompt import FieldPrompt, PromptResult

SETTLE_STEPS = 180


class IriPhase(Enum):
    """The network is grown one satellite at a time, then left to settle.

    Only in ``RUN`` do the keys mean anything but "stop waiting", which is why
    this is not the same thing as :class:`UiMode`.
    """

    BUILD = "build"
    SETTLE = "settle"
    RUN = "run"


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
        p.drawText(12, 22, IRIDIUM_MENU.line())
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
        match feed_prompt(self.prompt, ev):
            case PromptResult.TYPING | PromptResult.MORE:
                return       # still filling in -- (T)ransmit asks for three
            case PromptResult.SUBMIT:
                self._run_prompt()
        self.prompt = None
        self.ui_mode = UiMode.MAIN

    def _main_key(self, ev):
        if self.phase is not IriPhase.RUN:
            # any key cuts the intro short, and still does its own job
            self.phase = IriPhase.RUN
            self.settle = SETTLE_STEPS
            self.message = ""
        action = IRIDIUM_MENU.action(keys.char(ev), keys.named(ev))
        if action is None:
            return
        if action.asks_for_numbers:
            self._begin_prompt(action)
        else:
            _IRIDIUM_ACTIONS[action](self)

    def _ask_exit(self):
        self.ui_mode = UiMode.CONFIRM
        self.message = EXIT_QUESTION

    def _queue_step(self):
        self.stepbuf += 1        # held down, the key repeats and they queue up

    def _repeat(self):
        self.iri.step()
        self.update()
        self.iri.step()
        self.iri.repeat_all()

    def _begin_prompt(self, action: IridiumAction):
        self.prompt_action = action
        self.ui_mode = UiMode.PROMPT
        fields = action.fields
        if len(fields) == 1:
            self.prompt = FieldPrompt(action.value, [(f"{fields[0]}=", True)])
        else:
            self.prompt = FieldPrompt(action.value, [(f, True) for f in fields])

    def _run_prompt(self):
        try:
            _IRIDIUM_PROMPTS[self.prompt_action](self, self.prompt.ints())
            self.message = ""
        except PermutoError as exc:
            self.message = str(exc)

    def _kill(self, nums):
        self.iri.kill_node(Iridium.num_to_label(nums[0]))

    def _transmit(self, nums):
        self.iri.step()
        self.iri.transmit(Iridium.num_to_label(nums[0]),
                          Iridium.num_to_label(nums[1]), nums[2])


# -- what each key of IRIDIUM_MENU does ------------------------------------

_IRIDIUM_ACTIONS = {
    IridiumAction.QUIT: IridiumView._ask_exit,
    IridiumAction.STEP: IridiumView._queue_step,
    IridiumAction.REPEAT: IridiumView._repeat,
    IridiumAction.CLEAR: lambda v: v.iri.reset(),
}

#: and what the two that collect numbers do once they have them
_IRIDIUM_PROMPTS = {
    IridiumAction.KILL: IridiumView._kill,
    IridiumAction.TRANSMIT: IridiumView._transmit,
}
