"""Interactive PySide6 viewer: the ``polytop.mod`` main loop as a Qt widget --
relax on a timer, project to 2-D, spin, and draw.

Keys:
    s  spin on/off       c  calculating on/off     a  next algorithm
    l  node labels       o  operator colours        r  reset (re-randomise)
    q  quit
"""

from __future__ import annotations

import os

from ..core import intvector as iv
from ..core import layout
from ..core.graph import Graph
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
    """Resolve a spec to a Graph.

    * with ``operators`` given, build the permutograph from base + operators
      directly (the ``/PG`` idea: no file needed);
    * otherwise resolve a name or file, preferring a ``.pgd`` (permutation
      labels + operator colours) over plain ``.nod`` topology.
    """
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


def run(name_or_path, seed: int = 1, operators=None) -> int:
    from PySide6.QtCore import QPointF, QTimer
    from PySide6.QtGui import QColor, QFont, QPainter
    from PySide6.QtWidgets import QApplication, QWidget

    from ..core import spa

    class PermutographView(QWidget):
        def __init__(self, name):
            super().__init__()
            self.name = str(name)
            self.operators = list(operators) if operators is not None else None
            self.seed = seed
            self.alg_i = 0
            self.spinning = True
            self.calculating = True
            self.labels = False
            self.op_colors = True
            self.program = False       # SPA/ParSum program mode
            self.phase = "off"         # off | spa | parsum | done
            self.start = 1
            self._pcount = 0
            self.g = load_graph(name, seed=self.seed, operators=self.operators)
            title = self.name if self.operators is None \
                else f"{self.name} {' '.join(self.operators)}"
            self.setWindowTitle(f"permuto — {title}")
            self.resize(820, 860)
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._step)
            self.timer.start(30)

        @property
        def alg(self):
            return layout.ALGORITHMS[self.alg_i]

        # -- program (SPA / ParSum) ------------------------------------
        def _start_program(self):
            self.start = min(self.g.nodes) if self.start not in self.g.nodes else self.start
            spa.init_spa(self.g, self.start)
            self.phase = "spa"
            self._pcount = 0

        def _advance_program(self):
            self._pcount += 1
            if self._pcount % 3:      # slow enough to watch
                return
            if self.phase == "spa":
                if not spa.shortest_path(self.g):
                    self.phase = "parsum"
                    spa.init_par_sum(self.g)
            elif self.phase == "parsum":
                if not spa.par_sum(self.g):
                    self.phase = "done"

        def _step(self):
            if self.program:
                if self.spinning and self.g.dimensions >= 3:
                    layout.spin(self.g)      # keep rotating, freeze relaxation
                self._advance_program()
            else:
                layout.relax_step(self.g, alg=self.alg,
                                  calculating=self.calculating, spinning=self.spinning)
            self.update()

        # -- input -----------------------------------------------------
        def mousePressEvent(self, ev):
            pts = render.project(self.g, self.width(), self.height())
            pos = ev.position()
            best, bestd = None, 1e18
            for num, (x, y, _z) in pts.items():
                d = (x - pos.x()) ** 2 + (y - pos.y()) ** 2
                if d < bestd:
                    best, bestd = num, d
            if best is not None:
                self.start = best
                if self.program:
                    self._start_program()
                self.update()

        def paintEvent(self, _ev):
            p = QPainter(self)
            p.fillRect(self.rect(), QColor(18, 18, 28))
            render.paint(self.g, p, self.width(), self.height(),
                         labels=self.labels, op_colors=self.op_colors,
                         program=self.program)
            p.setPen(QColor(150, 155, 175))
            p.setFont(QFont("Menlo", 10))
            mode = f"program={self.phase} start={self.start}" if self.program \
                else f"alg={self.alg} dim={self.g.dimensions}"
            flags = f"{mode}  spin={'on' if self.spinning else 'off'}  " \
                    f"labels={'on' if self.labels else 'off'}  " \
                    f"opcol={'on' if self.op_colors else 'off'}"
            p.drawText(12, 22, f"{self.name}: {self.g.nnodes} nodes")
            p.drawText(12, 40, flags)
            p.drawText(12, self.height() - 14,
                       "keys: s spin  c calc  a alg  l labels  o opcol  "
                       "p program(SPA)  click=start  r reset  q quit")
            p.end()

        def keyPressEvent(self, ev):
            k = ev.text().lower()
            if k == "s":
                self.spinning = not self.spinning
            elif k == "c":
                self.calculating = not self.calculating
            elif k == "a":
                self.alg_i = (self.alg_i + 1) % len(layout.ALGORITHMS)
            elif k == "l":
                self.labels = not self.labels
            elif k == "o":
                self.op_colors = not self.op_colors
            elif k == "p":
                self.program = not self.program
                if self.program:
                    self._start_program()
                else:
                    self.phase = "off"
            elif k == "r":
                self.seed += 1
                self.program = False
                self.phase = "off"
                self.g = load_graph(self.name, seed=self.seed,
                                    operators=self.operators)
            elif k == "q":
                self.close()
            self.update()

    app = QApplication.instance() or QApplication([])
    view = PermutographView(name_or_path)
    view.show()
    return app.exec()
