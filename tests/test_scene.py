"""What is in the picture, asked without drawing it.

These decisions used to be made inside a QPainter loop, so the only way to
check them was to look at pixels -- and nobody did: the direction discs, the
hollow dead ball and the white ring on an active node had no test at all
(HANDOVER, "what to do next", item 1).  Split out of the painting, they are
plain numbers and RGB triples, and this is what they say.

The picture itself is still checked where it belongs, in test_render.py and
by driving the widget in test_viewer.py.
"""

import pytest

from permuto import scene
from permuto.core.graph import (L_FREE, L_INPUT, L_LOCKED, L_OUTPUT, Graph,
                                Link, Node)
from permuto.loader import load_graph

SIZE = 700


def _two_nodes(dimensions=2, z=0):
    """Two nodes side by side, linked, at known coordinates.

    Hand-built rather than relaxed, so the geometry in the assertions below is
    arithmetic and not an accident of the layout.  ``z`` decides whether the
    edge between them faces the viewer: ``front = (zi + zj) > 0``, so a flat
    2-D graph is entirely back-facing and drawn dim throughout.
    """
    g = Graph()
    g.dimensions = dimensions
    for num, x in ((1, -(1 << 23)), (2, 1 << 23)):
        nd = Node(num=num, pos=[x, 0, z] + [0] * 5, color=num, perm=str(num))
        nd.links = [Link(to=3 - num, op=1)]
        g.nodes[num] = nd
    g.n_operators = 1
    return g


def _edge(sc):
    assert len(sc.edges) == 1, "two linked nodes make exactly one edge"
    return sc.edges[0]


# -- which colour an edge is, and why ---------------------------------------

def test_a_broken_edge_is_black_and_stays_wide_at_the_back():
    """Breaking a line is the one mark that must read the same front or back:
    it says the graph was edited, not how far away it is."""
    g = _two_nodes()
    g.nodes[1].links[0].broken = True
    e = _edge(scene.build(g, SIZE, SIZE, op_colors=True, program=True))
    assert e.reason == "broken"
    assert e.rgb == scene.BROKEN
    assert e.width == scene.stroke_width(SIZE, 1.1)


def test_the_program_wave_outranks_the_operator_colour():
    """While SPA runs, the line state is what the picture is about; the
    operator number keeps its digit but loses the colour."""
    g = _two_nodes(3, z=1)                  # facing the viewer: undimmed
    g.nodes[1].links[0].status = L_LOCKED
    plain = _edge(scene.build(g, SIZE, SIZE, op_colors=True))
    running = _edge(scene.build(g, SIZE, SIZE, op_colors=True, program=True))
    assert plain.reason == "operator"
    assert running.reason == "state"
    assert running.rgb == scene.state_color(L_LOCKED, True)


def test_an_edge_with_nothing_to_say_is_plain():
    g = _two_nodes(3, z=1)
    g.n_operators = 0                       # a .nod graph knows no operators
    e = _edge(scene.build(g, SIZE, SIZE, op_colors=True))
    assert (e.reason, e.rgb) == ("plain", scene.PLAIN_FRONT)


def test_back_edges_are_dimmed_because_the_palette_trick_is_gone():
    """The original flipped to the bright half of the DOS palette for the
    front; with real colours the port dims the back instead (PORT-GAPS 6).

    The back end also carries FOG of the background now -- dimming alone puts
    both ends within 45% of each other, which as a *continuous* ramp reads
    flatter than the two steps it replaced.
    """
    front = scene.operator_color(1, True)
    back = scene.operator_color(1, False)
    assert back == scene.hazed(scene.dim(front, 45))
    assert all(b < f for b, f in zip(back, front))
    assert scene.state_color(L_LOCKED, False) == \
        scene.hazed(scene.dim(scene.state_color(L_LOCKED, True), 50))


def test_depth_between_the_ends_is_a_ramp_and_the_ends_are_the_old_two():
    """True/False still mean exactly what they meant while depth was a
    yes/no question, so no call site changed meaning when it grew a range."""
    back, front = scene.operator_color(1, 0.0), scene.operator_color(1, 1.0)
    assert (back, front) == (scene.operator_color(1, False),
                             scene.operator_color(1, True))
    mid = scene.operator_color(1, 0.5)
    assert all(b < m < f for b, m, f in zip(back, mid, front))


