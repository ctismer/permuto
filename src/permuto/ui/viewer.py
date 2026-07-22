"""Interactive PySide6 viewer: the port of the ``polytop.mod`` main loop as a
Qt widget — relax on a timer, project to 2-D, spin, and draw.

Keys:  s = toggle spin   c = toggle calculating   q = quit
"""

from __future__ import annotations

from ..core import intvector as iv
from ..core import layout
from ..core.graph import Graph
from . import render


def _load(name_or_path, seed: int) -> Graph:
    import os

    p = str(name_or_path)
    if not os.path.exists(p):
        root = os.path.join(os.path.dirname(__file__), "..", "..", "..")
        p = os.path.join(root, "legacy", "modula", "nod", p)
        if not p.endswith(".nod"):
            p += ".nod"
    return Graph.load_nod(p, dimensions=iv.MAXDIMEN, seed=seed)


def run(name_or_path, seed: int = 1) -> int:
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtGui import QColor, QPainter
    from PySide6.QtWidgets import QApplication, QWidget

    class PermutographView(QWidget):
        def __init__(self, g: Graph, alg: str = "rubber"):
            super().__init__()
            self.g = g
            self.alg = alg
            self.spinning = True
            self.calculating = True
            self.setWindowTitle("permuto")
            self.resize(800, 800)
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._step)
            self.timer.start(30)

        def _step(self):
            layout.relax_step(self.g, alg=self.alg,
                              calculating=self.calculating, spinning=self.spinning)
            self.update()

        def paintEvent(self, _ev):
            p = QPainter(self)
            p.fillRect(self.rect(), QColor(18, 18, 28))
            render.paint(self.g, p, self.width(), self.height())
            p.end()

        def keyPressEvent(self, ev):
            k = ev.text().lower()
            if k == "s":
                self.spinning = not self.spinning
            elif k == "c":
                self.calculating = not self.calculating
            elif k == "q":
                self.close()

    app = QApplication.instance() or QApplication([])
    view = PermutographView(_load(name_or_path, seed))
    view.show()
    return app.exec()
