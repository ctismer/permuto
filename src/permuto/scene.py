"""What one frame of the graph consists of, before anything is drawn.

``PmDisp.DrawEdges`` decided and drew in the same loop, and the port had kept
that: which colour an edge is, how wide, whether it carries a direction disc
and where that disc sits were all computed inside a ``QPainter`` loop.  Nothing
about those decisions needs a painter, and while they lived inside one they
could only be tested by looking at pixels -- which is why the direction discs,
the hollow dead balls and the white ring on an active node had no test at all.

So this module answers "what is in the picture" in plain numbers and RGB
triples, and :mod:`permuto.ui.render` does nothing but put them on a
``QPainter``.  A second frontend inherits the geometry and the palette and
supplies its own five drawing calls.

The layer order is the one the original needed and this module returns in:
edges run into the node centres and under the operator digits, so the digits
sit on a punched-out patch of background, the balls go over both, and the
labels go inside the balls.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .core import intvector as iv
from .core.graph import L_INPUT, L_LOCKED, L_OUTPUT
from .editor import BASE_FIELD, fields_of, value_of

Point = tuple[float, float]
RGB = tuple[int, int, int]

BACKGROUND: RGB = (18, 18, 28)   # picture background; shared with the chrome
INK: RGB = (0, 0, 0)             # PlotCenteredStr(..., 0) -- labels are black

#: distinct, reasonably colour-blind-friendly hues for operators 1..n
OPERATOR_PALETTE: list[RGB] = [
    (90, 200, 255), (255, 150, 90), (140, 230, 120), (230, 120, 220),
    (240, 220, 90), (120, 190, 235), (250, 130, 150), (170, 220, 200),
]

#: the standard DOS 16-colour palette, by index -- the balls use it, and
#: Iridium/SIMONE colours nodes by it directly (Window.Yellow=14 idle,
#: Blue=1 destination, Red=4 and NextColor for packets)
DOS_PALETTE: list[RGB] = [
    (0, 0, 0), (60, 60, 220), (0, 170, 0), (0, 170, 170),
    (210, 40, 40), (200, 0, 200), (170, 85, 0), (200, 200, 200),
    (110, 110, 120), (110, 110, 255), (85, 255, 85), (85, 255, 255),
    (255, 110, 110), (255, 120, 255), (245, 235, 90), (255, 255, 255),
]

PLAIN_FRONT: RGB = (90, 200, 255)    # an edge with nothing to say about itself
PLAIN_BACK: RGB = (70, 80, 120)
BROKEN: RGB = (0, 0, 0)
RING: RGB = (255, 255, 255)          # the white ring on an active node

PICTURE_PIXELS = 320   # the original picture area was 479 x 320 (pmdisp.def)

#: The picture extent at which marks stop growing: the size their proportions
#: were judged at, and roughly what the viewer opens with.
#:
#: Past it, pulling the window open buys *distance between the nodes*, not
#: bigger balls.  Marks that keep a constant fraction of the picture make
#: enlarging a pure zoom: the same picture, bigger, telling you nothing new --
#: whereas the reason to pull a window open is to see the structure in the room
#: that appears.  The 1995 original could not be resized at all, so there is no
#: behaviour here to be faithful to.
MARK_REFERENCE = 740

# One knob for the whole UI's apparent size.  A faithful mapping (1.0) puts
# every mark at the same fraction of the picture it had on the 479x320 original,
# but that reads a touch large on a modern display, so the default trims it.
# This is the single number to turn if things want to be bigger or smaller, and
# the one a size control would drive.
#
# Written as the arithmetic it is: marks used to be 0.62 of a window *height* of
# 860, and are now measured against a picture *extent* of 740, so this restates
# the same size against the new reference.  Rounding it to 0.72 is a 0.075%
# change and still visibly wrong: it moves a centred ball label across a
# rounding boundary, and 5840 pixels of the opening window shift by one.
UI_SCALE = 0.62 * 860 / 740

YELLOW = 14            # Iridium: the colour of an idle satellite


# -- sizes, in the original's picture pixels --------------------------------

def picture_extent(width: int, height: int) -> int:
    """What "the picture" measures, for the purpose of sizing marks: its short
    side -- the same quantity :func:`project` spreads the nodes over.

    Sizing marks by the height alone let the two disagree: a tall narrow window
    drew balls for a height the picture never got, 2.6x too fat for the
    distances they sat in.
    """
    return min(width, height)


def _scale(extent: int, picture_pixels: float) -> float:
    return picture_pixels * min(extent, MARK_REFERENCE) / PICTURE_PIXELS * UI_SCALE


def mark_size(extent: int, picture_pixels: float) -> float:
    """A mark size (font, node), in the original's picture pixels, for today.

    Below :data:`MARK_REFERENCE` it keeps the same fraction of the picture
    (PORT-GAPS section 6), so a small window stays legible; above it the mark
    stands still and the extra room goes into the graph.  Floored at 1 px so
    fonts never round to nothing.
    """
    return max(1.0, _scale(extent, picture_pixels))


def stroke_width(extent: int, picture_pixels: float) -> float:
    """Like :func:`mark_size` but for pen widths, which may go below 1 px so
    that a busy sphere of edges does not turn into a solid blob."""
    return max(0.5, _scale(extent, picture_pixels))


def dim(rgb: RGB, percent: int) -> RGB:
    """A back-facing mark, dimmed -- the depth cue, in place of the original's
    ``colour + 8`` palette trick (PORT-GAPS section 6)."""
    r, g, b = rgb
    return (r * percent // 100, g * percent // 100, b * percent // 100)


def operator_color(opk: int, front: bool) -> RGB:
    rgb = OPERATOR_PALETTE[(opk - 1) % len(OPERATOR_PALETTE)]
    return rgb if front else dim(rgb, 45)


def state_color(state: int, front: bool) -> RGB:
    """LineStatus -> colour (PmDisp): input/output green, locked red, free grey."""
    if state in (L_INPUT, L_OUTPUT):
        rgb = (90, 220, 110)
    elif state == L_LOCKED:
        rgb = (220, 80, 80)
    else:                                    # L_FREE
        rgb = (80, 85, 100)
    return rgb if front else dim(rgb, 50)


def ball_color(color: int, front: bool) -> int:
    """The palette entry a node's ball is filled with.

    ``color`` says which character the permutation starts with, so the classes
    are visible in the picture.  Front nodes take the bright half --
    ``farbe := (color+8) MOD 16`` -- which is the depth cue.

    Only 1..7 and their bright twins 9..15 are usable: 0 is black and 8 is dark
    grey, and a graph big enough to run past the palette would land on them
    (``ikosa9`` has 812 nodes, hence colours up to 34).  Cycling through seven
    keeps the pairs intact and never draws a black ball.
    """
    entry = 1 + (color - 1) % 7
    return entry + 8 if front else entry


# -- the projection ---------------------------------------------------------

def project(g, width: int, height: int) -> dict[int, tuple[int, int, int]]:
    """Map each node to (screen x, screen y, depth z), like ``PmDisp.DrawEdges``:
    ``px = Scale(pos[1], Scale_X, Norm) + centre`` (component 3 = depth).

    The original used different ``Scale_X`` and ``Scale_Y`` because its pixels
    were not square (the ``AspectX=350 / AspectY=480`` correction made circles
    look round).  On today's square pixels the honest equivalent is a single,
    isotropic scale, so a sphere stays a sphere whatever the window shape and
    however much of the width the operator panel takes.
    """
    NORM = iv.NORM
    scale = (min(width, height) // 2) * 95 // 100
    cx, cy = width // 2, height // 2
    pts: dict[int, tuple[int, int, int]] = {}
    for nd in g.nodes.values():
        pos = nd.pos
        px = iv.scale(pos[0], scale, NORM) + cx
        py = iv.scale(-pos[1], scale, NORM) + cy
        z = pos[2] if g.dimensions >= 3 else 0
        pts[nd.num] = (px, py, z)
    return pts


# -- what is in the picture -------------------------------------------------

@dataclass(frozen=True)
class Edge:
    """A line between two nodes, and what its colour is saying.

    ``reason`` is why it looks the way it does -- "broken", "state", "operator"
    or "plain".  Nothing draws it; it is there so a test can ask.
    """

    a: Point
    b: Point
    rgb: RGB
    width: float
    front: bool
    reason: str = "plain"


@dataclass(frozen=True)
class Disc:
    """Which way the SPA wave runs along an edge.

    A disc at one sixth of the edge answers that: near this node for an input,
    near the neighbour for an output.  Colour alone (green) only says "on the
    path" -- the disc is the port's addition, PORT-GAPS section 6.
    """

    at: Point
    rgb: RGB
    incoming: bool


@dataclass(frozen=True)
class Digit:
    """The operator number at an edge midpoint, on a punched-out patch."""

    at: Point
    op: int
    rgb: RGB


@dataclass(frozen=True)
class Ball:
    """A node.  ``fill`` is None for a dead one -- background with a black rim."""

    at: Point
    radius: float
    fill: RGB | None
    ringed: bool = False          # active: a white ring one pixel further out
    label: str = ""


@dataclass
class Scene:
    """One frame, in drawing order.  Every layer covers the one before it."""

    edges: list[Edge] = field(default_factory=list)
    discs: list[Disc] = field(default_factory=list)
    digits: list[Digit] = field(default_factory=list)
    balls: list[Ball] = field(default_factory=list)
    radius: float = 0.0
    digit_size: float = 0.0
    digit_pad: float = 0.0        # half the punched-out patch behind a digit
    label_size: float = 0.0
    disc_radius: float = 0.0
    rim_width: float = 0.0
    ring_extra: float = 0.0


#: what goes inside the balls decides how big they are -- one ``names`` drives
#: both in ``PmDisp.DrawNodes``.  5 / 9 / 12 / 9 are the values ``TrueDisc`` was
#: called with, and they are radii, not diameters: ``TrueCircle(diam+1)`` rings
#: the ball one pixel further out, and a four-character perm in the 6x8 cell is
#: 24 px wide -- it only fits inside a ball of radius 12.
BALL_RADIUS = {0: 5, 1: 9, 2: 12, 3: 9}


def text_mode_for(name_mode: int, labels: bool, program: bool) -> int:
    """Which of ``0 none / 1 node# / 2 perm / 3 display`` to write in the balls."""
    if program:
        return 3
    if name_mode:
        return name_mode
    return 2 if labels else 0


