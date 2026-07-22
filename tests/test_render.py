"""Smoke test for the offscreen renderer (skipped if PySide6 is unavailable)."""

import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from conftest import modula_dir  # noqa: E402

from permuto.core import intvector as iv  # noqa: E402
from permuto.core import layout  # noqa: E402
from permuto.core.graph import Graph  # noqa: E402
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
