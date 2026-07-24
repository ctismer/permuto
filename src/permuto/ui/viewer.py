"""Interactive PySide6 viewer -- ``polytop.mod`` as a Qt widget.

The interaction model lives in :mod:`permuto.session` (UI-free and tested);
this widget draws it and feeds it keystrokes, keeping the original's keys and
its two status lines.

Keys (as in the original):
    A next algorithm   C calc on/off   R run (continuous) on/off
    H hurry on/off     S spin on/off   N cycle name mode
    F file menu        P program menu  E edit operators (permutograph mode)
    space  single-step (while not running)   ESC confirm exit

File menu (F):     Q quit   O PostScript out   L load .ply   S save .ply
Program menu (P):  N kill/repair node   L break/repair line   C collapse
                   U uncollapse   S run SPA   T SPTA   P ParSum
                   (for node/line actions, click the node(s) afterwards)
"""

from __future__ import annotations

import os

from ..core import intvector as iv
from ..core.graph import Graph
from ..core.pm import PM
from ..errors import PermutoError
from ..session import Mode, NameMode, Session, new_permutograph_session
from . import render


def _nod_dir():
    return os.path.join(os.path.dirname(__file__), "..", "..", "..",
                        "legacy", "modula", "nod")


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
            f"no .pgd/.nod found for {name_or_path!r} "
            f"(and no operators given to build one)")
    if chosen.endswith(".pgd"):
        return Graph.from_pgd(chosen, dimensions=dimensions, seed=seed)
    return Graph.load_nod(chosen, dimensions=dimensions, seed=seed)


def make_session(name_or_path, *, seed: int = 1, operators=None) -> Session:
    """Build the initial :class:`Session` for the viewer.

    A base + operators (or a ``.pgd``) yields permutograph mode, with a live
    :class:`PM`; a plain ``.nod`` yields polytop mode.
    """
    if operators is not None:
        return new_permutograph_session(str(name_or_path), list(operators))
    chosen = _resolve_file(str(name_or_path))
    if chosen and chosen.endswith(".pgd"):
        from ..formats import read_pgd

        cmd = read_pgd(chosen)
        return new_permutograph_session(cmd.base, cmd.operators)
    g = load_graph(name_or_path, seed=seed)
    return Session(graph=g, mode=Mode.POLYTOP)


