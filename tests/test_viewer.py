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
    img = view.grab().toImage()   # renders the widget -> fires paintEvent
    if view._paint_error is not None:
        raise view._paint_error
    return img


def _press(view, ch):
    """Send a key the way a user would, through the widget's own handler."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    special = {"esc": Qt.Key_Escape, "enter": Qt.Key_Return,
               "back": Qt.Key_Backspace, "space": Qt.Key_Space,
               "up": Qt.Key_Up, "down": Qt.Key_Down,
               "home": Qt.Key_Home, "end": Qt.Key_End}
    if ch in special:
        view.keyPressEvent(QKeyEvent(QKeyEvent.KeyPress, special[ch],
                                     Qt.NoModifier, ""))
    else:
        view.keyPressEvent(QKeyEvent(QKeyEvent.KeyPress, ord(ch.upper()),
                                     Qt.NoModifier, ch))


def _node_pixels(view, img):
    """The colour drawn at each node's centre, as the user sees it."""
    from permuto.ui import render

    pic_w = view.width() - (260 if view.session.permuto else 0)
    out = []
    for x, y, _z in render.project(view.g, pic_w, view.height()).values():
        if 0 <= x < img.width() and 0 <= y < img.height():
            out.append(img.pixelColor(int(x), int(y)))
    return out


def test_permutograph_view_paints_in_every_mode(qapp):
    captured = {}

    def drive(view):
        # main
        _repaint(view)
        # program menu (forces node numbers on)
        view.ui_mode = viewer.UiMode.PROGRAM
        _repaint(view)
        # a running SPA program
        view.session.start_spa(1)
        for _ in range(20):
            view.session.tick()
        _repaint(view)
        # operator editor open
        view.ui_mode = viewer.UiMode.MAIN
        _press(view, "e")                     # into the operator editor
        _repaint(view)
        # a numeric prompt
        view.ui_mode = viewer.UiMode.PROMPT
        view.prompt_kind = viewer.PromptKind.NODE
        from permuto.ui.prompt import single
        view.prompt = single("StartNode=")
        view.prompt.type_char("1")
        _repaint(view)
        # SelectCard over a node's neighbours
        view.ui_mode = viewer.UiMode.SELECT
        n = 1
        view.select = viewer.Selection(node=n, action=viewer.NodeAction.BREAK,
                                       items=list(view.g.nodes[n].links))
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


def _spread(view, width=640, height=800):
    from permuto.ui import render

    pts = render.project(view.g, width, height)
    xs = [p[0] for p in pts.values()]
    ys = [p[1] for p in pts.values()]
    return max(max(xs) - min(xs), max(ys) - min(ys))


def test_editing_the_base_leaves_a_full_size_picture(qapp):
    """Typing a new base in the operator editor rebuilds the graph, whose fresh
    coordinates come from the link numbers -- a dot unless the rebuild frames
    them.  Drives the real editor keys, 1234 -> 12345."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    def key(ch):
        return QKeyEvent(QKeyEvent.KeyPress, ord(ch.upper()), Qt.NoModifier, ch)

    captured = {}

    def drive(view):
        view.resize(900, 800)
        view.keyPressEvent(key("e"))                  # into the editor
        assert view.ui_mode is viewer.UiMode.EDIT
        for _ in range(len(view.session.pm.base)):    # clear the field
            view.keyPressEvent(QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Backspace,
                                         Qt.NoModifier, "\b"))
        for ch in "12345":
            view.keyPressEvent(key(ch))
        view.keyPressEvent(QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Return,
                                     Qt.NoModifier, "\r"))
        captured["mode"] = view.ui_mode
        captured["nodes"] = view.g.nnodes
        captured["spread"] = _spread(view)
        view.close()

    viewer.run("1234", operators=["12", "+", "23", "+", "34"], _drive=drive)
    assert captured["mode"] is viewer.UiMode.MAIN
    assert captured["nodes"] == 120, "base 12345 must give 5! nodes"
    assert captured["spread"] > 100, "rebuilt graph collapsed to a dot"


def test_hurry_computes_many_iterations_per_frame(qapp):
    """HurryUp trades looking for computing: it drops the spin while
    calculating, so it must buy iterations in return -- one timer tick runs a
    whole checkpoint's worth instead of a single step."""
    captured = {}

    def frames(view, n=10):
        before = view.session.iteration
        for _ in range(n):
            view._on_timer()
        return view.session.iteration - before

    def drive(view):
        view.session.running = True
        view.session.hurry_up = False
        captured["plain"] = frames(view)
        view.session.hurry_up = True
        captured["hurried"] = frames(view)
        view.close()

    viewer.run("1234", operators=["12", "+", "23", "+", "34"], _drive=drive)
    assert captured["plain"] == 10, "one iteration per frame without hurry"
    assert captured["hurried"] > 3 * captured["plain"], \
        "hurry only cost the spin and bought nothing"


