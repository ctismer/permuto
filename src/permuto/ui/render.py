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


def paint(g, painter, width: int, height: int) -> None:
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QBrush, QColor, QPen

    pts = project(g, width, height)
    painter.setRenderHint(painter.RenderHint.Antialiasing, True)

    front_pen = QPen(QColor(90, 200, 255))
    front_pen.setWidthF(2.2)
    back_pen = QPen(QColor(70, 80, 120))
    back_pen.setWidthF(1.0)

    for nd in g.ordered():
        xi, yi, zi = pts[nd.num]
        for j in nd.links:
            if j <= nd.num:  # draw each undirected edge once
                continue
            xj, yj, zj = pts[j]
            painter.setPen(front_pen if (zi + zj) > 0 else back_pen)
            painter.drawLine(QPointF(xi, yi), QPointF(xj, yj))

    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(235, 235, 245)))
    for (x, y, z) in pts.values():
        painter.drawEllipse(QPointF(x, y), 3.5, 3.5)


def render_image(g, width: int = 800, height: int = 800):
    _ensure_gui_app()
    from PySide6.QtGui import QColor, QImage, QPainter

    img = QImage(width, height, QImage.Format.Format_ARGB32)
    img.fill(QColor(18, 18, 28))
    p = QPainter(img)
    paint(g, p, width, height)
    p.end()
    return img


def save_png(g, path, width: int = 800, height: int = 800):
    render_image(g, width, height).save(str(path), "PNG")
    return path
