"""Smoke test for the offscreen renderer (skipped if PySide6 is unavailable)."""

import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from conftest import modula_dir  # noqa: E402

from permuto.core import intvector as iv  # noqa: E402
from permuto.core import layout  # noqa: E402
from permuto.core.graph import Graph, Node  # noqa: E402
from permuto.ui import render  # noqa: E402


def test_import_viewer():
    import permuto.ui.viewer  # noqa: F401  (import must not raise)


def test_render_produces_nonempty_image():
    g = Graph.load_nod(modula_dir() / "nod" / "tetraede.nod",
                       dimensions=iv.MAXDIMEN, seed=1)
    for _ in range(200):
        layout.relax_step(g, alg="rubber")
    img = render.render_image(g, 200, 200)
    assert img.width() == 200 and img.height() == 200
    bg = img.pixel(0, 0)
    drawn = any(img.pixel(x, y) != bg
                for x in range(0, 200, 7) for y in range(0, 200, 7))
    assert drawn, "nothing was drawn"


def test_projection_is_isotropic_so_shapes_do_not_distort():
    """Equal scale in x and y, or a sphere stops looking like a sphere once the
    operator panel makes the picture area non-square.  A unit step along axis 0
    must move the same number of pixels as a unit step along axis 1, whatever
    the window shape."""
    g = Graph()
    g.nnodes = 2
    g.dimensions = 3
    g.nodes[1] = Node(num=1, pos=[iv.NORM, 0, 0, 0, 0, 0, 0, 0])
    g.nodes[2] = Node(num=2, pos=[0, iv.NORM, 0, 0, 0, 0, 0, 0])
    for w, h in ((900, 300), (300, 900), (700, 700)):
        pts = render.project(g, w, h)
        dx = abs(pts[1][0] - w // 2)      # x offset of the pos[0]=NORM node
        dy = abs(pts[2][1] - h // 2)      # y offset of the pos[1]=NORM node
        assert dx == dy, f"anisotropic at {w}x{h}: {dx} != {dy}"


def test_operator_panel_lists_the_base_and_operators():
    from permuto.ui.viewer import make_session

    s = make_session("1234", operators=["12", "+", "23", "+", "34"])
    rows = render.operator_panel_rows(s.pm)
    assert rows[0] == ("Base", "1234", ("base",))
    values = {v for _, v, f in rows if f and f[0] == "op"}
    assert {"12", "23", "34"} <= values


def test_viewer_builds_without_a_display():
    """The whole viewer construction path (session + panel + first paint) must
    work headless, so this stays covered without a human at the screen."""
    from PySide6.QtGui import QImage, QPainter
    from permuto.ui.viewer import make_session

    s = make_session("11111112",
                     operators=["1234", "+", "5678", "+", "18", "27", "+", "36", "45"])
    assert s.graph.nnodes == 8
    for _ in range(50):
        s.tick()
    img = QImage(700, 600, QImage.Format.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    render.paint(s.graph, p, 500, 600, op_colors=True, name_mode=2)
    render.paint_operator_panel(s.pm, p, 520, 60, 600)
    p.end()
    bg = img.pixel(0, 0)
    assert any(img.pixel(x, y) != bg
               for x in range(0, 700, 15) for y in range(0, 600, 15))
