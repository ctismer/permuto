"""Interactive PySide6 viewer -- ``polytop.mod`` as a Qt widget.

The interaction model lives in :mod:`permuto.session` (UI-free and tested);
this widget draws it and feeds it keystrokes, keeping the original's keys and
its two status lines.

Keys (as in the original):
    A next algorithm   C calc on/off   R run (continuous) on/off
    H hurry on/off     S spin on/off   N cycle name mode
    F file menu        P program menu  E edit operators (permutograph mode)
    space  single-step (while not running)   ESC confirm exit

File menu (F):     Q quit (asks)   O PostScript out   L load .pms/.ply
                   S save .pms
Program menu (P):  N kill/repair node   L break/repair line   C collapse
                   U uncollapse   S run SPA   T SPTA   P ParSum
                   Node actions ask for a node number (ReadInt); line/collapse
                   then pick the neighbour with space/Enter (SelectCard), as in
                   the original -- it had no mouse.
"""

from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QApplication, QWidget

from ..core import layout
from ..core.graph import Graph
from ..core.iri import Iridium
from ..editor import OperatorEditor
from ..errors import PermutoError
from ..formats import save_ps
from ..loader import make_session, session_from_file, write_session
from ..session import (EXIT_QUESTION, NodeAction, PromptKind, Selection,
                       UiMode, confirms_exit)
from . import render
from .prompt import FieldPrompt


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


def feed_prompt(prompt, ev) -> str:
    """Map a Qt key event onto a :class:`FieldPrompt`.

    The one place key events touch a prompt, used by every view -- returns
    ``"cancel"``, ``"submit"`` or ``"typing"``.
    """
    if ev.key() == Qt.Key_Escape:
        return "cancel"
    if ev.key() in (Qt.Key_Return, Qt.Key_Enter):
        return prompt.enter()
    if ev.key() == Qt.Key_Backspace:
        prompt.backspace()
        return "typing"
    prompt.type_char(ev.text())
    return "typing"


def load_note(warnings) -> str:
    """The status line for a load that had to be salvaged.

    A truncated session can produce one warning per node, so the line shows the
    first two and counts the rest.
    """
    if not warnings:
        return ""
    note = "; ".join(warnings[:2])
    if len(warnings) > 2:
        note += f" (+{len(warnings) - 2} more)"
    return f"loaded (truncated): {note}"


def exit_confirmed(ev) -> bool:
    """``UserIO.UserWantsToExit`` as a keystroke -- used by every view.

    The question is asked wherever the original asked it: ESC in the main menu,
    ESC or ``Q`` in the file menu, ESC or ``Q`` in Iridium.
    """
    return confirms_exit(ev.text(),
                         enter=ev.key() in (Qt.Key_Return, Qt.Key_Enter))


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


#: the editor's cursor keys, as :meth:`OperatorEditor.move` names them
_EDIT_MOVES = {Qt.Key_Up: "up", Qt.Key_Down: "down",
               Qt.Key_Home: "first", Qt.Key_End: "last"}


