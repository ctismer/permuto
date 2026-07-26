"""Drawing — the port of ``PmDisp.DrawEdges``: orthographic 2-D projection of
the N-dimensional node positions, with a front/back depth cue.

Used by both the interactive PySide6 viewer and a headless offscreen renderer
(so we can produce a PNG without a display).
"""

from __future__ import annotations

import os
from typing import Dict, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QGuiApplication, QImage,
                           QPainter, QPen)

from ..core import intvector as iv
from ..core.graph import L_INPUT, L_LOCKED, L_OUTPUT
from ..editor import BASE_FIELD, fields_of, value_of


def _ensure_gui_app():
    app = QGuiApplication.instance()
    if app is None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QGuiApplication([])
    return app


def project(g, width: int, height: int) -> Dict[int, Tuple[int, int, int]]:
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
    pts: Dict[int, Tuple[int, int, int]] = {}
    for nd in g.nodes.values():
        pos = nd.pos
        px = iv.scale(pos[0], scale, NORM) + cx
        py = iv.scale(-pos[1], scale, NORM) + cy
        z = pos[2] if g.dimensions >= 3 else 0
        pts[nd.num] = (px, py, z)
    return pts


# distinct, reasonably colour-blind-friendly hues for operators 1..n
_PALETTE = [
    (90, 200, 255), (255, 150, 90), (140, 230, 120), (230, 120, 220),
    (240, 220, 90), (120, 190, 235), (250, 130, 150), (170, 220, 200),
]


def _op_color(opk: int, front: bool):
    r, g, b = _PALETTE[(opk - 1) % len(_PALETTE)]
    if not front:  # dim the back edges for depth
        r, g, b = r * 45 // 100, g * 45 // 100, b * 45 // 100
    return QColor(r, g, b)


def _state_color(state: int, front: bool):
    # LineStatus -> colour (PmDisp): input/output green, locked red, free grey
    if state in (L_INPUT, L_OUTPUT):
        r, g, b = 90, 220, 110
    elif state == L_LOCKED:
        r, g, b = 220, 80, 80
    else:  # L_FREE
        r, g, b = 80, 85, 100
    if not front:
        r, g, b = r * 50 // 100, g * 50 // 100, b * 50 // 100
    return QColor(r, g, b)


BACKGROUND = (18, 18, 28)   # picture background; shared with the viewer chrome


_PICTURE_PIXELS = 320   # the original picture area was 479 x 320 (pmdisp.def)

# One knob for the whole UI's apparent size.  A faithful mapping (1.0) puts
# every mark at the same fraction of the picture it had on the 479x320 original,
# but that reads a touch large on a modern display, so the default trims it.
# This is the single number to turn if things want to be bigger or smaller.
UI_SCALE = 0.62


def _scaled(height: int, picture_pixels: float) -> float:
    """A mark size (font, node), in the original's picture pixels, for today.

    Kept as an absolute count it would vanish in a large window, so it keeps the
    same fraction of the picture height (PORT-GAPS section 6), times UI_SCALE.
    Floored at 1 px so fonts never round to nothing.
    """
    return max(1.0, picture_pixels * height / _PICTURE_PIXELS * UI_SCALE)


INK = (0, 0, 0)     # PlotCenteredStr(px, py, str, 0) -- labels are always black


def _line(height: int, picture_pixels: float) -> float:
    """Like :func:`_scaled` but for pen widths, which may go below 1 px so that
    a busy sphere of edges does not turn into a solid blob."""
    return max(0.5, picture_pixels * height / _PICTURE_PIXELS * UI_SCALE)


