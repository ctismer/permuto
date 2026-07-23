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


def load_graph(name_or_path, *, dimensions: int = iv.MAXDIMEN,
               seed: int = 0) -> Graph:
    """Resolve a name or file to a Graph. Prefer a ``.pgd`` (gives permutation
    labels + operator colours); fall back to plain ``.nod`` topology."""
    p = str(name_or_path)
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
    if not candidates:
        raise FileNotFoundError(f"no .pgd/.nod found for {name_or_path!r}")
    chosen = candidates[0]
    if chosen.endswith(".pgd"):
        return Graph.from_pgd(chosen, dimensions=dimensions, seed=seed)
    return Graph.load_nod(chosen, dimensions=dimensions, seed=seed)


def run(name_or_path, seed: int = 1) -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QColor, QFont, QPainter
    from PySide6.QtWidgets import QApplication, QWidget

    class PermutographView(QWidget):
        def __init__(self, name):
            super().__init__()
            self.name = str(name)
            self.seed = seed
            self.alg_i = 0
            self.spinning = True
            self.calculating = True
            self.labels = False
            self.op_colors = True
            self.g = load_graph(name, seed=self.seed)
            self.setWindowTitle(f"permuto — {self.name}")
            self.resize(820, 860)
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._step)
            self.timer.start(30)

        @property
        def alg(self):
            return layout.ALGORITHMS[self.alg_i]

        def _step(self):
            layout.relax_step(self.g, alg=self.alg,
                              calculating=self.calculating, spinning=self.spinning)
            self.update()

        def paintEvent(self, _ev):
            p = QPainter(self)
            p.fillRect(self.rect(), QColor(18, 18, 28))
            render.paint(self.g, p, self.width(), self.height(),
                         labels=self.labels, op_colors=self.op_colors)
            p.setPen(QColor(150, 155, 175))
            p.setFont(QFont("Menlo", 10))
            flags = f"alg={self.alg}  dim={self.g.dimensions}  " \
                    f"spin={'on' if self.spinning else 'off'}  " \
                    f"calc={'on' if self.calculating else 'off'}  " \
                    f"labels={'on' if self.labels else 'off'}  " \
                    f"opcol={'on' if self.op_colors else 'off'}"
            p.drawText(12, 22, f"{self.name}: {self.g.nnodes} nodes")
            p.drawText(12, 40, flags)
            p.drawText(12, self.height() - 14,
                       "keys: s spin  c calc  a alg  l labels  o opcol  r reset  q quit")
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
            elif k == "r":
                self.seed += 1
                self.g = load_graph(self.name, seed=self.seed)
            elif k == "q":
                self.close()
            self.update()

    app = QApplication.instance() or QApplication([])
    view = PermutographView(name_or_path)
    view.show()
    return app.exec()
