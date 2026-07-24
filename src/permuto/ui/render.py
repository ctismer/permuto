"""Drawing — the port of ``PmDisp.DrawEdges``: orthographic 2-D projection of
the N-dimensional node positions, with a front/back depth cue.

Used by both the interactive PySide6 viewer and a headless offscreen renderer
(so we can produce a PNG without a display).
"""

from __future__ import annotations

import os
from typing import Dict, Tuple

from ..core import intvector as iv


def _ensure_gui_app():
    from PySide6.QtGui import QGuiApplication

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
    from PySide6.QtGui import QColor

    r, g, b = _PALETTE[(opk - 1) % len(_PALETTE)]
    if not front:  # dim the back edges for depth
        r, g, b = r * 45 // 100, g * 45 // 100, b * 45 // 100
    return QColor(r, g, b)


def _state_color(state: int, front: bool):
    # LineStatus -> colour (PmDisp): input/output green, locked red, free grey
    from ..core.graph import L_INPUT, L_LOCKED, L_OUTPUT
    from PySide6.QtGui import QColor

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


def _line(height: int, picture_pixels: float) -> float:
    """Like :func:`_scaled` but for pen widths, which may go below 1 px so that
    a busy sphere of edges does not turn into a solid blob."""
    return max(0.5, picture_pixels * height / _PICTURE_PIXELS * UI_SCALE)


def paint(g, painter, width: int, height: int, *,
          labels: bool = False, op_colors: bool = False,
          program: bool = False, name_mode: int = 0,
          operator_digits: bool = True) -> None:
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QBrush, QColor, QFont, QPen

    pts = project(g, width, height)
    painter.setRenderHint(painter.RenderHint.Antialiasing, True)

    front_pen = QPen(QColor(90, 200, 255))
    front_pen.setWidthF(_line(height, 1.1))
    back_pen = QPen(QColor(70, 80, 120))
    back_pen.setWidthF(_line(height, 0.6))
    have_ops = op_colors and g.n_operators > 0

    # edges, each undirected pair once; remember midpoints for the op digit
    digit_spots = []   # (x, y, op, front)
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
            if operator_digits and have_ops and not program and not broken \
                    and idx < len(nd.opno) and nd.opno[idx]:
                digit_spots.append(((xi + xj) / 2, (yi + yj) / 2,
                                    nd.opno[idx], front))

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

    # nodes: diameter follows the name mode, dead ones hollow, active ringed
    diam = {0: 5, 1: 9, 2: 12, 3: 9}.get(name_mode, 5)
    radius = _scaled(height, diam) / 2
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
            painter.setBrush(QBrush(QColor(235, 235, 245)))
            painter.drawEllipse(QPointF(x, y), radius, radius)
        if nd.state.active:
            pen = QPen(QColor(255, 255, 255))
            pen.setWidthF(_line(height, 0.8))
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(x, y), radius + 1, radius + 1)

    # labels inside/next to the balls: node number / perm / SPA display value
    text_mode = name_mode if name_mode else (2 if labels else 0)
    if program:
        text_mode = 3
    if text_mode:
        label_font = QFont("Menlo")
        label_font.setPixelSize(int(_scaled(height, 7)))
        painter.setFont(label_font)
        painter.setPen(QColor(215, 215, 230))
        for nd in g.nodes.values():
            if text_mode == 1:
                text = str(nd.num)
            elif text_mode == 2:
                text = nd.perm
            else:
                text = str(nd.state.display)
            if text:
                x, y, _z = pts[nd.num]
                painter.drawText(QPointF(x + radius + 2, y - radius), str(text))


def operator_panel_rows(pm):
    """The lines of the operator editor, as ``(label, value, field)`` tuples.

    ``field`` is ``('base',)`` or ``('op', i, j)`` (1-based), or ``None`` for
    the blank spacer line after the base -- matching the original's layout of a
    base line, a gap, then 6 operators of 3 cycles each, only the first cycle
    of each operator carrying an ``Op n`` label.
    """
    rows = [("Base", pm.base, ("base",)), ("", "", None)]
    for i in range(len(pm.optable)):
        for j in range(len(pm.optable[i])):
            label = f"Op {i + 1}" if j == 0 else ""
            rows.append((label, pm.optable[i][j], ("op", i + 1, j + 1)))
    return rows


def paint_operator_panel(pm, painter, x, y, height, *,
                         active_field=None, buffer_text=None):
    """Draw the operator table beside the picture.

    In the original this is permanently visible in permutograph mode; with
    ``active_field`` set it shows the edit cursor, and ``buffer_text`` is the
    digits being typed into that field.
    """
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor, QFont

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
    from PySide6.QtGui import QColor, QImage, QPainter

    img = QImage(width, height, QImage.Format.Format_ARGB32)
    img.fill(QColor(*BACKGROUND))
    p = QPainter(img)
    paint(g, p, width, height, **kw)
    p.end()
    return img


def save_png(g, path, width: int = 800, height: int = 800, **kw):
    render_image(g, width, height, **kw).save(str(path), "PNG")
    return path