def label_text(nd, text_mode: int) -> str:
    if text_mode == 1:
        return str(nd.num)
    if text_mode == 2:
        return nd.perm
    if text_mode == 3:
        return str(nd.state.display)
    return ""


def build(g, width: int, height: int, *, labels: bool = False,
          op_colors: bool = False, program: bool = False,
          name_mode: int = 0, operator_digits: bool = True) -> Scene:
    """Everything in one frame of *g*, in the order it has to be drawn."""
    pts = project(g, width, height)
    extent = picture_extent(width, height)
    have_ops = op_colors and g.n_operators > 0
    text_mode = text_mode_for(name_mode, labels, program)
    radius = mark_size(extent, BALL_RADIUS[text_mode])
    scene = Scene(radius=radius,
                  digit_size=mark_size(extent, 8),
                  digit_pad=mark_size(extent, 4),
                  label_size=mark_size(extent, 8),   # the 6x8 font cell
                  disc_radius=mark_size(extent, 3),
                  rim_width=stroke_width(extent, 0.8),
                  ring_extra=mark_size(extent, 1))

    for nd in g.ordered():
        xi, yi, zi = pts[nd.num]
        for link in nd.links:
            if link.to <= nd.num:
                continue                     # every undirected edge once
            xj, yj, zj = pts[link.to]
            front = (zi + zj) > 0
            broken = link.broken
            state = link.status if program else None
            op = link.op if have_ops and link.op else None

            if broken:
                rgb, reason = BROKEN, "broken"
                wide = True
            elif state is not None:
                rgb, reason = state_color(state, front), "state"
                wide = front
            elif op is not None:
                rgb, reason = operator_color(op, front), "operator"
                wide = front
            else:
                rgb = PLAIN_FRONT if front else PLAIN_BACK
                reason, wide = "plain", front
            scene.edges.append(Edge(
                (xi, yi), (xj, yj), rgb,
                stroke_width(extent, 1.1 if wide else 0.6), front, reason))

            if not broken and state in (L_INPUT, L_OUTPUT):
                incoming = state == L_INPUT
                at = ((5 * xi + xj) / 6, (5 * yi + yj) / 6) if incoming \
                    else ((5 * xj + xi) / 6, (5 * yj + yi) / 6)
                scene.discs.append(Disc(at, state_color(state, front), incoming))

            # ``IF (names>0) & (progsel # P_SPTA)`` (pmdisp.mod:94): one switch
            # for both, so "write nothing" leaves the links bare too.  The
            # P_SPTA half is Iridium, which iridium_scene draws instead.
            if operator_digits and text_mode and not broken and op:
                scene.digits.append(Digit(((xi + xj) / 2, (yi + yj) / 2), op,
                                          operator_color(op, front)))

    for nd in g.ordered():
        x, y, _z = pts[nd.num]
        lit = g.dimensions >= 3 and pts[nd.num][2] >= 0
        fill = None if nd.state.dead \
            else DOS_PALETTE[ball_color(nd.color, lit)]
        scene.balls.append(Ball((x, y), radius, fill, nd.state.active,
                                label_text(nd, text_mode)))
    return scene