# -- the direction discs ----------------------------------------------------

def test_an_input_disc_sits_near_this_node_and_an_output_near_the_other():
    """Colour says the edge carries the wave; the disc says which way -- a
    sixth of the way along, from whichever end the wave enters."""
    g = _two_nodes()
    g.nodes[1].links[0].status = L_INPUT
    sc = scene.build(g, SIZE, SIZE, program=True)
    (disc,) = sc.discs
    a, b = sc.edges[0].a, sc.edges[0].b
    assert disc.incoming
    assert disc.at == ((5 * a[0] + b[0]) / 6, (5 * a[1] + b[1]) / 6)

    g.nodes[1].links[0].status = L_OUTPUT
    (disc,) = scene.build(g, SIZE, SIZE, program=True).discs
    assert not disc.incoming
    assert disc.at == ((5 * b[0] + a[0]) / 6, (5 * b[1] + a[1]) / 6)


@pytest.mark.parametrize("state", [L_FREE, L_LOCKED])
def test_only_a_moving_wave_gets_a_disc(state):
    """A locked or free edge goes nowhere, so there is no direction to show."""
    g = _two_nodes()
    g.nodes[1].links[0].status = state
    assert scene.build(g, SIZE, SIZE, program=True).discs == []


def test_a_broken_edge_carries_no_disc_even_mid_wave():
    """It is out of the graph; a leftover arrow on it would be a lie."""
    g = _two_nodes()
    g.nodes[1].links[0].status = L_INPUT
    g.nodes[1].links[0].broken = True
    assert scene.build(g, SIZE, SIZE, program=True).discs == []


# -- the balls --------------------------------------------------------------

def test_a_dead_node_is_hollow_and_an_active_one_is_ringed():
    g = _two_nodes()
    g.nodes[1].state.dead = True
    g.nodes[2].state.active = True
    dead, active = scene.build(g, SIZE, SIZE).balls
    assert dead.fill is None, "dead: background, so the black rim shows"
    assert not dead.ringed
    assert active.fill is not None and active.ringed


def test_no_graph_can_produce_an_invisible_ball():
    """ikosa9 has 812 nodes and colours up to 34; entry 0 is black on a black
    background and 8 is nearly so.  Cycling 1..7 with the bright twins keeps
    every ball visible -- the reason ball_color does not simply take color%16."""
    g = load_graph("ikosa9", seed=1)
    colours = {nd.color for nd in g.nodes.values()}
    assert max(colours) > 16, "otherwise this graph proves nothing"
    entries = {scene.ball_color(c, lit) for c in colours for lit in (True, False)}
    assert entries.isdisjoint({0, 8}), f"invisible entry among {sorted(entries)}"
    assert entries <= set(range(1, 8)) | set(range(9, 16))


def test_the_front_half_of_the_palette_is_the_depth_cue():
    """farbe := (color+8) MOD 16 -- the one place the original's trick stayed,
    because a ball is a flat colour and dimming it would just look muddy."""
    for colour in range(1, 8):
        assert scene.ball_color(colour, True) == scene.ball_color(colour, False) + 8


def test_a_flat_graph_has_no_front_and_takes_the_dark_half():
    """Depth needs three dimensions; in 2-D every ball is at z = 0 and the
    picture would otherwise be uniformly bright for no reason."""
    flat = scene.build(_two_nodes(dimensions=2), SIZE, SIZE)
    deep = scene.build(_two_nodes(dimensions=3), SIZE, SIZE)
    assert flat.balls[0].fill == scene.DOS_PALETTE[scene.ball_color(1, False)]
    assert deep.balls[0].fill == scene.DOS_PALETTE[scene.ball_color(1, True)]


# -- what goes inside the balls, and how big they are ------------------------

