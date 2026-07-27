"""Drawing -- putting a :class:`permuto.scene.Scene` on a ``QPainter``.

What is *in* the picture is decided in :mod:`permuto.scene`, which is UI-free:
the projection, the palette, which colour an edge is and why, where a direction
disc sits, how big a ball is.  This module is the part that genuinely needs Qt,
and it is deliberately dull -- five layers, each a loop over one list.

Used by both the interactive viewer and a headless offscreen renderer (so we
can produce a PNG without a display).
"""

from __future__ import annotations

import os

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetricsF,
                           QGuiApplication, QImage, QPainter, QPen)

from .. import scene
from ..scene import (BACKGROUND, INK, Scene, mark_size, operator_panel_rows,
                     project, stroke_width)

# Names the viewer and the tests reach for; the values live in permuto.scene.
_scaled = mark_size
_line = stroke_width
_DOS_PALETTE = scene.DOS_PALETTE
UI_SCALE = scene.UI_SCALE

__all__ = ["project", "paint", "paint_iridium", "operator_panel_rows",
           "operator_panel_width", "paint_operator_panel", "render_image",
           "save_png", "indexed_image", "BACKGROUND", "INK", "draw_scene"]


def _ensure_gui_app():
    app = QGuiApplication.instance()
    if app is None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QGuiApplication([])
    return app


def _pen(rgb, width: float) -> QPen:
    pen = QPen(QColor(*rgb))
    pen.setWidthF(width)
    return pen


def _menlo(pixels: float) -> QFont:
    font = QFont("Menlo")
    font.setPixelSize(int(pixels))
    return font


# -- the five layers, in drawing order --------------------------------------

def _draw_edges(sc: Scene, painter) -> None:
    for e in sc.edges:
        painter.setPen(_pen(e.rgb, e.width))
        painter.drawLine(QPointF(*e.a), QPointF(*e.b))


def _draw_discs(sc: Scene, painter) -> None:
    """The direction discs, on top of the edges they belong to."""
    if not sc.discs:
        return
    painter.setPen(Qt.PenStyle.NoPen)
    for d in sc.discs:
        painter.setBrush(QBrush(QColor(*d.rgb)))
        painter.drawEllipse(QPointF(*d.at), sc.disc_radius, sc.disc_radius)


def _draw_digits(sc: Scene, painter) -> None:
    """The operator number at each edge midpoint, on a punched-out patch of
    background -- so it stays readable where the edge runs under it."""
    if not sc.digits:
        return
    painter.setFont(_menlo(sc.digit_size))
    pad = sc.digit_pad
    for d in sc.digits:
        box = QRectF(d.at[0] - pad, d.at[1] - pad * 1.25, pad * 2, pad * 2.5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(*BACKGROUND)))
        painter.drawRect(box)
        painter.setPen(QColor(*d.rgb))
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, str(d.op))


def _draw_balls(sc: Scene, painter) -> None:
    """The nodes: a filled disc, hollow if dead, ringed white if active."""
    for b in sc.balls:
        at = QPointF(*b.at)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(*(b.fill or BACKGROUND))))
        painter.drawEllipse(at, b.radius, b.radius)
        if b.fill is None:                      # dead: background, black rim
            painter.setPen(_pen((0, 0, 0), sc.rim_width))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(at, b.radius, b.radius)
        if b.ringed:
            painter.setPen(_pen(scene.RING, sc.rim_width))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            ring = b.radius + sc.ring_extra
            painter.drawEllipse(at, ring, ring)


def _draw_labels(sc: Scene, painter) -> None:
    """Node number / perm / SPA display value, inside the ball.  "we plot text
    inside the balls, therefore black is a good choice" -- PmDisp."""
    if not any(b.label for b in sc.balls):
        return
    painter.setFont(_menlo(sc.label_size))
    painter.setPen(QColor(*INK))
    for b in sc.balls:
        if not b.label:
            continue
        x, y = b.at
        r = b.radius
        painter.drawText(QRectF(x - r, y - r, 2 * r, 2 * r),
                         Qt.AlignmentFlag.AlignCenter, b.label)


def draw_scene(sc: Scene, painter) -> None:
    """Every layer of *sc*, in the order each covers the one below it."""
    painter.setRenderHint(painter.RenderHint.Antialiasing, True)
    _draw_edges(sc, painter)
    _draw_discs(sc, painter)
    _draw_digits(sc, painter)
    _draw_balls(sc, painter)
    _draw_labels(sc, painter)


def paint(g, painter, width: int, height: int, **kw) -> None:
    """Draw *g* onto *painter* -- see :func:`permuto.scene.build` for the
    switches."""
    draw_scene(scene.build(g, width, height, **kw), painter)


def paint_iridium(g, painter, width: int, height: int) -> None:
    """Draw the Iridium/SIMONE network -- see :func:`permuto.scene.iridium_scene`."""
    draw_scene(scene.iridium_scene(g, width, height), painter)


# -- the operator panel beside the picture ----------------------------------

def _panel_metrics(pm, height):
    """Row height, font, where the value column starts, and how wide it gets."""
    line_px = mark_size(height, 11)
    font = _menlo(line_px * 0.7)
    fm = QFontMetricsF(font)
    widest = max((fm.horizontalAdvance((value or "·") + "_")   # + the cursor
                  for _, value, field in operator_panel_rows(pm)
                  if field is not None), default=0.0)
    # one character clear of the label column: "Op 10" and an eight-place base
    # were touching at line_px * 3
    value_x = line_px * 3 + fm.horizontalAdvance("0")
    return line_px, font, value_x, widest


def operator_panel_width(pm, height) -> float:
    """How much of the window to leave beside the picture for the table.

    Measured from what is in it -- the label column, the widest cycle, room for
    the edit cursor, and a margin either side.  It used to be a flat 260 px
    whatever the table held, two thirds of it empty, and the picture paid.
    """
    line_px, _font, value_x, widest = _panel_metrics(pm, height)
    return 2 * line_px + value_x + widest


def paint_operator_panel(pm, painter, x, y, height, *,
                         active_field=None, buffer_text=None):
    """Draw the operator table beside the picture, *x* being the left edge of
    the room :func:`operator_panel_width` asked for.

    In the original this is permanently visible in permutograph mode; with
    ``active_field`` set it shows the edit cursor, and ``buffer_text`` is the
    digits being typed into that field.
    """
    line_px, font, value_x, _widest = _panel_metrics(pm, height)
    painter.setFont(font)
    x += line_px                                  # the left margin
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
            painter.drawText(QPointF(x + value_x, cy),
                             (shown or "·") + ("_" if editing else ""))


# -- offscreen --------------------------------------------------------------

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
