"""The real Qt widgets, driven through every UI mode.

These would have caught the _paint_chrome crash: the earlier tests only called
render.paint() directly and never the QWidget.paintEvent that actually runs
when you launch the viewer.  Here the widget is built and its paintEvent fired
synchronously (via repaint()) in each mode; a caught paint exception is recorded
on the widget, so any AttributeError/KeyError in the paint path fails the test
instead of crashing at shutdown.
"""

import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from permuto.ui import viewer  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _repaint(view):
    view.resize(900, 800)
    view._paint_error = None
    view.grab()             # renders the widget -> fires paintEvent synchronously
    if view._paint_error is not None:
        raise view._paint_error


def test_permutograph_view_paints_in_every_mode(qapp):
    captured = {}

    def drive(view):
        # main
        _repaint(view)
        # program menu (forces node numbers on)
        view.ui_mode = "program"
        _repaint(view)
        # a running SPA program
        view.session.start_spa(1)
        for _ in range(20):
            view.session.tick()
        _repaint(view)
        # operator editor open
        view.ui_mode = "edit"
        view.edit_field = ("base",)
        view.edit_buffer = view.session.pm.base
        _repaint(view)
        # a numeric prompt
        view.ui_mode = "prompt"
        view.prompt_kind = "node"
        from permuto.ui.prompt import single
        view.prompt = single("StartNode=")
        view.prompt.type_char("1")
        _repaint(view)
        # SelectCard over a node's neighbours
        view.ui_mode = "select"
        n = 1
        view.select = {"node": n, "action": "break2",
                       "items": list(view.g.nodes[n].links), "pos": 0}
        _repaint(view)
        captured["error"] = view._paint_error
        view.close()

    viewer.run("pgl4", seed=1, _drive=drive)
    assert captured["error"] is None, f"paint raised: {captured['error']!r}"


def test_polytop_view_paints_a_plain_nod_graph(qapp):
    captured = {}

    def drive(view):
        _repaint(view)
        view.ui_mode = "program"
        _repaint(view)
        captured["error"] = view._paint_error
        view.close()

    viewer.run("wuerfel", seed=1, _drive=drive)
    assert captured["error"] is None, f"paint raised: {captured['error']!r}"


def test_permutograph_built_from_base_and_operators_paints(qapp):
    captured = {}

    def drive(view):
        _repaint(view)
        captured["error"] = view._paint_error
        view.close()

    viewer.run("11111112",
               operators=["1234", "+", "5678", "+", "18", "27", "+", "36", "45"],
               _drive=drive)
    assert captured["error"] is None, f"paint raised: {captured['error']!r}"


def test_iridium_view_paints_through_build_and_run(qapp):
    captured = {}

    def drive(view):
        # build phase
        _repaint(view)
        # force the network fully built and run a step
        while not view.iri.built:
            view._tick()
        view.phase = "run"
        view.iri.transmit("900", "009")
        view.iri.step()
        _repaint(view)
        # a transmit prompt open
        view._begin_prompt("transmit", ["Node1", "Node2", "Repeat"])
        view.prompt.type_char("9")
        _repaint(view)
        captured["error"] = view._paint_error
        view.close()

    viewer.run_iridium(_drive=drive)
    assert captured["error"] is None, f"paint raised: {captured['error']!r}"
