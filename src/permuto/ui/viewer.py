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

import os
import pathlib
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QApplication, QWidget

from ..core import intvector as iv
from ..core import layout
from ..core.graph import Graph
from ..core.iri import Iridium
from ..core.pm import find_link
from ..errors import PermutoError
from ..formats import load_session, read_pgd, save_ps, save_session
from ..formats.plyfile import PlySession
from ..session import (DIMENSION_CHECK_INTERVAL, EXIT_QUESTION, Mode, NameMode,
                       Session, confirms_exit, new_permutograph_session)
from . import render
from .prompt import FieldPrompt


def _nod_dir():
    """Where the named sample graphs live.

    Prefer the copy bundled with the package (so ``pip install`` + ``permuto
    show pgl4`` just works), and fall back to the recovered originals under
    ``legacy/`` when running from a source checkout.
    """
    here = os.path.dirname(__file__)
    bundled = os.path.join(here, "..", "data", "nod")
    if os.path.isdir(bundled):
        return bundled
    return os.path.join(here, "..", "..", "..", "legacy", "modula", "nod")


def _resolve_file(p: str):
    """Return the .pgd/.nod path for a name or file, or None if none exists."""
    candidates = []
    if os.path.exists(p):
        candidates.append(p)
        if p.endswith(".nod") and os.path.exists(p[:-4] + ".pgd"):
            candidates.insert(0, p[:-4] + ".pgd")
    else:
        base = os.path.join(_nod_dir(), p)
        for ext in (".pgd", ".nod"):
            if os.path.exists(base + ext):
                candidates.append(base + ext)
        if p.endswith((".pgd", ".nod")) and os.path.exists(os.path.join(_nod_dir(), p)):
            candidates.insert(0, os.path.join(_nod_dir(), p))
    return candidates[0] if candidates else None


def load_graph(name_or_path, *, dimensions: int = iv.MAXDIMEN,
               seed: int = 0, operators=None) -> Graph:
    """Resolve a spec to a Graph (file, or base + operators to build)."""
    if operators is not None:
        return Graph.build(str(name_or_path), list(operators),
                           dimensions=dimensions, seed=seed)
    chosen = _resolve_file(str(name_or_path))
    if chosen is None:
        raise FileNotFoundError(
            f"nothing found for {name_or_path!r}: no session (.pms/.ply), "
            f"no graph (.pgd/.nod), and no operators to build one")
    if chosen.endswith(".pgd"):
        return Graph.from_pgd(chosen, dimensions=dimensions, seed=seed)
    return Graph.load_nod(chosen, dimensions=dimensions, seed=seed)


def _session_path(p: str):
    """Return the session file for *p*, trying ``.pms``/``.ply`` too, or None.

    So ``show xanti`` finds ``xanti.pms`` -- symmetric with save, which appends
    ``.pms`` to a bare name.
    """
    for cand in (p, p + ".pms", p + ".ply"):
        if not os.path.isfile(cand):
            continue
        if cand.endswith((".pms", ".ply")):
            return cand
        with open(cand, "rb") as f:
            if f.read(15) == b"permuto session":
                return cand
    return None


def make_session(name_or_path, *, seed: int = 1, operators=None) -> Session:
    """Build the initial :class:`Session` for the viewer.

    A base + operators (or a ``.pgd``) yields permutograph mode, with a live
    ``PM``; a plain ``.nod`` yields polytop mode; a saved session file
    (``.pms`` / ``.ply``) is loaded and resumed where it left off.
    """
    if operators is not None:
        return new_permutograph_session(str(name_or_path), list(operators))
    p = str(name_or_path)
    session_file = _session_path(p)
    if session_file is not None:
        loaded = load_session(session_file)
        mode = Mode.PERMUTO if loaded.pm is not None else Mode.POLYTOP
        session = Session(graph=loaded.graph, mode=mode, pm=loaded.pm)
        session.iteration = loaded.iteration
        session.load_warnings = list(loaded.warnings)   # shown in the status line
        return session
    chosen = _resolve_file(p)
    if chosen and chosen.endswith(".pgd"):
        cmd = read_pgd(chosen)
        return new_permutograph_session(cmd.base, cmd.operators)
    g = load_graph(name_or_path, seed=seed)
    return Session(graph=g, mode=Mode.POLYTOP)


