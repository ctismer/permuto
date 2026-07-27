"""``kugel.mod`` -- a study in making 16 colours look like a lit sphere.

Not viewer code: this program shares nothing with the permutograph (it imports
only the DOS graphics library) and is ported for its own sake.  It is also the
one place in the whole 1995 source that uses floating point -- everything else
was deliberately integer-only -- so the port keeps floats here.

The question it asks is how to get a smooth, natural-looking gradient out of a
palette of 14 usable entries, and it answers it twice:

* **ordered dither** (the default) -- a fixed 4x4 pattern decides whether a
  pixel is rounded up to the next colour.  The threshold pattern is the one
  from the Windows 3.0 setup screen, which the author copied off the screen and
  wrote into the source as an ASCII picture; it is reproduced below.
* **Floyd-Steinberg** (``floyd=True``, the ``FLOYD`` argument in 1995) -- the
  rounding error of each pixel is carried into its neighbours, so the error
  cancels out over an area instead of forming bands.  Weights 3/8 above, 2/8
  above-left, 3/8 left, and "jedes Pixel ist genau einmal a, b oder c" -- the
  whole error is distributed, none is dropped.

The trick that makes it look seamless is geometric: only one octant is computed
and mirrored eight ways, and the loops start two pixels *before* the octant so
the error buffer is already charged when the visible part begins.  Without that
the octant boundaries would show as seams.

Brightness is ``acos(dist/radius) / (pi/2)``: 1.0 at the centre, 0 at the rim --
the elevation angle of the surface, linear in the angle rather than in the
cosine.  That is a choice about how it *looks*, not a physical light model.
"""

from __future__ import annotations

import math
import random

# "schwarz und weiß bleiben" -- entries 0 and 15 are left alone, so the ramp is
# 14 colours wide and the background stays a true black.
MIN_COLOR, MAX_COLOR = 1, 14
COLOR_STEPS = MAX_COLOR - MIN_COLOR + 1

FULL = 10000                      # brightness in fixed point, as in the original
WEIGHTS = [0] * (MAX_COLOR + 2)   # 1-based, WEIGHTS[c] = where colour c starts
for _c in range(MIN_COLOR, MAX_COLOR + 1):
    WEIGHTS[_c] = FULL // COLOR_STEPS * (_c - MIN_COLOR)
WEIGHTS[MAX_COLOR + 1] = FULL // COLOR_STEPS * COLOR_STEPS

# Shake: the Floyd-Steinberg pass adds noise of this amplitude before rounding,
# which breaks up what little banding the error diffusion leaves.
SHAKE = 3 * 600 // COLOR_STEPS

# The 4x4 ordered-dither thresholds, as bit positions (x MOD 4)*4 + (y MOD 4).
# Each level adds two more pixels to the ones already set:
#
#   o . . .   * . o .   * . * .   * . * .   * . * o   * o * *   * * * *
#   . . . .   . . . .   . o . .   . * . o   . * . *   . * . *   . * o *
#   . . o .   o . * .   * . * .   * . * .   * o * .   * * * o   * * * *
#   . . . .   . . . .   . . . o   . o . *   . * . *   . * . *   o * . *
_DITHER_STEPS = [(0, 10), (2, 8), (5, 15), (7, 13), (3, 9), (1, 11), (6, 12), (4, 14)]
DITHER: list[frozenset] = [frozenset()]
for _pair in _DITHER_STEPS:
    DITHER.append(frozenset(DITHER[-1] | set(_pair)))


def _palette() -> list[tuple[int, int, int]]:
    """``SetRgb`` -- the hand-mixed ramp, converted from 6-bit DAC to 8-bit.

    Red starts high and stays the strongest channel while blue climbs fastest
    from almost nothing, so the ramp runs deep red -> warm pink-white rather
    than through grey.  The sphere reads as *lit*, and that colour choice --
    not the dithering -- is what the study is about.
    """
    pal = [(0, 0, 0)] * 16
    pal[15] = (255, 255, 255)
    for c in range(MIN_COLOR, MAX_COLOR + 1):
        i = c - MIN_COLOR
        r, g, b = 22 + 31 * i // 10, 35 * i // 10, 3 + 38 * i // 10
        pal[c] = (min(255, r * 255 // 63), min(255, g * 255 // 63),
                  min(255, b * 255 // 63))
    return pal


PALETTE = _palette()


def _color_for(value: int) -> int:
    """The palette entry a brightness falls into (the original's linear scan)."""
    c = MIN_COLOR
    while c < MAX_COLOR and value >= WEIGHTS[c + 1]:
        c += 1
    return c


def render_sphere(radius: int = 200, width: int = 640, height: int = 480, *,
                  floyd: bool = False, seed: int = 0) -> list[list[int]]:
    """The sphere as palette indices, ``[y][x]``, 0 where nothing was drawn.

    *floyd* picks the error-diffusion pass instead of the ordered dither.  The
    original seeded ``Lib.RANDOM`` from the clock and that module's source is
    lost, so *seed* stands in for it -- the noise is the same idea, not the
    same numbers.
    """
    img = [[0] * width for _ in range(height)]
    x0, y0 = width // 2, height // 2
    rng = random.Random(seed)
    r = float(radius)
    r2 = r * r

    # errors of the row above, indexed by x; x runs down to y-2, hence the pad
    pad = 12
    above = [0] * (width + 2 * pad)
    for y in range(-2, radius + 1):
        x1 = int(math.sqrt(r2 - y * y))
        left = 0          # F_Hold: the error of the pixel just written
        carry = 0
        for x in range(y - 2, x1 + 1):
            dist = math.sqrt(float(x) * x + float(y) * y)
            arg = dist / r
            # ACos(1.0) was a library bug in 1991; the guard is kept because it
            # is also the right answer at the rim.
            bright = 0.0 if arg >= 1.0 else math.acos(arg) / (math.pi / 2)

            if floyd:
                # 3/8 above + 2/8 above-left + 3/8 left; the stored values are
                # already divided by 8 ("DIV 8 schon drin")
                carry = 3 * above[x + pad] + 2 * above[x - 1 + pad] + 3 * left
                carry += int(FULL * bright) - SHAKE + rng.randrange(2 * SHAKE)
                color = _color_for(carry)
                carry -= WEIGHTS[color]          # what this pixel could not show
                above[x - 1 + pad] = left        # written back one step behind
                left = carry // 8
            else:
                value = int(FULL * bright)
                color = _color_for(value)
                if color < MAX_COLOR:
                    span = (WEIGHTS[color + 1] - WEIGHTS[color]) // 8
                    bit = (x % 4) * 4 + (y % 4)
                    if bit in DITHER[(value - WEIGHTS[color]) // span]:
                        color += 1
                # the original also kept the error arrays up to date here, but
                # overwrote the accumulated value first, so those stores never
                # reached a pixel -- left out, the picture is identical

            if x >= y:      # one octant; the two pixels before it only charge
                for px, py in ((x0 - x, y0 - y), (x0 + x, y0 - y),
                               (x0 - x, y0 + y), (x0 + x, y0 + y),
                               (x0 - y, y0 - x), (x0 + y, y0 - x),
                               (x0 - y, y0 + x), (x0 + y, y0 + x)):
                    if 0 <= px < width and 0 <= py < height:
                        img[py][px] = color
    return img