def paint(g, painter, width: int, height: int, *,
          labels: bool = False, op_colors: bool = False,
          program: bool = False, name_mode: int = 0,
          operator_digits: bool = True) -> None:
    pts = project(g, width, height)
    painter.setRenderHint(painter.RenderHint.Antialiasing, True)

    front_pen = QPen(QColor(90, 200, 255))
    front_pen.setWidthF(_line(height, 1.1))
    back_pen = QPen(QColor(70, 80, 120))
    back_pen.setWidthF(_line(height, 0.6))
    have_ops = op_colors and g.n_operators > 0

    # edges, each undirected pair once; remember midpoints for the op digit
    digit_spots = []   # (x, y, op, front)
    disc_spots = []    # (x, y, colour) -- the direction disc of a wave edge
    for nd in g.ordered():
        xi, yi, zi = pts[nd.num]
        for idx, j in enumerate(nd.links):
            if j <= nd.num:
                continue
            xj, yj, zj = pts[j]
            front = (zi + zj) > 0
            broken = (idx + 1) in nd.state.broken
            if broken:
                pen = QPen(QColor(0, 0, 0))
                pen.setWidthF(_line(height, 1.1))
            elif program and idx < len(nd.state.lines):
                pen = QPen(_state_color(nd.state.lines[idx], front))
                pen.setWidthF(_line(height, 1.1 if front else 0.6))
            elif have_ops and idx < len(nd.opno):
                pen = QPen(_op_color(nd.opno[idx], front))
                pen.setWidthF(_line(height, 1.1 if front else 0.6))
            else:
                painter.setPen(front_pen if front else back_pen)
                pen = None
            if pen is not None:
                painter.setPen(pen)
            painter.drawLine(QPointF(xi, yi), QPointF(xj, yj))
            # Which way does the wave run?  A disc at 1/6 of the edge answers
            # that: near this node for an input, near the neighbour for an
            # output.  Colour alone (green) only says "on the path".
            if program and not broken and idx < len(nd.state.lines) \
                    and nd.state.lines[idx] in (L_INPUT, L_OUTPUT):
                if nd.state.lines[idx] == L_INPUT:
                    qx, qy = (5 * xi + xj) / 6, (5 * yi + yj) / 6
                else:
                    qx, qy = (5 * xj + xi) / 6, (5 * yj + yi) / 6
                disc_spots.append((qx, qy, _state_color(nd.state.lines[idx], front)))
            if operator_digits and have_ops and not program and not broken \
                    and idx < len(nd.opno) and nd.opno[idx]:
                digit_spots.append(((xi + xj) / 2, (yi + yj) / 2,
                                    nd.opno[idx], front))

    # the direction discs, on top of the edges they belong to
    if disc_spots:
        disc_r = _scaled(height, 3)
        painter.setPen(Qt.NoPen)
        for x, y, colour in disc_spots:
            painter.setBrush(QBrush(colour))
            painter.drawEllipse(QPointF(x, y), disc_r, disc_r)

    # operator number at each edge midpoint, on a punched-out background patch
    if digit_spots:
        digit_font = QFont("Menlo")
        digit_font.setPixelSize(int(_scaled(height, 8)))
        painter.setFont(digit_font)
        pad = _scaled(height, 4)
        for x, y, op, front in digit_spots:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(*BACKGROUND)))
            painter.drawRect(QRectF(x - pad, y - pad * 1.25, pad * 2, pad * 2.5))
            painter.setPen(_op_color(op, front))
            painter.drawText(QRectF(x - pad, y - pad * 1.25, pad * 2, pad * 2.5),
                             Qt.AlignCenter, str(op))

    # What goes inside the balls decides how big they are -- one `names` drives
    # both in ``PmDisp.DrawNodes``.
    text_mode = name_mode if name_mode else (2 if labels else 0)
    if program:
        text_mode = 3
    # 5 / 9 / 12 / 9 are the values ``TrueDisc`` was called with, and they are
    # radii, not diameters: ``TrueCircle(diam+1)`` rings the ball one pixel
    # further out, and a four-character perm in the 6x8 cell is 24 px wide --
    # it only fits inside a ball of radius 12, which is where it was drawn.
    radius = _scaled(height, {0: 5, 1: 9, 2: 12, 3: 9}[text_mode])

    def ball_color(nd) -> int:
        """The palette entry a node's ball is filled with.

        ``color`` says which character the permutation starts with, so the
        classes are visible in the picture.  Front nodes take the bright half
        -- ``farbe := (color+8) MOD 16`` -- which is the depth cue.

        Only 1..7 and their bright twins 9..15 are usable: 0 is black and 8 is
        dark grey, and a graph big enough to run past the palette would land on
        them (``ikosa9`` has 812 nodes, hence colours up to 34).  Cycling
        through seven keeps the pairs intact and never draws a black ball.
        """
        colour = 1 + (nd.color - 1) % 7
        if g.dimensions >= 3 and pts[nd.num][2] >= 0:
            colour += 8
        return colour

    for nd in g.ordered():
        x, y, _z = pts[nd.num]
        if nd.state.dead:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(*BACKGROUND)))
            painter.drawEllipse(QPointF(x, y), radius, radius)
            pen = QPen(QColor(0, 0, 0))
            pen.setWidthF(_line(height, 0.8))
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(x, y), radius, radius)
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(*_DOS_PALETTE[ball_color(nd)])))
            painter.drawEllipse(QPointF(x, y), radius, radius)
        if nd.state.active:
            pen = QPen(QColor(255, 255, 255))
            pen.setWidthF(_line(height, 0.8))
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            ring = radius + _scaled(height, 1)
            painter.drawEllipse(QPointF(x, y), ring, ring)

    # labels inside the balls: node number / perm / SPA display value.  "we plot
    # text inside the balls, therefore black is a good choice" -- PmDisp
    if text_mode:
        label_font = QFont("Menlo")
        label_font.setPixelSize(int(_scaled(height, 8)))   # the 6x8 font cell
        painter.setFont(label_font)
        painter.setPen(QColor(*INK))
        for nd in g.ordered():
            if text_mode == 1:
                text = str(nd.num)
            elif text_mode == 2:
                text = nd.perm
            else:
                text = str(nd.state.display)
            if not text:
                continue
            x, y, _z = pts[nd.num]
            painter.drawText(
                QRectF(x - radius, y - radius, 2 * radius, 2 * radius),
                Qt.AlignCenter, str(text))