@pytest.mark.parametrize("kw,mode,shown", [
    ({}, 0, ""),                                   # nothing asked for
    ({"labels": True}, 2, "1"),                    # the renderer's default
    ({"name_mode": 1}, 1, "1"),                    # node number
    ({"name_mode": 2}, 2, "1"),                    # the permutation
    ({"program": True}, 3, "0"),                   # the SPA display value
])
def test_what_is_written_in_a_ball_decides_how_big_it_is(kw, mode, shown):
    """One `names` drives both in PmDisp.DrawNodes: a four-character perm needs
    a radius of 12 to fit, "write nothing" needs only 5."""
    sc = scene.build(_two_nodes(), SIZE, SIZE, **kw)
    assert sc.radius == scene.mark_size(SIZE, scene.BALL_RADIUS[mode])
    assert sc.balls[0].label == shown


def test_writing_nothing_leaves_the_links_bare_too():
    """pmdisp.mod:94 guards the ball labels and the operator digits with the
    same `names>0`, so cycling N to "write nothing" clears both."""
    g = _two_nodes()
    assert scene.build(g, SIZE, SIZE, op_colors=True, name_mode=1).digits
    assert not scene.build(g, SIZE, SIZE, op_colors=True, name_mode=0).digits


def test_a_broken_edge_loses_its_operator_digit():
    g = _two_nodes()
    g.nodes[1].links[0].broken = True
    assert not scene.build(g, SIZE, SIZE, op_colors=True, name_mode=1).digits


# -- Iridium ----------------------------------------------------------------

def test_a_satellite_shows_its_name_when_idle_and_its_packet_when_busy():
    g = _two_nodes()
    g.nodes[1].color = scene.YELLOW              # idle
    g.nodes[1].perm = "900"
    g.nodes[2].color = 4                         # carrying something
    g.nodes[2].iri.message_num = 7
    idle, busy = scene.iridium_scene(g, SIZE, SIZE).balls
    assert idle.label == "900"
    assert busy.label == "7"


def test_a_satellite_grows_with_what_it_has_left():
    """diameter = Scale(11, avail+1500, 10000) -- a drained node shrinks, and
    the picture shows the load without any legend."""
    g = _two_nodes()
    g.nodes[1].iri.avail = 10000
    g.nodes[2].iri.avail = 0
    full, empty = scene.iridium_scene(g, SIZE, SIZE).balls
    assert full.radius > empty.radius
    assert empty.radius == scene.mark_size(SIZE, 11 * 1500 / 10000) / 2


# -- how the picture answers a bigger window --------------------------------

def test_pulling_the_window_open_buys_distance_not_bigger_balls():
    """The point of enlarging is to see the structure in the room that appears.
    Marks that keep a constant fraction of the picture make it a pure zoom --
    the same picture, larger, saying nothing new.  Past MARK_REFERENCE they
    stand still and the graph spreads out underneath them."""
    g = _two_nodes()
    sizes = [740, 1110, 1480, 2220]
    radii = {scene.build(g, s, s).radius for s in sizes}
    assert len(radii) == 1, f"the balls grew with the window: {sorted(radii)}"

    spread = [abs(scene.build(g, s, s).edges[0].a[0]
                  - scene.build(g, s, s).edges[0].b[0]) for s in sizes]
    assert spread == sorted(spread) and spread[-1] > 2 * spread[0], \
        "the nodes have to move apart, or there is nothing to see"


def test_a_small_window_still_scales_so_it_stays_legible():
    """Below the reference the old rule holds: a mark keeps its share of the
    picture, so a small window is a small picture and not a few vast balls."""
    g = _two_nodes()
    small, reference = scene.build(g, 370, 370), scene.build(g, 740, 740)
    assert small.radius < reference.radius
    assert small.radius == pytest.approx(reference.radius / 2, rel=0.01)


def test_marks_are_measured_by_the_side_the_nodes_are_spread_over():
    """They used to be measured by the height while the nodes were spread over
    the short side, so a tall narrow window drew balls 2.6x too fat for the
    distances they sat in."""
    assert scene.picture_extent(300, 900) == 300
    narrow = scene.build(_two_nodes(), 300, 900)
    square = scene.build(_two_nodes(), 300, 300)
    assert narrow.radius == square.radius, \
        "the extra height is empty margin; it may not inflate the marks"


