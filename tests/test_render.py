"""Smoke test for the offscreen renderer (skipped if PySide6 is unavailable)."""

import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from conftest import modula_dir  # noqa: E402

from permuto import scene  # noqa: E402
from permuto.core import intvector as iv  # noqa: E402
from permuto.core import layout  # noqa: E402
from permuto.core.graph import Graph, Node  # noqa: E402
from permuto.ui import render  # noqa: E402


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
    g.dimensions = 3
    g.nodes[1] = Node(num=1, pos=[iv.NORM, 0, 0, 0, 0, 0, 0, 0])
    g.nodes[2] = Node(num=2, pos=[0, iv.NORM, 0, 0, 0, 0, 0, 0])
    for w, h in ((900, 300), (300, 900), (700, 700)):
        pts = render.project(g, w, h)
        dx = abs(pts[1][0] - w // 2)      # x offset of the pos[0]=NORM node
        dy = abs(pts[2][1] - h // 2)      # y offset of the pos[1]=NORM node
        assert dx == dy, f"anisotropic at {w}x{h}: {dx} != {dy}"


def _painted(g, w, h, **kw):
    from PySide6.QtGui import QImage, QPainter

    img = QImage(w, h, QImage.Format.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    render.paint(g, p, w, h, **kw)
    p.end()
    return img


def _relaxed_permutograph(steps=200):
    g = Graph.build("1234", ["12", "+", "23", "+", "34"], seed=1)
    for _ in range(steps):
        layout.relax_step(g, alg="rubber")
    return g


def test_a_node_carries_the_colour_of_its_class():
    """What the eye reads off the picture has to be in the data first:
    ``color := Str.Pos(BasePerm, perm[0]) + 1`` groups the permutations by
    first character, and a ``.nod`` graph, having no permutations, falls back
    to blocks of the node numbering (``SetupPolytope``).  Whether the drawing
    then uses it is checked from the viewer, in test_viewer.py."""
    g = _relaxed_permutograph(steps=1)
    by_first = {}
    for nd in g.nodes.values():
        by_first.setdefault(nd.perm[0], set()).add(nd.color)
    assert len(by_first) == 4, "base 1234 has four classes"
    assert all(len(cols) == 1 for cols in by_first.values()), "one colour each"

    plain = Graph.load_nod(modula_dir() / "nod" / "tetraede.nod", seed=1)
    assert plain.nnodes <= 24
    assert [plain.nodes[n].color for n in sorted(plain.nodes)] == \
           [1 + (n - 1) // 6 for n in sorted(plain.nodes)]


def test_operator_panel_lists_the_base_and_operators():
    from permuto.editor import BASE_FIELD
    from permuto.loader import make_session

    s = make_session("1234", operators=["12", "+", "23", "+", "34"])
    rows = render.operator_panel_rows(s.pm)
    assert rows[0] == ("Base", "1234", BASE_FIELD)
    values = {v for _, v, f in rows if f and not f.is_base}
    assert {"12", "23", "34"} <= values


def test_iridium_view_builds_and_paints_a_transmitting_network():
    """The /I drawing path: build the 55-satellite grid the way the viewer
    does, transmit, and paint. Checks the network builds and the packet turns
    a node non-idle (so the colour path is exercised), then that something is
    drawn."""
    from PySide6.QtGui import QImage, QPainter
    from permuto.core.graph import Graph
    from permuto.core.iri import Iridium, YELLOW

    g = Graph()
    g.set_dimensions(2)
    iri = Iridium(g)
    while not iri.built:
        iri.new_node()
        for _ in range(5):
            layout.backup(g)
            layout.contract(g, "new")
            layout.normalize(g)
    assert g.nnodes == 55
    iri.transmit("900", "009")
    assert any(nd.color != YELLOW for nd in g.nodes.values())  # a packet is live

    img = QImage(600, 600, QImage.Format.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    render.paint_iridium(g, p, 600, 600)
    p.end()
    bg = img.pixel(0, 0)
    assert any(img.pixel(x, y) != bg
               for x in range(0, 600, 12) for y in range(0, 600, 12))


def test_viewer_builds_without_a_display():
    """The whole viewer construction path (session + panel + first paint) must
    work headless, so this stays covered without a human at the screen."""
    from PySide6.QtGui import QImage, QPainter
    from permuto.loader import make_session

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


# -- what covers what ----------------------------------------------------
# paint() draws in layers: edges, then the operator digits on their punched-out
# patches, then the balls, then the labels inside them.  Nothing but the order
# of those loops decides the picture, so these pin the order down.

def _spread_permutograph():
    """The default permutograph, relaxed until the nodes are apart."""
    from permuto.loader import make_session

    s = make_session("1234", operators=["12", "+", "23", "+", "34"])
    for _ in range(200):
        layout.relax_step(s.graph, alg="rubber")
    return s.graph


def _rgb(img, x, y):
    c = img.pixelColor(x, y)
    return (c.red(), c.green(), c.blue())


def test_balls_cover_the_edges_that_run_into_them():
    """Every node's own edges end at its centre, so a centre showing an edge
    colour would mean the balls were drawn first.

    A centre is checked against the fills the scene actually asked for, not
    against the sixteen palette entries: a ball is shaded by how deep it sits
    now, so its fill lies *between* two entries.  The set is still the right
    comparison because a nearer ball may cover a further one's centre.
    """
    g = _spread_permutograph()
    size = 700
    img = render.render_image(g, size, size, op_colors=True)
    sc = scene.build(g, size, size, op_colors=True)
    fills = {b.fill for b in sc.balls if b.fill is not None}
    checked = 0
    for n, (x, y, _z) in render.project(g, size, size).items():
        if not (0 <= x < size and 0 <= y < size):
            continue
        assert _rgb(img, int(x), int(y)) in fills, \
            f"node {n}'s centre is not a filled ball"
        checked += 1
    assert checked > 5, "no nodes landed on the picture"


def test_labels_are_inked_inside_the_balls():
    """text_mode 1 writes node numbers in black inside the ball -- after it."""
    g = _spread_permutograph()
    size = 700
    img = render.render_image(g, size, size, name_mode=1)
    r = int(render._scaled(size, 9))          # the radius text_mode 1 uses
    ink = 0
    for x, y, _z in render.project(g, size, size).values():
        for px in range(int(x) - r, int(x) + r + 1):
            for py in range(int(y) - r, int(y) + r + 1):
                if 0 <= px < size and 0 <= py < size \
                        and _rgb(img, px, py) == render.INK:
                    ink += 1
    assert ink > 20, "no black label ink inside the balls"


def test_the_operator_digit_punches_its_patch_through_the_edge():
    """The digit sits on a background patch, drawn over the edge.  Under it,
    the edge would simply paint across the patch again."""
    g = _spread_permutograph()
    size = 700
    pts = render.project(g, size, size)

    def clean_patches(img):
        """Edges whose midpoint has a 3x3 block of pure background on the line
        -- only the punched-out patch can produce that."""
        found = 0
        for nd in g.ordered():
            xi, yi, _zi = pts[nd.num]
            for link in nd.links:
                j = link.to
                if j <= nd.num or not link.op:
                    continue
                xj, yj, _zj = pts[j]
                for t in (0.44, 0.47, 0.5, 0.53, 0.56):
                    x, y = round(xi + (xj - xi) * t), round(yi + (yj - yi) * t)
                    if not (1 <= x < size - 1 and 1 <= y < size - 1):
                        continue
                    if all(_rgb(img, x + dx, y + dy) == render.BACKGROUND
                           for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                        found += 1
                        break
        return found

    # name_mode=1: the digits follow `names`, so a picture with nothing
    # written on the balls has nothing on the links either
    with_digits = render.render_image(g, size, size, op_colors=True,
                                      name_mode=1, operator_digits=True)
    without = render.render_image(g, size, size, op_colors=True,
                                  name_mode=1, operator_digits=False)
    assert clean_patches(without) == 0, "the bare edge must cover its midpoint"
    assert clean_patches(with_digits) > 0, \
        "the digit patch must cover the edge, not sit under it"


def _with_spa(steps=6):
    """A permutograph part-way through SPA: line states, and one node each
    killed and marked active."""
    from permuto.core import spa

    g = _spread_permutograph()
    spa.init_spa(g, 1)
    for _ in range(steps):
        spa.shortest_path(g)
    return g


def test_the_direction_discs_actually_reach_the_picture():
    """The decisions are checked in test_scene; this is the other half -- that
    the layer is drawn at all.  Nothing painted it in any test until now
    (HANDOVER, item 1).

    A disc is the same green as the edge it sits on -- it is a thickening of
    the line, not a second colour -- so the only honest question is whether
    that spot carries more of that green with the layer than without it.
    """
    from dataclasses import replace

    from permuto import scene

    g = _with_spa()
    size = 700
    sc = scene.build(g, size, size, op_colors=True, program=True)
    assert sc.discs, "the wave has to have moved for this test to mean anything"

    def _drawn(s):
        from PySide6.QtGui import QImage, QPainter
        img = QImage(size, size, QImage.Format.Format_ARGB32)
        img.fill(0)
        p = QPainter(img)
        render.draw_scene(s, p)
        p.end()
        return img

    def _around(img, disc, r):
        x0, y0 = int(disc.at[0]), int(disc.at[1])
        return sum(1
                   for x in range(x0 - r, x0 + r + 1)
                   for y in range(y0 - r, y0 + r + 1)
                   if 0 <= x < size and 0 <= y < size
                   and _rgb(img, x, y) == disc.rgb)

    with_discs = _drawn(sc)
    without = _drawn(replace(sc, discs=[]))
    r = int(sc.disc_radius) + 1
    thicker = sum(1 for d in sc.discs
                  if _around(with_discs, d, r) > _around(without, d, r))
    assert thicker, "no direction disc thickened the edge it belongs to"


def test_a_dead_ball_is_hollow_and_an_active_one_wears_its_ring():
    """`P`->`N` kills a node and the SPA front marks others active; both are
    drawn, and both were unpainted in every test before this one."""
    from permuto import scene

    g = _with_spa()
    size = 700
    dead, active = list(g.nodes)[0], list(g.nodes)[1]
    g.nodes[dead].state.dead = True
    g.nodes[active].state.active = True
    g.nodes[active].state.dead = False

    sc = scene.build(g, size, size, op_colors=True, program=True)
    img = _painted(g, size, size, op_colors=True, program=True)
    pts = render.project(g, size, size)

    x, y, _z = pts[dead]
    assert _rgb(img, int(x), int(y)) == render.BACKGROUND, \
        "a dead node must be hollow, not filled"

    x, y, _z = pts[active]
    ring = sc.radius + sc.ring_extra
    white = any(_rgb(img, int(x + dx), int(y)) == (255, 255, 255)
                for dx in (round(ring), round(ring) + 1, round(ring) - 1,
                           -round(ring), -round(ring) - 1, -round(ring) + 1)
                if 0 <= int(x + dx) < size)
    assert white, "an active node must be ringed white"