# The standard DOS 16-colour palette, by index -- Iridium/SIMONE colours nodes
# by these (Window.Yellow=14 idle, Blue=1 destination, Red=4 and NextColor for
# packets).
_DOS_PALETTE = [
    (0, 0, 0), (60, 60, 220), (0, 170, 0), (0, 170, 170),
    (210, 40, 40), (200, 0, 200), (170, 85, 0), (200, 200, 200),
    (110, 110, 120), (110, 110, 255), (85, 255, 85), (85, 255, 255),
    (255, 110, 110), (255, 120, 255), (245, 235, 90), (255, 255, 255),
]


def paint_iridium(g, painter, width: int, height: int) -> None:
    """Draw the Iridium/SIMONE network (``PmDisp`` with ``progsel = P_SPTA``).

    Node size encodes availability, the colour is the satellite's state
    (yellow idle, blue destination, else the packet's colour), and the label is
    the node's own name when idle, otherwise the message number it carries.
    No operator digits -- Iridium never sets ``opno``.
    """
    pts = project(g, width, height)
    painter.setRenderHint(painter.RenderHint.Antialiasing, True)

    pen = QPen(QColor(150, 150, 160))
    pen.setWidthF(_line(height, 0.9))
    painter.setPen(pen)
    for nd in g.ordered():
        xi, yi, _zi = pts[nd.num]
        for j in nd.links:
            if j > nd.num:
                xj, yj, _zj = pts[j]
                painter.drawLine(QPointF(xi, yi), QPointF(xj, yj))

    YELLOW = 14
    font = QFont("Menlo")
    font.setPixelSize(int(_scaled(height, 7)))
    painter.setFont(font)
    for nd in g.ordered():
        x, y, _z = pts[nd.num]
        # diameter = Scale(11, avail+1500, 10000), scaled to the picture
        diam = _scaled(height, 11 * (nd.iri.avail + 1500) / 10000)
        r = diam / 2
        colour = QColor(*_DOS_PALETTE[nd.color % 16])
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(colour))
        painter.drawEllipse(QPointF(x, y), r, r)
        # label: own name when idle (yellow), else the message number it carries
        text = nd.perm if nd.color == YELLOW else str(nd.iri.message_num)
        if text and text != "0":
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(QRectF(x - r, y - r, 2 * r, 2 * r),
                             Qt.AlignCenter, text)


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


def paint_operator_panel(pm, painter, x, y, height, *,
                         active_field=None, buffer_text=None):
    """Draw the operator table beside the picture.

    In the original this is permanently visible in permutograph mode; with
    ``active_field`` set it shows the edit cursor, and ``buffer_text`` is the
    digits being typed into that field.
    """
    font = QFont("Menlo")
    line_px = _scaled(height, 11)
    font.setPixelSize(int(line_px * 0.7))
    painter.setFont(font)
    for row, (label, value, field) in enumerate(operator_panel_rows(pm)):
        cy = y + row * line_px
        if label:
            painter.setPen(QColor(150, 155, 175))
            painter.drawText(QPointF(x, cy), label)
        if field is not None:
            shown = value
            editing = active_field is not None and field == active_field
            if editing and buffer_text is not None:
                shown = buffer_text
            painter.setPen(QColor(255, 230, 140) if editing
                           else QColor(215, 215, 230))
            painter.drawText(QPointF(x + line_px * 3, cy),
                             (shown or "·") + ("_" if editing else ""))


def render_image(g, width: int = 800, height: int = 800, **kw):
    _ensure_gui_app()
    img = QImage(width, height, QImage.Format.Format_ARGB32)
    img.fill(QColor(*BACKGROUND))
    p = QPainter(img)
    paint(g, p, width, height, **kw)
    p.end()
    return img


def save_png(g, path, width: int = 800, height: int = 800, **kw):
    render_image(g, width, height, **kw).save(str(path), "PNG")
    return path


def indexed_image(indices, palette):
    """Palette indices ``[y][x]`` plus an RGB table -> a QImage.

    A plain pixel writer: it knows nothing about what produced the indices.
    """
    _ensure_gui_app()
    height, width = len(indices), len(indices[0])
    img = QImage(width, height, QImage.Format.Format_ARGB32)
    rgb = [QColor(*c).rgb() for c in palette]
    for y, row in enumerate(indices):
        for x, c in enumerate(row):
            img.setPixel(x, y, rgb[c])
    return img
