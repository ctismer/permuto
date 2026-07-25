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


def test_saving_and_loading_a_pms_in_the_running_viewer(qapp, tmp_path):
    """Start bare, save the session, load a different one, load the first back
    -- all through the viewer's own F->S / F->L, painting after each."""
    captured = {}

    def drive(view):
        for _ in range(30):
            view.session.tick()
        view._save_session(str(tmp_path / "pgl4.pms"))
        first_nodes = view.g.nnodes

        # a different graph, written as .pms, then loaded via the viewer
        from permuto.core.graph import Graph
        from permuto.formats import PlySession, write_pms
        other = Graph.build("123", ["12", "+", "23"], seed=1)
        write_pms(tmp_path / "other.pms",
                  PlySession(graph=other, mode="permuto", base="123"))

        view._load_session(str(tmp_path / "other.pms"))
        _repaint(view)
        loaded_nodes = view.g.nnodes

        view._load_session(str(tmp_path / "pgl4.pms"))     # first one back
        _repaint(view)
        captured.update(first=first_nodes, loaded=loaded_nodes,
                        reloaded=view.g.nnodes)
        view.close()

    viewer.run("1234", operators=["12", "+", "23", "+", "34"], _drive=drive)
    assert captured["first"] == 24 and captured["loaded"] == 6
    assert captured["reloaded"] == 24


def test_viewer_always_saves_text_pms_never_binary(qapp, tmp_path):
    """The save prompt says .pms, and .ply is read-only legacy, so the viewer
    must write text whatever extension is typed -- no hidden switch to binary."""
    captured = {}

    def drive(view):
        captured["bare"] = view._save_session(str(tmp_path / "xanti")).name
        captured["ply"] = view._save_session(str(tmp_path / "foo.ply")).name
        # the file written for a .ply name must still be text
        captured["is_text"] = (tmp_path / "foo.pms").read_bytes()[:15] == \
            b"permuto session"
        view.close()

    viewer.run("1234", operators=["12", "+", "23", "+", "34"], _drive=drive)
    assert captured["bare"] == "xanti.pms"
    assert captured["ply"] == "foo.pms"
    assert captured["is_text"]


def test_loading_a_session_saved_at_a_different_scale_fills_the_view(qapp, tmp_path):
    """A .pms saved at another fixed-point scale (e.g. the old NORM=4096) must
    show at full size at once, not microscopic until relaxation catches up."""
    from permuto.core import intvector as iv
    from permuto.core import layout
    from permuto.core.graph import Graph
    from permuto.formats import PlySession, write_pms
    from permuto.ui import render

    saved = iv.NORM
    try:
        iv.NORM = 4096                       # save at the old scale
        g = Graph.build("1234", ["12", "+", "23", "+", "34"], seed=1)
        for _ in range(80):
            layout.relax_step(g, alg="rubber")
        write_pms(tmp_path / "old.pms", PlySession(graph=g, mode="permuto", base="1234"))
    finally:
        iv.NORM = saved                      # load at the current (large) scale

    captured = {}

    def drive(view):
        view._load_session(str(tmp_path / "old.pms"))
        pts = render.project(view.g, 740, 800)
        xs = [p[0] for p in pts.values()]
        ys = [p[1] for p in pts.values()]
        captured["spread"] = max(max(xs) - min(xs), max(ys) - min(ys))
        view.close()

    viewer.run("1234", operators=["12", "+", "23", "+", "34"], _drive=drive)
    assert captured["spread"] > 100, "loaded graph is a dot, not renormalized"


def test_starting_directly_on_a_session_file(qapp, tmp_path):
    """`permuto show <name>` resumes a saved session, finding <name>.pms when a
    bare name is given (symmetric with save appending .pms)."""
    from permuto.core.graph import Graph
    from permuto.formats import PlySession, write_pms

    g = Graph.build("1234", ["12", "+", "23", "+", "34"], seed=1)
    write_pms(tmp_path / "sess.pms",
              PlySession(graph=g, mode="permuto", base="1234", iteration=42))
    captured = {}

    def drive(view):
        captured["nodes"] = view.g.nnodes
        captured["iter"] = view.session.iteration
        captured["pm"] = view.session.pm is not None
        _repaint(view)
        view.close()

    # bare name (no extension) must resolve to sess.pms
    viewer.run(str(tmp_path / "sess"), _drive=drive)
    assert captured["nodes"] == 24
    assert captured["iter"] == 42
    assert captured["pm"] is True


def test_freshly_built_graph_fills_the_view_not_a_dot(qapp):
    """A just-built permutograph seeds its coordinates from the topology (tiny),
    which at the large NORM would project to a single dot; the viewer must
    normalize the initial picture so it fills the view straight away."""
    from permuto.ui import render

    captured = {}

    def drive(view):
        view.resize(900, 800)
        pts = render.project(view.g, 640, 800)
        xs = [p[0] for p in pts.values()]
        ys = [p[1] for p in pts.values()]
        captured["spread"] = max(max(xs) - min(xs), max(ys) - min(ys))
        view.close()

    viewer.run("1234", operators=["12", "+", "23", "+", "34"], _drive=drive)
    assert captured["spread"] > 100, "startup graph collapsed to a dot"


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
