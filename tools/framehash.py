"""Hash a fixed set of rendered frames, so a change can prove it left the
picture alone.

Run it before a change and after it, and diff the two outputs::

    python tools/framehash.py > /tmp/before.txt
    ...edit...
    python tools/framehash.py | diff /tmp/before.txt -

The cases cover what actually varies in the drawing code: both window shapes,
every name mode, a graph part-way through SPA (line states, direction discs, a
broken edge, a dead node, an active one), a plain .nod graph and the 812-node
geodesic.  A refactor of `permuto.scene` or `permuto.ui.render` that is meant to
be invisible has to come out identical here; one that is meant to change the
look should change exactly the frames you expect.

This is not a test.  It is deliberately a tool: the frames are a judgement
call about what is worth watching, and the "expected" side is whatever the
code produced before you touched it.  See docs/HANDOVER.md, "How to read a
coverage hole", for why both halves matter.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtGui import QImage, QPainter                        # noqa: E402
from PySide6.QtWidgets import QApplication                        # noqa: E402

from permuto.core import layout, spa                              # noqa: E402
from permuto.core.graph import Graph                              # noqa: E402
from permuto.loader import load_graph                             # noqa: E402
from permuto.ui import render                                     # noqa: E402


def _frame(g, width, height, **kw) -> str:
    img = QImage(width, height, QImage.Format.Format_ARGB32)
    img.fill(0)
    painter = QPainter(img)
    render.paint(g, painter, width, height, **kw)
    painter.end()
    return hashlib.sha256(img.constBits().tobytes()).hexdigest()[:16]


def _permutograph(steps: int = 120) -> Graph:
    g = Graph.build("1234", ["12", "+", "23", "+", "34"], seed=1)
    for _ in range(steps):
        layout.relax_step(g, alg=layout.Algorithm.RUBBER)
    return g


def _mid_spa() -> Graph:
    """Everything the program mode can put on screen at once."""
    g = _permutograph()
    spa.init_spa(g, 1)
    for _ in range(6):
        spa.shortest_path(g)
    g.nodes[3].state.dead = True          # a hollow ball with a black rim
    g.nodes[5].state.active = True        # and the white ring
    g.nodes[2].links[0].broken = True     # a black edge, and no digit on it
    return g


CASES = {
    "the window the viewer opens with": lambda: _frame(
        _permutograph(), 873, 860, op_colors=True, name_mode=2),
    "polytop mode, full width": lambda: _frame(
        _permutograph(), 1000, 860, name_mode=1),
    "square": lambda: _frame(_permutograph(), 700, 700),
    "tall and narrow": lambda: _frame(_permutograph(), 300, 900),
    "short and wide": lambda: _frame(_permutograph(), 900, 300),
    "well past the mark reference": lambda: _frame(
        _permutograph(), 1800, 1800, op_colors=True, name_mode=2),
    "labels": lambda: _frame(_permutograph(), 700, 700, labels=True),
    "operator colours, no names": lambda: _frame(
        _permutograph(), 700, 700, op_colors=True),
    "node numbers": lambda: _frame(
        _permutograph(), 700, 700, op_colors=True, name_mode=1),
    "mid-SPA": lambda: _frame(
        _mid_spa(), 700, 700, op_colors=True, program=True),
    "mid-SPA, small": lambda: _frame(
        _mid_spa(), 240, 240, op_colors=True, program=True),
    "a .nod graph": lambda: _frame(load_graph("tetraede", seed=1), 500, 500),
    "the 812-node geodesic": lambda: _frame(
        load_graph("ikosa9", seed=1), 800, 800, labels=True),
}


def main() -> int:
    QApplication.instance() or QApplication([])
    for name, case in CASES.items():
        print(f"{case()}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