def test_every_mark_in_the_picture_follows_the_same_rule():
    """One family: ball, label, digit, disc, rim and pen widths all stop
    growing together, or the ball outgrows the text meant to sit inside it."""
    g = _two_nodes()
    # concrete sizes, not multiples of MARK_REFERENCE: derived from the constant
    # they would agree with any value of it, including "never stop growing"
    assert scene.MARK_REFERENCE <= 740, "both sizes below are meant to clamp"
    kw = dict(op_colors=True, name_mode=2, program=True)
    at_reference = scene.build(g, 740, 740, **kw)
    far_bigger = scene.build(g, 2220, 2220, **kw)
    for attr in ("radius", "digit_size", "digit_pad", "label_size",
                 "disc_radius", "rim_width", "ring_extra"):
        assert getattr(at_reference, attr) == getattr(far_bigger, attr), attr
    assert at_reference.edges[0].width == far_bigger.edges[0].width


# -- depth: what is nearer, and how one can tell ----------------------------

def _three_at_depths(zs):
    """One node per z, all at the same place on screen -- so only depth can
    distinguish them.  Numbered against the order they should end up in."""
    g = Graph()
    g.dimensions = 3
    for num, z in enumerate(zs, start=1):
        g.nodes[num] = Node(num=num, pos=[0, 0, z] + [0] * 5,
                            color=1, perm=str(num))
    return g


def test_the_balls_are_drawn_back_to_front():
    """The painter has no z-buffer, so the order in the scene *is* the depth
    order.  It used to be node order, which is to say none: which ball covered
    which was decided by whichever the graph happened to list last."""
    zs = [1 << 20, -(1 << 23), 1 << 23]                    # middle, far, near
    balls = scene.build(_three_at_depths(zs), SIZE, SIZE, name_mode=1).balls
    order = [zs[int(b.label) - 1] for b in balls]
    assert order == sorted(order), "a nearer ball must be drawn later"


def test_a_ball_further_back_is_darker_and_smaller():
    """The two cues the sorting needs to be readable: without them the overlaps
    are correct and still look like a flat tangle."""
    far, mid, near = scene.build(_three_at_depths(
        [-(1 << 23), 0, 1 << 23]), SIZE, SIZE).balls
    assert far.fill < mid.fill < near.fill        # channel by channel, tuple-wise
    assert far.radius < mid.radius < near.radius
    assert near.radius == pytest.approx(scene.build(
        _three_at_depths([0]), SIZE, SIZE).balls[0].radius), \
        "the nearest ball keeps the size the original drew every ball at"


def test_depth_shading_needs_no_reference_beyond_the_frame_itself():
    """Measured against the deepest node *of this frame*: NORM would leave a
    graph whose z happens to be small sitting in the middle of the ramp, with
    no front and no back."""
    shallow = scene.build(_three_at_depths([-100, 0, 100]), SIZE, SIZE).balls
    deep = scene.build(_three_at_depths(
        [-(1 << 23), 0, 1 << 23]), SIZE, SIZE).balls
    assert [b.fill for b in shallow] == [b.fill for b in deep]


# -- the fourth dimension ---------------------------------------------------

def _four_dimensional():
    """Two nodes that differ *only* in their fourth component."""
    g = Graph()
    g.dimensions = 4
    for num, w in ((1, -(1 << 23)), (2, 1 << 23)):
        g.nodes[num] = Node(num=num, pos=[0, 0, 0, w] + [0] * 4,
                            color=num, perm=str(num))
    return g


def test_without_the_hyper_turn_a_fourth_dimension_is_invisible():
    """The whole reason for the turn: project drops components past the third,
    so two nodes apart only in the fourth sit at the same pixel for ever."""
    a, b = scene.project(_four_dimensional(), SIZE, SIZE).values()
    assert a == b


def test_the_hyper_turn_brings_the_fourth_dimension_onto_the_screen():
    """A quarter turn of the (1,4) plane puts it where x was."""
    import math

    pts = scene.project(_four_dimensional(), SIZE, SIZE, math.pi / 2)
    (x1, _y1, _z1), (x2, _y2, _z2) = pts.values()
    assert x1 < SIZE // 2 < x2, "the two must now be at opposite sides"


def test_a_graph_with_three_dimensions_ignores_the_hyper_turn():
    """Nothing to look at from another side, and turning the view would only
    invent something: the fourth component is zero for every node."""
    g = _two_nodes(dimensions=3, z=1 << 20)
    assert scene.project(g, SIZE, SIZE, 1.0) == scene.project(g, SIZE, SIZE)