def run(name_or_path, seed: int = 1, operators=None) -> int:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QColor, QFont, QPainter
    from PySide6.QtWidgets import QApplication, QWidget

    from ..errors import ProgramStateError
    from ..formats import read_ply, save_ps, write_ply
    from ..formats.plyfile import PlySession

    class PermutographView(QWidget):
        def __init__(self):
            super().__init__()
            self.spec_name = str(name_or_path)
            self.operators = list(operators) if operators is not None else None
            self.seed = seed
            self.session = make_session(name_or_path, seed=seed,
                                        operators=self.operators)

            # UI chrome state
            self.ui_mode = "main"       # main | file | program | edit | prompt
            self.labels = False
            self.op_colors = True
            self.message = ""           # transient status/error line
            self.pending = None         # (action, ...) awaiting a node click

            # operator editor state
            self.edit_field = None      # ('base',) or ('op', i, j)
            self.edit_buffer = ""
            self.edit_base_before = ""

            # text prompt state (file names, numbers)
            self.prompt_label = ""
            self.prompt_buffer = ""
            self.prompt_kind = None

            title = self.spec_name if self.operators is None \
                else f"{self.spec_name} {' '.join(self.operators)}"
            self.setWindowTitle(f"permuto - {title}")
            self.resize(1000, 860)
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._on_timer)
            self.timer.start(30)

        @property
        def g(self):
            return self.session.graph

        # -- the clock -------------------------------------------------
        def _on_timer(self):
            # only relax freely while running; single-step waits for a key
            if self.ui_mode == "main" and self.session.running:
                self.session.tick()
            elif self.session.program_mode:
                self.session.tick()      # a running program advances on its own
            self.update()

        # ================= painting ==================================
        def paintEvent(self, _ev):
            p = QPainter(self)
            p.fillRect(self.rect(), QColor(*render.BACKGROUND))
            pic_w = self.width() - (260 if self.session.permuto else 0)
            render.paint(self.g, p, pic_w, self.height(),
                         labels=self.labels, op_colors=self.op_colors,
                         program=self.session.program_mode,
                         name_mode=self.session.name_mode)
            if self.session.permuto and self.session.pm is not None:
                render.paint_operator_panel(
                    self.session.pm, p, pic_w + 16, 60, self.height(),
                    active_field=self.edit_field if self.ui_mode == "edit" else None,
                    buffer_text=self.edit_buffer if self.ui_mode == "edit" else None)
            self._paint_chrome(p)
            p.end()

        def _paint_chrome(self, p):
            from PySide6.QtGui import QColor, QFont

            font = QFont("Menlo")
            font.setPixelSize(max(11, int(self.height() * 12 / 320 * 0.7)))
            p.setFont(font)

            # top: the menu line for the current UI mode
            p.setPen(QColor(200, 205, 225))
            p.drawText(12, 22, self._top_line())

            # bottom: the status line, plus any transient message
            p.setPen(QColor(150, 155, 175))
            p.drawText(12, self.height() - 32, self.session.status_line())
            if self.message:
                p.setPen(QColor(255, 210, 140))
                p.drawText(12, self.height() - 14, self.message)
            elif self.ui_mode == "prompt":
                p.setPen(QColor(255, 230, 140))
                p.drawText(12, self.height() - 14,
                           f"{self.prompt_label}{self.prompt_buffer}_")

        def _top_line(self):
            if self.ui_mode == "file":
                return self.session.file_menu_line()
            if self.ui_mode == "program":
                return self.session.program_menu_line()
            if self.ui_mode == "edit":
                return ("editing operators: digits, arrows move, "
                        "Ctrl-Home base, Ctrl-End last, Enter/Esc leave")
            return self.session.menu_line()

        # ================= input =====================================
        def keyPressEvent(self, ev):
            self.message = ""
            if self.ui_mode == "edit":
                self._edit_key(ev)
            elif self.ui_mode == "prompt":
                self._prompt_key(ev)
            elif self.ui_mode == "file":
                self._file_key(ev)
            elif self.ui_mode == "program":
                self._program_key(ev)
            else:
                self._main_key(ev)
            self.update()

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
                self.ui_mode = "program"
            elif k == "e" and s.permuto:
                self._enter_edit()
            elif ev.key() == Qt.Key_Escape:
                self.close()
            elif not s.running:
                s.tick()             # any other key single-steps

        # -- file menu -------------------------------------------------
        def _file_key(self, ev):
            k = ev.text().lower()
            if ev.key() == Qt.Key_Escape or k == "q":
                self.ui_mode = "main"
            elif k == "o":
                self._begin_prompt("PostScript out = ", "ps")
            elif k == "l":
                self._begin_prompt("Load .ply = ", "load")
            elif k == "s":
                self._begin_prompt("Save .ply = ", "save")

        # -- program menu ----------------------------------------------
        def _program_key(self, ev):
            k = ev.text().lower()
            s = self.session
            if ev.key() == Qt.Key_Escape:
                self.ui_mode = "main"
            elif k == "n":
                self.pending = ("kill",)
                self.message = "click a node to kill/repair"
            elif k == "l":
                self.pending = ("break1",)
                self.message = "click the first node of the edge"
            elif k == "c":
                self.pending = ("collapse1",)
                self.message = "click the node to collapse"
            elif k == "u":
                self.pending = ("uncollapse",)
                self.message = "click the node to uncollapse"
            elif k == "s":
                self.pending = ("spa",)
                self.message = "click the start node"
            elif k == "t":
                self._guard(s.start_spta)
                self.ui_mode = "main"
            elif k == "p":
                if self._guard(s.start_par_sum):
                    self.ui_mode = "main"

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

        # -- text prompt (filenames) -----------------------------------
        def _begin_prompt(self, label, kind):
            self.ui_mode = "prompt"
            self.prompt_label = label
            self.prompt_buffer = ""
            self.prompt_kind = kind

        def _prompt_key(self, ev):
            if ev.key() == Qt.Key_Escape:
                self.ui_mode = "main"
            elif ev.key() in (Qt.Key_Return, Qt.Key_Enter):
                self._run_prompt()
                self.ui_mode = "main"
            elif ev.key() == Qt.Key_Backspace:
                self.prompt_buffer = self.prompt_buffer[:-1]
            elif ev.text() and ev.text().isprintable():
                self.prompt_buffer += ev.text()

        def _run_prompt(self):
            name = self.prompt_buffer.strip()
            if not name:
                return
            try:
                if self.prompt_kind == "ps":
                    save_ps(self.g, name)
                    self.message = f"wrote {name}"
                elif self.prompt_kind == "save":
                    self._save_ply(name)
                    self.message = f"saved {name}"
                elif self.prompt_kind == "load":
                    self._load_ply(name)
                    self.message = f"loaded {name}"
            except (PermutoError, OSError) as exc:
                self.message = str(exc)

        def _save_ply(self, path):
            pm = self.session.pm
            sess = PlySession(
                graph=self.g, permuto=self.session.permuto,
                base=pm.base if pm else "",
                optable=[list(r) for r in pm.optable] if pm else [],
                last_edit_line=pm.last_edit_line if pm else 0)
            write_ply(path, sess)

        def _load_ply(self, path):
            loaded = read_ply(path)
            if loaded.pm is not None:
                self.session = Session(graph=loaded.graph, mode=Mode.PERMUTO,
                                       pm=loaded.pm)
            else:
                self.session = Session(graph=loaded.graph, mode=Mode.POLYTOP)

        # -- mouse (node picking for program actions) ------------------
        def mousePressEvent(self, ev):
            pic_w = self.width() - (260 if self.session.permuto else 0)
            pts = render.project(self.g, pic_w, self.height())
            pos = ev.position()
            best, bestd = None, 1e18
            for num, (x, y, _z) in pts.items():
                d = (x - pos.x()) ** 2 + (y - pos.y()) ** 2
                if d < bestd:
                    best, bestd = num, d
            if best is not None and self.pending is not None:
                self._apply_pending(best)
            self.update()

        def _apply_pending(self, node):
            s = self.session
            action = self.pending[0]
            pm = s.pm
            if action == "kill":
                self.g.nodes[node].state.dead = not self.g.nodes[node].state.dead
                self.pending = None
                self.ui_mode = "main"
            elif action == "break1":
                self.pending = ("break2", node)
                self.message = "click the second node of the edge"
            elif action == "break2":
                self._toggle_broken(self.pending[1], node)
                self.pending = None
                self.ui_mode = "main"
            elif action == "collapse1":
                self.pending = ("collapse2", node)
                self.message = "click the node to collapse it onto"
            elif action == "collapse2":
                self._guard(lambda: pm.collapse(self.g, self.pending[1], node))
                self.pending = None
                self.ui_mode = "main"
            elif action == "uncollapse":
                self._guard(lambda: pm.uncollapse(self.g, node))
                self.pending = None
                self.ui_mode = "main"
            elif action == "spa":
                self._guard(lambda: s.start_spa(node))
                self.pending = None
                self.ui_mode = "main"

        def _toggle_broken(self, n1, n2):
            from ..core.pm import find_link

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

    app = QApplication.instance() or QApplication([])
    view = PermutographView()
    view.show()
    return app.exec()