class PermutographView(ViewBase):
    """The main viewer: the graph, the operator panel and the two menu lines."""

    def __init__(self, name_or_path, seed: int = 1, operators=None):
        ops = list(operators) if operators is not None else None
        session = make_session(name_or_path, seed=seed, operators=ops)
        super().__init__(1000, 860)
        self.spec_name = str(name_or_path)
        self.operators = ops
        self.seed = seed
        self.session = session

        # UI chrome state
        self.ui_mode = UiMode.MAIN
        # a load note (e.g. a truncated session) shows in the status line
        self.message = load_note(session.load_warnings)
        self.pending = None         # a NodeAction awaiting its node number

        # an OperatorEditor while UiMode.EDIT, otherwise None
        self.editor = None

        # a FieldPrompt while typing a file name or node number
        self.prompt_kind = None
        self.select = None          # SelectCard state, when picking a neighbour

        title = self.spec_name if ops is None \
            else f"{self.spec_name} {' '.join(ops)}"
        self.setWindowTitle(f"permuto - {title}")

    @property
    def g(self):
        return self.session.graph

    # -- the clock -------------------------------------------------
    def _on_timer(self):
        # only relax freely while running; single-step waits for a key
        if self.ui_mode is UiMode.MAIN and self.session.running:
            self.session.advance_frame()
        elif self.session.program_mode:
            self.session.tick()      # a running program advances on its own
        self.update()

    # ================= painting ==================================
    def _paint(self, p):
        pic_w = self.width() - (260 if self.session.permuto else 0)
        render.paint(self.g, p, pic_w, self.height(),
                     op_colors=True,      # the viewer always colours by operator
                     program=self.session.program_mode,
                     name_mode=self.session.label_mode(self.ui_mode,
                                                       self.prompt_kind))
        if self.session.permuto and self.session.pm is not None:
            render.paint_operator_panel(
                self.session.pm, p, pic_w + 16, 60, self.height(),
                active_field=self.editor.field if self.editor else None,
                buffer_text=self.editor.buffer if self.editor else None)
        self._paint_chrome(p)

    def _paint_chrome(self, p):
        self._set_chrome_font(p)

        # top: the menu line for the current UI mode
        p.setPen(QColor(200, 205, 225))
        p.drawText(12, 22, self.session.top_line(self.ui_mode, self.prompt_kind))

        # bottom: the status line, plus the live prompt / message
        p.setPen(QColor(150, 155, 175))
        p.drawText(12, self.height() - 32, self.session.status_line())
        p.setPen(QColor(255, 230, 140))
        if self.ui_mode is UiMode.PROMPT and self.prompt:
            p.drawText(12, self.height() - 14,
                       self.prompt.display()
                       + (f"    {self.message}" if self.message else ""))
        elif self.ui_mode is UiMode.SELECT and self.select:
            p.drawText(12, self.height() - 14,
                       f" neighbour: node {self.select.current}   "
                       f"(space = next, Enter = pick, Esc = cancel)")
        elif self.message:
            p.setPen(QColor(255, 210, 140))
            p.drawText(12, self.height() - 14, self.message)

    # ================= input =====================================
    def keyPressEvent(self, ev):
        self.message = ""
        # every mode must name its handler: an unlisted one is a KeyError here,
        # not a key that silently lands in the main menu
        {UiMode.MAIN: self._main_key,
         UiMode.FILE: self._file_key,
         UiMode.PROGRAM: self._program_key,
         UiMode.EDIT: self._edit_key,
         UiMode.PROMPT: self._prompt_key,
         UiMode.SELECT: self._select_key,
         UiMode.CONFIRM: self._confirm_key}[self.ui_mode](ev)
        self.update()

    def _confirm_key(self, ev):
        """Yes closes, anything else goes back to the main menu."""
        if exit_confirmed(ev):
            self.close()
        else:
            self.ui_mode = UiMode.MAIN

    # -- main menu -------------------------------------------------
    def _main_key(self, ev):
        k = ev.text().lower()
        s = self.session
        if k == "a":
            s.next_algorithm()
        elif k == "c":
            s.calculating = not s.calculating
        elif k == "r":
            s.running = not s.running
        elif k == "h":
            s.hurry_up = not s.hurry_up
        elif k == "s":
            s.spinning = not s.spinning
        elif k == "n":
            s.cycle_name_mode()
        elif k == "f":
            self.ui_mode = UiMode.FILE
        elif k == "p":
            self.ui_mode = UiMode.PROGRAM    # numbers are forced on while here
        elif k == "e" and s.permuto:
            self._enter_edit()
        elif ev.key() == Qt.Key_Escape:
            self.ui_mode = UiMode.CONFIRM
        elif not s.running:
            s.tick()             # any other key single-steps

    # -- file menu -------------------------------------------------
    def _file_key(self, ev):
        k = ev.text().lower()
        if ev.key() == Qt.Key_Escape or k == "q":
            # (Q)uit means quit the program, and so does ESC here -- both
            # ask first, and a "no" drops back to the main menu.
            self.ui_mode = UiMode.CONFIRM
        elif k == "o":
            self._begin_prompt("PostScript out = ", PromptKind.PS)
        elif k == "l":
            self._begin_prompt("Load (.pms/.ply) = ", PromptKind.LOAD)
        elif k == "s":
            self._begin_prompt("Save .pms = ", PromptKind.SAVE)

    # -- program menu ----------------------------------------------
    def _program_key(self, ev):
        k = ev.text().lower()
        s = self.session
        if ev.key() == Qt.Key_Escape:
            self.ui_mode = UiMode.MAIN
        elif k == "n":
            self._ask_node("Node=", NodeAction.KILL, "kill/repair")
        elif k == "l":
            self._ask_node("Node 1=", NodeAction.BREAK, "break/repair a line")
        elif k == "c":
            self._ask_node("Collapse node=", NodeAction.COLLAPSE, "collapse")
        elif k == "u":
            self._ask_node("Uncollapse node=", NodeAction.UNCOLLAPSE, "uncollapse")
        elif k == "s":
            self._ask_node("StartNode=", NodeAction.SPA, "run SPA from")
        elif k == "t":
            self._guard(s.start_spta)
            self.ui_mode = UiMode.MAIN
        elif k == "p":
            if self._guard(s.start_par_sum):
                self.ui_mode = UiMode.MAIN

    def _ask_node(self, label, action, what):
        """Ask for a node the original way -- type its number and Enter
        (``UserIO.ReadInt``).  The DOS program had no mouse."""
        self.pending = action
        self._begin_prompt(f" {label}", PromptKind.NODE)
        self.message = f"type a node number and Enter to {what}"

    # -- operator editor -------------------------------------------
    def _enter_edit(self):
        self.ui_mode = UiMode.EDIT
        self.editor = OperatorEditor(self.session.pm)

    def _edit_key(self, ev):
        ed = self.editor
        if ev.text().isdigit():
            ed.type_digit(ev.text())
            return
        if ev.key() == Qt.Key_Backspace:
            ed.backspace()
            return
        where = _EDIT_MOVES.get(ev.key())
        leaving = ev.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape)
        if where is None and not leaving:
            return
        error = ed.commit()          # any move or exit commits the field first
        if error:
            self.message = error     # blocking validation: cannot leave
            return
        if leaving:
            self._leave_edit()
        else:
            ed.move(where)

    def _leave_edit(self):
        try:
            self.session.rebuild_permutograph(
                base_changed=self.editor.base_changed)
        except PermutoError as exc:
            self.message = str(exc)
        self.ui_mode = UiMode.MAIN
        self.editor = None

    # -- text prompt (filenames, node numbers) ---------------------
    def _begin_prompt(self, label, kind):
        self.ui_mode = UiMode.PROMPT
        self.prompt_kind = kind
        self.prompt = FieldPrompt(label.strip(),
                                  [(label.strip(), kind is PromptKind.NODE)])

    def _prompt_key(self, ev):
        result = feed_prompt(self.prompt, ev)
        if result == "cancel":
            self.pending = None
            self.ui_mode = UiMode.MAIN
        elif result == "submit":
            self._run_prompt()

    def _run_prompt(self):
        text = self.prompt.text()
        if not text:
            return
        if self.prompt_kind is PromptKind.NODE:
            if not text.isdigit() or int(text) not in self.g.nodes:
                self.message = f"no node {text} (1..{self.g.nnodes})"
                self.ui_mode = UiMode.MAIN
                self.pending = None
                return
            self._apply_pending(int(text))
            return
        try:
            if self.prompt_kind is PromptKind.PS:
                save_ps(self.g, text)
                self.message = f"wrote {text}"
            elif self.prompt_kind is PromptKind.SAVE:
                written = self._save_session(text)
                self.message = f"saved {written}"
            elif self.prompt_kind is PromptKind.LOAD:
                self._load_session(text)        # sets its own message
        except (PermutoError, OSError) as exc:
            self.message = str(exc)
        self.ui_mode = UiMode.MAIN

    def _save_session(self, path):
        return write_session(self.session, path)

    def _load_session(self, path):
        self.session = session_from_file(path)
        self.message = load_note(self.session.load_warnings) \
            or f"loaded {path}"

    # (no mouse: the DOS original was keyboard-only; node picking by click
    #  is deferred to the refactor/extend phase.)

    def _apply_pending(self, node):
        """Act on a node number just entered (``ReadInt`` returned)."""
        s = self.session
        action = self.pending
        if action is NodeAction.BREAK:
            self._begin_select(node, action, "select the other end")
        elif action is NodeAction.COLLAPSE:
            self._begin_select(node, action, "select the node to collapse onto")
        else:
            self._guard({NodeAction.KILL: lambda: s.kill_node(node),
                         NodeAction.UNCOLLAPSE: lambda: s.uncollapse(node),
                         NodeAction.SPA: lambda: s.start_spa(node)}[action])
            self._done_pending()

    def _begin_select(self, node, action, what):
        """Enter SelectCard: cycle *node*'s neighbours with space, Enter picks.

        This is the original's second step for line-break and collapse --
        ``UserIO.SelectCard`` over the node's link list.
        """
        neighbours = list(self.g.nodes[node].links)
        if not neighbours:
            self.message = f"node {node} has no neighbours"
            self._done_pending()
            return
        self.select = Selection(node=node, action=action, items=neighbours)
        self.ui_mode = UiMode.SELECT
        self.message = f"{what}: space = next, Enter = pick, Esc = cancel"

    def _select_key(self, ev):
        sel = self.select
        if ev.key() == Qt.Key_Escape:
            self._end_select()
        elif ev.key() == Qt.Key_Space:
            sel.advance()
        elif ev.key() in (Qt.Key_Return, Qt.Key_Enter):
            if sel.action is NodeAction.BREAK:
                self.session.toggle_line(sel.node, sel.current)
            elif sel.action is NodeAction.COLLAPSE:
                self._guard(lambda: self.session.collapse(sel.node, sel.current))
            self._end_select()

    def _end_select(self):
        self.select = None
        self._done_pending()

    def _done_pending(self):
        self.pending = None
        self.ui_mode = UiMode.MAIN

    # -- helpers ---------------------------------------------------
    def _guard(self, fn) -> bool:
        """Run a core action, showing any PermutoError instead of crashing."""
        try:
            fn()
            return True
        except PermutoError as exc:
            self.message = str(exc)
            return False


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
        layout.contract(self.graph, "new")
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