def test_escape_asks_before_leaving(qapp):
    """``UserWantsToExit`` -- ESC puts the question up, "n" goes back, and the
    file menu's (Q)uit asks the same way."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    from permuto.session import EXIT_QUESTION

    def key(ch, code=None):
        return QKeyEvent(QKeyEvent.KeyPress, code or ord(ch.upper()),
                         Qt.NoModifier, ch)

    esc = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier, "\x1b")
    captured = {}

    def drive(view):
        view.keyPressEvent(esc)
        captured["asked"] = (view.ui_mode, view.session.top_line(view.ui_mode))
        view.keyPressEvent(key("n"))                # not yet
        captured["after_no"] = view.ui_mode
        view.keyPressEvent(key("f"))               # file menu -> (Q)uit
        view.keyPressEvent(key("q"))
        captured["file_quit"] = view.ui_mode
        view.keyPressEvent(key("j"))               # "ja" counts, as in 1995
        captured["closed"] = not view.isVisible()

    viewer.run("1234", operators=["12", "+", "23", "+", "34"], _drive=drive)
    assert captured["asked"] == (viewer.UiMode.CONFIRM, EXIT_QUESTION)
    assert captured["after_no"] is viewer.UiMode.MAIN, "'n' must not quit"
    assert captured["file_quit"] is viewer.UiMode.CONFIRM, "(Q)uit must ask too"
    assert captured["closed"]


def test_iridium_escape_asks_before_leaving(qapp):
    from permuto.session import EXIT_QUESTION

    captured = {}

    def drive(view):
        _press(view, "q")
        captured["asked"] = (view.ui_mode, view.message)
        _press(view, "x")                     # not a yes
        captured["after_no"] = view.ui_mode
        captured["still_open"] = view.isVisible()
        view.close()

    viewer.run_iridium(_drive=drive)
    assert captured["asked"] == (viewer.UiMode.CONFIRM, EXIT_QUESTION)
    assert captured["after_no"] is viewer.UiMode.MAIN
    assert captured["still_open"]


def test_pressing_n_walks_the_label_modes_the_user_can_use(qapp):
    """N cycles none -> node# -> perm -> (display, once SPA filled it) and back.
    Driven through the widget, because that is where the user meets it."""
    captured = {}

    def drive(view):
        captured["before"] = [view.session.name_mode
                              for _ in range(4) if not _press(view, "n")]
        view.session.start_spa(1)
        captured["after"] = [view.session.name_mode
                             for _ in range(4) if not _press(view, "n")]
        view.close()

    viewer.run("1234", operators=["12", "+", "23", "+", "34"], _drive=drive)
    assert captured["before"] == [1, 2, 0, 1], "display mode has nothing to show"
    assert 3 in captured["after"], "after SPA the display mode must be offered"


def test_the_picture_shows_coloured_balls_with_black_labels(qapp):
    """What the eye is supposed to get out of the window: every ball carries
    its own colour (the class its permutation belongs to) and its label in
    black, inside the ball."""
    captured = {}

    def drive(view):
        _press(view, "n")            # node numbers
        _press(view, "n")            # permutation strings
        img = _repaint(view)
        balls = _node_pixels(view, img)
        captured["hues"] = {c.hue() for c in balls}
        captured["black_balls"] = [c.name() for c in balls
                                   if (c.red(), c.green(), c.blue()) == (0, 0, 0)]
        # the label is black, and it is *inside* the ball
        from permuto.ui import render
        pic_w = view.width() - 260
        pts = render.project(view.g, pic_w, view.height())
        r = int(render._scaled(view.height(), 12))
        box = range(-r + 1, r)
        captured["labelled"] = sum(
            any(img.pixelColor(int(x) + dx, int(y) + dy).lightness() < 60
                for dx in box for dy in box)
            for x, y, _z in pts.values())
        captured["nodes"] = view.g.nnodes
        view.close()

    viewer.run("1234", operators=["12", "+", "23", "+", "34"], _drive=drive)
    assert len(captured["hues"]) >= 4, "base 1234 has four colour classes"
    assert captured["black_balls"] == [], "a black ball is an invisible node"
    assert captured["labelled"] == captured["nodes"], "labels are not in the balls"


def test_a_big_geodesic_has_no_invisible_nodes(qapp):
    """ikosa9 runs past the 16-colour palette (812 nodes, colours to 34); naive
    wrapping lands on black, which on the dark background is a hole."""
    captured = {}

    def drive(view):
        for _ in range(30):
            view.session.tick()
        img = _repaint(view)
        captured["black"] = [c for c in _node_pixels(view, img)
                             if (c.red(), c.green(), c.blue()) == (0, 0, 0)]
        view.close()

    viewer.run("ikosa9", seed=1, _drive=drive)
    assert captured["black"] == [], f"{len(captured['black'])} balls vanished"


def test_running_spa_from_the_program_menu_marks_the_path(qapp):
    """P, S, node number, Enter -- the whole keyboard route the original had,
    ending in a picture whose wave edges carry their direction discs."""
    captured = {}

    def drive(view):
        _press(view, "p")
        _press(view, "s")
        _press(view, "1")
        _press(view, "enter")
        for _ in range(40):
            view.session.tick()
        img = _repaint(view)
        from permuto.core.graph import L_INPUT, L_OUTPUT
        from permuto.ui import render
        pic_w = view.width() - 260
        pts = render.project(view.g, pic_w, view.height())
        greens = 0
        for nd in view.g.ordered():
            for idx, j in enumerate(nd.links):
                if j <= nd.num or nd.state.lines[idx] not in (L_INPUT, L_OUTPUT):
                    continue
                xi, yi, _ = pts[nd.num]
                xj, yj, _ = pts[j]
                if nd.state.lines[idx] == L_INPUT:
                    qx, qy = (5 * xi + xj) / 6, (5 * yi + yj) / 6
                else:
                    qx, qy = (5 * xj + xi) / 6, (5 * yj + yi) / 6
                greens += max(img.pixelColor(int(qx) + dx, int(qy) + dy).green()
                              for dx in (-1, 0, 1) for dy in (-1, 0, 1)) > 100
        captured["discs"] = greens
        captured["mode"] = view.ui_mode
        view.close()

    viewer.run("1234", operators=["12", "+", "23", "+", "34"], _drive=drive)
    assert captured["mode"] is viewer.UiMode.MAIN, \
        "the menu must close after the program starts"
    assert captured["discs"] > 10, "the wave edges carry no direction discs"


def test_polytop_view_paints_a_plain_nod_graph(qapp):
    captured = {}

    def drive(view):
        _repaint(view)
        view.ui_mode = viewer.UiMode.PROGRAM
        _repaint(view)
        captured["error"] = view._paint_error
        view.close()

    viewer.run("wuerfel", seed=1, _drive=drive)
    assert captured["error"] is None, f"paint raised: {captured['error']!r}"


def test_iridium_view_paints_through_build_and_run(qapp):
    captured = {}

    def drive(view):
        # build phase
        _repaint(view)
        # force the network fully built and run a step
        while not view.iri.built:
            view._on_timer()
        view.phase = "run"
        view.iri.transmit("900", "009")
        view.iri.step()
        _repaint(view)
        # a transmit prompt open
        view._begin_prompt(viewer.IriAction.TRANSMIT,
                           ["Node1", "Node2", "Repeat"])
        view.prompt.type_char("9")
        _repaint(view)
        captured["error"] = view._paint_error
        view.close()

    viewer.run_iridium(_drive=drive)
    assert captured["error"] is None, f"paint raised: {captured['error']!r}"


def test_a_salvaged_session_says_so_in_the_status_line(qapp, tmp_path):
    """A truncated .pms loads rather than failing, and both ways in -- starting
    on the file, and F->L while running -- must say that something was lost,
    not just quietly show a smaller graph."""
    from permuto.core import layout
    from permuto.core.graph import Graph
    from permuto.formats import PlySession, write_pms

    g = Graph.build("1234", ["12", "+", "23", "+", "34"], seed=1)
    for _ in range(30):
        layout.relax_step(g, alg="rubber")
    full = tmp_path / "full.pms"
    write_pms(full, PlySession(graph=g, mode="permuto", base="1234"))
    cut = tmp_path / "cut.pms"
    cut.write_text(full.read_text()[:len(full.read_text()) // 2])

    captured = {}

    def drive(view):
        captured["on_start"] = view.message         # started on the cut file
        view._load_session(str(full))               # a good one, over the top
        captured["good"] = view.message
        view._load_session(str(cut))                # and the cut one again
        captured["reloaded"] = view.message
        view.close()

    viewer.run(str(cut), _drive=drive)
    assert captured["on_start"].startswith("loaded (truncated):")
    assert captured["reloaded"].startswith("loaded (truncated):")
    assert "truncated" not in captured["good"], captured["good"]


def _rgb(img, x, y):
    c = img.pixelColor(x, y)
    return (c.red(), c.green(), c.blue())


def _edges_with_a_digit_patch(view):
    """How many edges show the punched-out background patch that an operator
    digit sits on.  The bare edge covers its own midpoint, so a clean block of
    background there can only come from the patch."""
    from permuto.ui import render

    img = _repaint(view)
    pic_w = view.width() - (260 if view.session.permuto else 0)
    pts = render.project(view.g, pic_w, view.height())
    found = 0
    for nd in view.g.ordered():
        xi, yi, _zi = pts[nd.num]
        for idx, j in enumerate(nd.links):
            if j <= nd.num or idx >= len(nd.opno) or not nd.opno[idx]:
                continue
            xj, yj, _zj = pts[j]
            for t in (0.44, 0.47, 0.5, 0.53, 0.56):
                x, y = round(xi + (xj - xi) * t), round(yi + (yj - yi) * t)
                if not (1 <= x < img.width() - 1 and 1 <= y < img.height() - 1):
                    continue
                if all(_rgb(img, x + dx, y + dy) == render.BACKGROUND
                       for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                    found += 1
                    break
    return found


def test_no_names_means_no_operator_numbers_on_the_edges(qapp):
    """`N` cycling to "write nothing" is the plain look-at-it view: small
    circles, no labels -- and no numbers on the links either.  The original
    guarded the edge digits with the very same `names` that sizes and fills the
    balls (pmdisp.mod:94), so the two cannot come apart."""
    captured = {}

    def drive(view):
        view.resize(900, 800)
        for _ in range(40):
            view.session.tick()
        captured["silent"] = _edges_with_a_digit_patch(view)   # NameMode.NONE
        _press(view, "n")                                      # -> node numbers
        captured["named"] = _edges_with_a_digit_patch(view)
        view.close()

    viewer.run("1234", operators=["12", "+", "23", "+", "34"], _drive=drive)
    assert captured["silent"] == 0, \
        "with nothing written, the links must be bare too"
    assert captured["named"] > 0, "with names, the operator numbers are back"


def _type(view, text):
    """Type a whole string into the open prompt, one key at a time."""
    for ch in text:
        _press(view, ch)


def _black_pixels_on_edge(view, n1, n2):
    """Near-black pixels along the middle of an edge -- what PmDisp draws a
    broken line in.  Measured with nothing written (NameMode.NONE), where the
    only black in the picture is a broken edge; the background sums to 64, an
    operator colour to far more, so a low sum can only be ink.
    """
    from permuto.ui import render

    img = _repaint(view)
    pic_w = view.width() - (260 if view.session.permuto else 0)
    pts = render.project(view.g, pic_w, view.height())
    x1, y1, _z1 = pts[n1]
    x2, y2, _z2 = pts[n2]
    hits = 0
    for k in range(7, 14):
        t = k / 20
        x, y = round(x1 + (x2 - x1) * t), round(y1 + (y2 - y1) * t)
        if 0 <= x < img.width() and 0 <= y < img.height() \
                and sum(_rgb(img, x, y)) < 30:
            hits += 1
    return hits


def test_breaking_a_line_needs_two_steps_and_blackens_that_edge(qapp):
    """P -> L asks for one end by number, then SelectCard walks the neighbours
    with space and Enter breaks the edge -- which PmDisp draws black.  The same
    keys again repair it, so the picture must come back."""
    captured = {}

    def break_the_line(view):
        _press(view, "p")                 # program menu
        _press(view, "l")                 # break/repair a line
        _press(view, "1")                 # node 1, as ReadInt wants it
        _press(view, "enter")
        _press(view, "space")             # walk on to the next neighbour
        chosen = view.select.current       # the one the status line offers
        _press(view, "enter")
        return chosen

    def drive(view):
        view.resize(900, 800)
        for _ in range(60):
            view.session.tick()
        other = break_the_line(view)
        captured["broken"] = _black_pixels_on_edge(view, 1, other)
        captured["mode"] = view.ui_mode
        captured["marks"] = set(view.g.nodes[1].state.broken)
        assert break_the_line(view) == other, "the same neighbour, second time"
        captured["repaired"] = _black_pixels_on_edge(view, 1, other)
        view.close()

    viewer.run("1234", operators=["12", "+", "23", "+", "34"], _drive=drive)
    assert captured["broken"] > 0, "a broken edge must be drawn black"
    assert captured["repaired"] == 0, "the same keys must repair it again"
    assert captured["marks"], "the mark belongs on the node, not just on screen"
    assert captured["mode"] is viewer.UiMode.MAIN, "the menu must close"


def test_the_file_menu_works_with_the_name_actually_typed_in(qapp, tmp_path):
    """F->S, F->O and F->L with the file name typed key by key, which is the
    only way a user reaches them."""
    saved = tmp_path / "typed"
    ps = tmp_path / "picture.ps"
    captured = {}

    def drive(view):
        for _ in range(40):
            view.session.tick()
        _press(view, "f")
        _press(view, "s")
        _type(view, str(saved))
        _press(view, "enter")
        captured["save"] = view.message

        _press(view, "f")
        _press(view, "o")
        _type(view, str(ps))
        _press(view, "enter")
        captured["ps"] = view.message

        _press(view, "f")
        _press(view, "l")
        _type(view, str(saved) + ".pms")
        _press(view, "enter")
        captured["load"] = view.message
        captured["nodes"] = view.g.nnodes
        captured["mode"] = view.ui_mode
        view.close()

    viewer.run("1234", operators=["12", "+", "23", "+", "34"], _drive=drive)
    assert (tmp_path / "typed.pms").is_file(), captured["save"]
    assert captured["save"].startswith("saved")
    assert ps.is_file() and ps.read_bytes().rstrip().endswith(b"Finish")
    assert captured["ps"].startswith("wrote")
    assert captured["load"].startswith("loaded")
    assert captured["nodes"] == 24, "the saved graph came back"
    assert captured["mode"] is viewer.UiMode.MAIN


def test_the_editor_cursor_keys_reach_the_right_cells(qapp):
    """E opens on the base, Down steps into the table, End goes to the last
    cell anyone filled in (not the last cell there is), Home back to the base."""
    from permuto.editor import BASE_FIELD, OpField

    captured = {}

    def drive(view):
        _press(view, "e")
        captured["opened"] = (view.editor.field, view.editor.buffer)
        _press(view, "down")
        captured["down"] = (view.editor.field, view.editor.buffer)
        _press(view, "end")
        captured["end"] = (view.editor.field, view.editor.buffer)
        _press(view, "home")
        captured["home"] = view.editor.field
        _press(view, "esc")
        captured["left"] = (view.ui_mode, view.editor)
        view.close()

    viewer.run("1234", operators=["12", "+", "23", "+", "34"], _drive=drive)
    assert captured["opened"] == (BASE_FIELD, "1234")
    assert captured["down"] == (OpField(1, 1), "12")
    assert captured["end"] == (OpField(3, 1), "34")
    assert captured["home"] == BASE_FIELD
    assert captured["left"] == (viewer.UiMode.MAIN, None)


def test_the_toggle_keys_move_their_own_flag_in_the_menu_line(qapp):
    """C, R, H and S each own one T/F in the top line -- a dispatch table that
    sent a key to the wrong handler would show up here."""
    captured = {}

    def drive(view):
        captured["start"] = view.session.top_line(view.ui_mode)
        for key in "crhs":
            _press(view, key)
        captured["toggled"] = view.session.top_line(view.ui_mode)
        captured["alg_before"] = view.session.status_line()
        _press(view, "a")
        captured["alg_after"] = view.session.status_line()
        view.close()

    viewer.run("1234", operators=["12", "+", "23", "+", "34"], _drive=drive)
    for flag in ("(C)alc T", "(R)un F", "(H)urry F", "(S)pin T"):
        assert flag in captured["start"], captured["start"]
    for flag in ("(C)alc F", "(R)un T", "(H)urry T", "(S)pin F"):
        assert flag in captured["toggled"], captured["toggled"]
    assert captured["alg_before"] != captured["alg_after"], "A steps the algorithm"


def _iri_node(view, label):
    """The satellite carrying *label* -- the name the user reads on screen."""
    return next(nd for nd in view.graph.nodes.values() if nd.perm == label)


def _carrying(view):
    """How many satellites hold a packet right now."""
    return sum(1 for nd in view.graph.nodes.values() if nd.iri.message_num)


def test_the_iridium_keys_kill_transmit_step_and_clear(qapp):
    """K, T, space and C, typed as a user types them: the commands take the
    three-digit label off the screen, not a node index."""
    captured = {}

    def drive(view):
        while not view.iri.built:            # grow the network out
            view._on_timer()
        _press(view, "s")                    # any key ends the settling wait
        captured["phase"] = view.phase
        captured["skip_still_stepped"] = view.stepbuf   # ...and does its own job

        _press(view, "k")                    # kill the satellite labelled 900
        _type(view, "900")
        _press(view, "enter")
        captured["dead"] = _iri_node(view, "900").iri.avail
        _press(view, "k")                    # and switch it back on
        _type(view, "900")
        _press(view, "enter")
        captured["alive"] = _iri_node(view, "900").iri.avail > 0

        _press(view, "t")                    # send 009 -> 018, no repeat
        for value in ("9", "18", "0"):
            _type(view, value)
            _press(view, "enter")
        captured["sent"] = _carrying(view)
        captured["mode"] = view.ui_mode

        before = view.stepbuf                # a step, queued for the timer
        _press(view, "space")
        queued = view.stepbuf
        view._on_timer()
        captured["queue"] = (queued - before, queued - view.stepbuf)

        _press(view, "c")                    # clear the network
        captured["cleared"] = _carrying(view)
        _repaint(view)
        captured["error"] = view._paint_error
        view.close()

    viewer.run_iridium(_drive=drive)
    assert captured["phase"] is viewer.IriPhase.RUN, "a key skips the wait"
    assert captured["skip_still_stepped"] == 1, \
        "skipping the wait must not swallow the key that did it"
    assert captured["dead"] == 0, "K kills the satellite it names"
    assert captured["alive"], "K again repairs it"
    assert captured["sent"] >= 2, "sender and target both hold the packet"
    assert captured["mode"] is viewer.UiMode.MAIN, "the prompt closed"
    assert captured["queue"] == (1, 1), "space queues a step, the timer drains it"
    assert captured["cleared"] == 0, "C clears the traffic"
    assert captured["error"] is None


def test_a_dead_satellite_cannot_send_and_says_so(qapp):
    """The 1992 note "don't allow for target to be a broken node" is an error
    here, not silence -- and it has to reach the status line."""
    captured = {}

    def drive(view):
        while not view.iri.built:
            view._on_timer()
        _press(view, "s")
        _press(view, "k")                    # kill 009 first
        _type(view, "9")
        _press(view, "enter")
        _press(view, "t")                    # then try to send from it
        for value in ("9", "18", "0"):
            _type(view, value)
            _press(view, "enter")
        captured["message"] = view.message
        captured["mode"] = view.ui_mode
        view.close()

    viewer.run_iridium(_drive=drive)
    assert "dead" in captured["message"], captured["message"]
    assert captured["mode"] is viewer.UiMode.MAIN


def test_a_three_field_prompt_stays_open_until_the_last_field(qapp):
    """Transmit asks for Node1, Node2 and Repeat in turn.  Enter on the first
    two commits that one field and keeps the prompt up (FieldPrompt.enter
    answers "more"); only the third submits.  Treating "more" as an ending
    swallowed the command after the first Enter."""
    captured = {}

    def drive(view):
        while not view.iri.built:
            view._on_timer()
        _press(view, "x")                    # end the wait without a side job
        _press(view, "t")
        captured["opened"] = view.ui_mode
        _type(view, "9")
        _press(view, "enter")
        captured["after_1st"] = (view.ui_mode, view.prompt is not None)
        _type(view, "18")
        _press(view, "enter")
        captured["after_2nd"] = (view.ui_mode, view.prompt is not None)
        _type(view, "0")
        _press(view, "enter")
        captured["after_3rd"] = (view.ui_mode, view.prompt is None)
        captured["arrived"] = _carrying(view)
        view.close()

    viewer.run_iridium(_drive=drive)
    assert captured["opened"] is viewer.UiMode.PROMPT
    assert captured["after_1st"] == (viewer.UiMode.PROMPT, True), \
        "one field committed, two to go -- the prompt must stay"
    assert captured["after_2nd"] == (viewer.UiMode.PROMPT, True)
    assert captured["after_3rd"] == (viewer.UiMode.MAIN, True)
    assert captured["arrived"] >= 2, "and only then does the packet exist"