def iridium_scene(g, width: int, height: int) -> Scene:
    """SIMONE's picture (``PmDisp`` with ``progsel = P_SPTA``).

    Node size encodes availability, the colour is the satellite's state, and the
    label is the node's own name when idle, otherwise the message number it
    carries.  No operator digits -- Iridium never sets ``opno``.
    """
    pts = project(g, width, height)
    extent = picture_extent(width, height)
    scene = Scene(label_size=mark_size(extent, 7))
    width_ = stroke_width(extent, 0.9)
    for nd in g.ordered():
        xi, yi, _zi = pts[nd.num]
        for link in nd.links:
            if link.to > nd.num:
                xj, yj, _zj = pts[link.to]
                scene.edges.append(Edge((xi, yi), (xj, yj), (150, 150, 160),
                                        width_, True, "iridium"))
    for nd in g.ordered():
        x, y, _z = pts[nd.num]
        # diameter = Scale(11, avail+1500, 10000), scaled to the picture
        radius = mark_size(extent, 11 * (nd.iri.avail + 1500) / 10000) / 2
        text = nd.perm if nd.color == YELLOW else str(nd.iri.message_num)
        scene.balls.append(Ball((x, y), radius, DOS_PALETTE[nd.color % 16],
                                label=text if text and text != "0" else ""))
    return scene


def operator_panel_rows(pm):
    """The lines of the operator editor, as ``(label, value, field)`` tuples.

    ``field`` is an :class:`~permuto.editor.OpField`, or ``None`` for the blank
    spacer line after the base -- matching the original's layout of a base
    line, a gap, then 6 operators of 3 cycles each, only the first cycle of
    each operator carrying an ``Op n`` label.  The cursor order comes from the
    editor, so the panel and the cursor cannot disagree.
    """
    rows = [("Base", pm.base, BASE_FIELD), ("", "", None)]
    for fld in fields_of(pm)[1:]:            # [0] is the base, already there
        label = f"Op {fld.op}" if fld.cyc == 1 else ""
        rows.append((label, value_of(pm, fld), fld))
    return rows
