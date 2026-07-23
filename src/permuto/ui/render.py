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
    """Map each node to (screen x, screen y, depth z), like PmDisp:
    ``px = Scale(pos[1], Scale_X, Norm) + centre`` (component 3 = depth)."""
    NORM = iv.NORM
    sx = (width // 2) * 95 // 100
    sy = (height // 2) * 95 // 100
    cx, cy = width // 2, height // 2
    pts: Dict[int, Tuple[int, int, int]] = {}
    for nd in g.nodes.values():
        pos = nd.pos
        px = iv.scale(pos[0], sx, NORM) + cx
        py = iv.scale(-pos[1], sy, NORM) + cy
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


def paint(g, painter, width: int, height: int, *,
          labels: bool = False, op_colors: bool = False,
          program: bool = False) -> None:
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QBrush, QColor, QFont, QPen

    pts = project(g, width, height)
    painter.setRenderHint(painter.RenderHint.Antialiasing, True)

    front_pen = QPen(QColor(90, 200, 255))
    front_pen.setWidthF(2.2)
    back_pen = QPen(QColor(70, 80, 120))
    back_pen.setWidthF(1.0)
    have_ops = op_colors and g.n_operators > 0

    for nd in g.ordered():
        xi, yi, zi = pts[nd.num]
        for idx, j in enumerate(nd.links):
            if j <= nd.num:  # draw each undirected edge once
                continue
            xj, yj, zj = pts[j]
            front = (zi + zj) > 0
            if program and idx < len(nd.state.lines):
                pen = QPen(_state_color(nd.state.lines[idx], front))
                pen.setWidthF(2.6 if front else 1.3)
                painter.setPen(pen)
            elif have_ops and idx < len(nd.opno):
                pen = QPen(_op_color(nd.opno[idx], front))
                pen.setWidthF(2.2 if front else 1.1)
                painter.setPen(pen)
            else:
                painter.setPen(front_pen if front else back_pen)
            painter.drawLine(QPointF(xi, yi), QPointF(xj, yj))

    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(235, 235, 245)))
    for (x, y, z) in pts.values():
        painter.drawEllipse(QPointF(x, y), 3.5, 3.5)

    if labels or program:
        painter.setPen(QColor(215, 215, 230))
        painter.setFont(QFont("Menlo", 9))
        for nd in g.nodes.values():
            text = str(nd.state.display) if program else nd.perm
            if text:
                x, y, _z = pts[nd.num]
                painter.drawText(QPointF(x + 6, y - 6), str(text))


def render_image(g, width: int = 800, height: int = 800, **kw):
    _ensure_gui_app()
    from PySide6.QtGui import QColor, QImage, QPainter

    img = QImage(width, height, QImage.Format.Format_ARGB32)
    img.fill(QColor(18, 18, 28))
    p = QPainter(img)
    paint(g, p, width, height, **kw)
    p.end()
    return img


def save_png(g, path, width: int = 800, height: int = 800, **kw):
    render_image(g, width, height, **kw).save(str(path), "PNG")
    return path