def _report_paint_error(exc: Exception) -> None:
    """Print a paint-time exception without letting it escape the Qt slot.

    An exception leaving paintEvent is stored in a traceback that keeps the
    local QPainter alive until interpreter shutdown, where destroying it on an
    already-torn-down window segfaults.  We print it here and swallow it so the
    window keeps running and the process exits cleanly.
    """
    import traceback

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
        self.ui_mode = "main"       # main | file | program | edit | prompt
        self.labels = False
        self.op_colors = True
        # a load note (e.g. a truncated session) shows in the status line
        self.message = "; ".join(session.load_warnings)
        self.pending = None         # (action, ...) awaiting a node click

        # operator editor state
        self.edit_field = None      # ('base',) or ('op', i, j)
        self.edit_buffer = ""
        self.edit_base_before = ""

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
        if self.ui_mode == "main" and self.session.running:
            self._run_a_frame()
        elif self.session.program_mode:
            self.session.tick()      # a running program advances on its own
        self.update()

    def _run_a_frame(self):
        """One timer tick's worth of relaxation.

        Normally one iteration per frame.  With HurryUp the original traded
        looking for computing -- it drew only at the 25-iteration
        checkpoints and skipped the spin while calculating -- so here it
        keeps iterating until ``tick`` asks for a redraw.  Without this the
        switch only cost the rotation and bought nothing.
        """
        s = self.session
        if not s.hurry_up:
            s.tick()
            return
        for _ in range(DIMENSION_CHECK_INTERVAL):   # at most one checkpoint
            if s.tick():
                break

    # ================= painting ==================================
    def _paint(self, p):
        pic_w = self.width() - (260 if self.session.permuto else 0)
        render.paint(self.g, p, pic_w, self.height(),
                     labels=self.labels, op_colors=self.op_colors,
                     program=self.session.program_mode,
                     name_mode=self._draw_name_mode())
        if self.session.permuto and self.session.pm is not None:
            render.paint_operator_panel(
                self.session.pm, p, pic_w + 16, 60, self.height(),
                active_field=self.edit_field if self.ui_mode == "edit" else None,
                buffer_text=self.edit_buffer if self.ui_mode == "edit" else None)
        self._paint_chrome(p)

    def _draw_name_mode(self):
        """Node numbers are forced on whenever a node is being chosen, so
        there is always something to read -- the original drew them before
        the program menu regardless of the current name mode."""
        picking = self.ui_mode in ("program", "select") or \
            (self.ui_mode == "prompt" and self.prompt_kind == "node")
        return NameMode.NUMBER if picking else self.session.name_mode

    def _paint_chrome(self, p):
        self._set_chrome_font(p)

        # top: the menu line for the current UI mode
        p.setPen(QColor(200, 205, 225))
        p.drawText(12, 22, self._top_line())

        # bottom: the status line, plus the live prompt / message
        p.setPen(QColor(150, 155, 175))
        p.drawText(12, self.height() - 32, self.session.status_line())
        p.setPen(QColor(255, 230, 140))
        if self.ui_mode == "prompt" and self.prompt:
            p.drawText(12, self.height() - 14,
                       self.prompt.display()
                       + (f"    {self.message}" if self.message else ""))
        elif self.ui_mode == "select" and self.select:
            sel = self.select
            cand = sel["items"][sel["pos"]]
            p.drawText(12, self.height() - 14,
                       f" neighbour: node {cand}   "
                       f"(space = next, Enter = pick, Esc = cancel)")
        elif self.message:
            p.setPen(QColor(255, 210, 140))
            p.drawText(12, self.height() - 14, self.message)

    def _top_line(self):
        if self.ui_mode == "file":
            return self.session.file_menu_line()
        if self.ui_mode == "prompt":
            return (self.session.file_menu_line()
                    if self.prompt_kind in ("ps", "save", "load")
                    else self.session.program_menu_line())
        if self.ui_mode in ("program", "select"):
            return self.session.program_menu_line()
        if self.ui_mode == "edit":
            return ("editing operators: digits, arrows move, "
                    "Ctrl-Home base, Ctrl-End last, Enter/Esc leave")
        if self.ui_mode == "confirm":
            return EXIT_QUESTION
        return self.session.menu_line()

    # ================= input =====================================
    def keyPressEvent(self, ev):
        self.message = ""
        if self.ui_mode == "edit":
            self._edit_key(ev)
        elif self.ui_mode == "prompt":
            self._prompt_key(ev)
        elif self.ui_mode == "select":
            self._select_key(ev)
        elif self.ui_mode == "file":
            self._file_key(ev)
        elif self.ui_mode == "program":
            self._program_key(ev)
        elif self.ui_mode == "confirm":
            self._confirm_key(ev)
        else:
            self._main_key(ev)
        self.update()

    def _confirm_key(self, ev):
        """Yes closes, anything else goes back to the main menu."""
        if exit_confirmed(ev):
            self.close()
        else:
            self.ui_mode = "main"

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
            self.ui_mode = "file"
        elif k == "p":
            self.ui_mode = "program"    # numbers are forced on while here
        elif k == "e" and s.permuto:
            self._enter_edit()
        elif ev.key() == Qt.Key_Escape:
            self.ui_mode = "confirm"
        elif not s.running:
            s.tick()             # any other key single-steps

    # -- file menu -------------------------------------------------
    def _file_key(self, ev):
        k = ev.text().lower()
        if ev.key() == Qt.Key_Escape or k == "q":
            # (Q)uit means quit the program, and so does ESC here -- both
            # ask first, and a "no" drops back to the main menu.
            self.ui_mode = "confirm"
        elif k == "o":
            self._begin_prompt("PostScript out = ", "ps")
        elif k == "l":
            self._begin_prompt("Load (.pms/.ply) = ", "load")
        elif k == "s":
            self._begin_prompt("Save .pms = ", "save")

    # -- program menu ----------------------------------------------
    def _program_key(self, ev):
        k = ev.text().lower()
        s = self.session
        if ev.key() == Qt.Key_Escape:
            self.ui_mode = "main"
        elif k == "n":
            self._ask_node("Node=", ("kill",), "kill/repair")
        elif k == "l":
            self._ask_node("Node 1=", ("break1",), "break/repair a line")
        elif k == "c":
            self._ask_node("Collapse node=", ("collapse1",), "collapse")
        elif k == "u":
            self._ask_node("Uncollapse node=", ("uncollapse",), "uncollapse")
        elif k == "s":
            self._ask_node("StartNode=", ("spa",), "run SPA from")
        elif k == "t":
            self._guard(s.start_spta)
            self.ui_mode = "main"
        elif k == "p":
            if self._guard(s.start_par_sum):
                self.ui_mode = "main"

    def _ask_node(self, label, pending, what):
        """Ask for a node the original way -- type its number and Enter
        (``UserIO.ReadInt``).  The DOS program had no mouse."""
        self.pending = pending
        self._begin_prompt(f" {label}", "node")
        self.message = f"type a node number and Enter to {what}"

    # -- operator editor -------------------------------------------
    def _enter_edit(self):
        self.ui_mode = "edit"
        self.edit_base_before = self.session.pm.base
        self.edit_field = ("base",)
        self.edit_buffer = self.session.pm.base

    def _commit_field(self) -> bool:
        """Validate and store the field being edited; True if it took."""
        pm = self.session.pm
        try:
            if self.edit_field[0] == "base":
                pm.set_base(self.edit_buffer)
            else:
                _, i, j = self.edit_field
                pm.set_cycle(i, j, self.edit_buffer)
            return True
        except PermutoError as exc:
            self.message = str(exc)
            return False

    def _load_field(self):
        pm = self.session.pm
        if self.edit_field[0] == "base":
            self.edit_buffer = pm.base
        else:
            _, i, j = self.edit_field
            self.edit_buffer = pm.optable[i - 1][j - 1]

    def _edit_key(self, ev):
        key = ev.key()
        if ev.text().isdigit():
            self.edit_buffer += ev.text()
            return
        if key == Qt.Key_Backspace:
            self.edit_buffer = self.edit_buffer[:-1]
            return
        # any move or exit first tries to commit the current field
        moving = key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Return,
                         Qt.Key_Enter, Qt.Key_Escape, Qt.Key_Home, Qt.Key_End)
        if moving and not self._commit_field():
            return                       # blocking validation: cannot leave
        if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape):
            self._leave_edit()
        elif key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Home, Qt.Key_End):
            self._move_edit(key)

    def _edit_fields(self):
        fields = [("base",)]
        pm = self.session.pm
        for i in range(len(pm.optable)):
            for j in range(len(pm.optable[i])):
                fields.append(("op", i + 1, j + 1))
        return fields

    def _move_edit(self, key):
        fields = self._edit_fields()
        idx = fields.index(self.edit_field)
        if key == Qt.Key_Up:
            idx = max(0, idx - 1)
        elif key == Qt.Key_Down:
            idx = min(len(fields) - 1, idx + 1)
        elif key == Qt.Key_Home:
            idx = 0
        elif key == Qt.Key_End:
            idx = max((n for n, f in enumerate(fields)
                       if f == ("base",) or self._field_value(f)), default=0)
        self.edit_field = fields[idx]
        self._load_field()

    def _field_value(self, field):
        if field[0] == "base":
            return self.session.pm.base
        _, i, j = field
        return self.session.pm.optable[i - 1][j - 1]

    def _leave_edit(self):
        base_changed = self.session.pm.base != self.edit_base_before
        try:
            self.session.rebuild_permutograph(base_changed=base_changed)
        except PermutoError as exc:
            self.message = str(exc)
        self.ui_mode = "main"
        self.edit_field = None

    # -- text prompt (filenames, node numbers) ---------------------
    def _begin_prompt(self, label, kind):
        self.ui_mode = "prompt"
        self.prompt_kind = kind
        self.prompt = FieldPrompt(label.strip(), [(label.strip(),
                                                   kind == "node")])

    def _prompt_key(self, ev):
        result = feed_prompt(self.prompt, ev)
        if result == "cancel":
            self.pending = None
            self.ui_mode = "main"
        elif result == "submit":
            self._run_prompt()

    def _run_prompt(self):
        text = self.prompt.text()
        if not text:
            return
        if self.prompt_kind == "node":
            if not text.isdigit() or int(text) not in self.g.nodes:
                self.message = f"no node {text} (1..{self.g.nnodes})"
                self.ui_mode = "main"
                self.pending = None
                return
            self._apply_pending(int(text))
            return
        try:
            if self.prompt_kind == "ps":
                save_ps(self.g, text)
                self.message = f"wrote {text}"
            elif self.prompt_kind == "save":
                written = self._save_session(text)
                self.message = f"saved {written}"
            elif self.prompt_kind == "load":
                self._load_session(text)        # sets its own message
        except (PermutoError, OSError) as exc:
            self.message = str(exc)
        self.ui_mode = "main"

    def _save_session(self, path):
        pm = self.session.pm
        mode = "permuto" if self.session.permuto else "polytop"
        sess = PlySession(
            graph=self.g, permuto=self.session.permuto, mode=mode,
            base=pm.base if pm else "",
            optable=[list(r) for r in pm.optable] if pm else [],
            last_edit_line=pm.last_edit_line if pm else 0,
            iteration=self.session.iteration)
        # the viewer always saves text .pms (binary .ply is read-only legacy);
        # whatever extension was typed, the file is a .pms
        out = pathlib.Path(path).with_suffix(".pms")
        return save_session(out, sess, binary=False)

    def _load_session(self, path):
        loaded = load_session(path)  # .pms or .ply, detected by content
        # No rescaling here: Session frames whatever coordinates it is given.
        if loaded.pm is not None:
            self.session = Session(graph=loaded.graph, mode=Mode.PERMUTO,
                                   pm=loaded.pm)
        else:
            self.session = Session(graph=loaded.graph, mode=Mode.POLYTOP)
        self.session.iteration = loaded.iteration    # restore where it was
        if loaded.warnings:                          # a salvaged truncation
            self.message = "loaded (truncated): " + "; ".join(
                loaded.warnings[:2]) + (
                f" (+{len(loaded.warnings) - 2} more)"
                if len(loaded.warnings) > 2 else "")
        else:
            self.message = f"loaded {path}"

    # (no mouse: the DOS original was keyboard-only; node picking by click
    #  is deferred to the refactor/extend phase.)

    def _apply_pending(self, node):
        """Act on a node number just entered (``ReadInt`` returned)."""
        s = self.session
        action = self.pending[0]
        if action == "kill":
            self.g.nodes[node].state.dead = not self.g.nodes[node].state.dead
            self._done_pending()
        elif action == "break1":
            self._begin_select(node, "break2", "select the other end")
        elif action == "collapse1":
            self._begin_select(node, "collapse2", "select the node to collapse onto")
        elif action == "uncollapse":
            self._guard(lambda: s.pm.uncollapse(self.g, node))
            self._done_pending()
        elif action == "spa":
            self._guard(lambda: s.start_spa(node))
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
        self.select = {"node": node, "action": action,
                       "items": neighbours, "pos": 0}
        self.ui_mode = "select"
        self.message = f"{what}: space = next, Enter = pick, Esc = cancel"

    def _select_key(self, ev):
        sel = self.select
        if ev.key() == Qt.Key_Escape:
            self._end_select()
        elif ev.key() == Qt.Key_Space:
            sel["pos"] = (sel["pos"] + 1) % len(sel["items"])
        elif ev.key() in (Qt.Key_Return, Qt.Key_Enter):
            chosen = sel["items"][sel["pos"]]
            if sel["action"] == "break2":
                self._toggle_broken(sel["node"], chosen)
            elif sel["action"] == "collapse2":
                self._guard(
                    lambda: self.session.pm.collapse(self.g, sel["node"], chosen))
            self._end_select()

    def _end_select(self):
        self.select = None
        self._done_pending()

    def _done_pending(self):
        self.pending = None
        self.ui_mode = "main"

    def _toggle_broken(self, n1, n2):
        for a, b in ((n1, n2), (n2, n1)):
            k = find_link(self.g, a, b)
            if k:
                st = self.g.nodes[a].state
                st.broken ^= {k}

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
        self.phase = "build"        # build -> settle -> run
        self.settle = 0
        self.stepbuf = 0            # queued step keys (autorepeat)
        self.confirming = False     # showing the exit question
        self.prompt_action = None
        self.message = ("SIMONE   building the network"
                        "   (any key skips the wait)")
        self.setWindowTitle("permuto - Iridium / SIMONE")

    def _relax(self):
        layout.backup(self.graph)
        layout.contract(self.graph, "new")
        layout.normalize(self.graph)

    def _on_timer(self):
        if self.phase == "build":
            if not self.iri.built:
                self.iri.new_node()
                for _ in range(5):
                    self._relax()
            else:
                self.phase = "settle"
        elif self.phase == "settle":
            self._relax()
            self.settle += 1
            if self.settle >= SETTLE_STEPS:
                self.phase = "run"
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
        if self.confirming:      # "Do You want to exit? (Y/N)"
            if exit_confirmed(ev):
                self.close()
            else:
                self.confirming = False
                self.message = ""
            self.update()
            return
        if self.prompt:
            result = feed_prompt(self.prompt, ev)
            if result == "cancel":
                self.prompt = None
            elif result == "submit":
                self._run_prompt()
                self.prompt = None
            self.update()
            return
        if self.phase != "run":
            self.phase = "run"      # any key skips the intro wait
            self.settle = SETTLE_STEPS
            self.message = ""
        k = ev.text().lower()
        if ev.key() == Qt.Key_Escape or k == "q":
            self.confirming = True
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
            self._begin_prompt("kill", ["Node"])
        elif k == "t":
            self._begin_prompt("transmit", ["Node1", "Node2", "Repeat"])
        self.update()

    def _begin_prompt(self, action, fields):
        self.prompt_action = action
        if len(fields) == 1:
            self.prompt = FieldPrompt(action, [(f"{fields[0]}=", True)])
        else:
            self.prompt = FieldPrompt(action, [(f, True) for f in fields])

    def _run_prompt(self):
        action, nums = self.prompt_action, self.prompt.ints()
        try:
            if action == "kill":
                self.iri.kill_node(Iridium.num_to_label(nums[0]))
            elif action == "transmit":
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
