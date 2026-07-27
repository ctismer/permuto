"""Faithful port of ``IntVector`` (intvecto.def / intvecto.mod).

Integer **fixed-point** vector arithmetic. ``NORM`` (= 4096) is treated as
``1.0``.  Vectors are plain Python lists of length ``MAXDIMEN``; operations
act on the first ``get_dimensions()`` components (the original keeps
``Dimensions`` module-local, accessed via Set/GetDimensions -- mirrored here).

Notes on fidelity:
* ``scale`` truncates toward zero (the TopSpeed ``MacFns.LI_DIV_I`` macro maps
  to the CPU integer divide) -- matters for negative coordinates.
* ``Sqrt`` is the integer floor sqrt (``Lib1.Root``); ``Sqr`` is ``x*x``.
* ``random_vector`` takes an explicit RNG: the original ``Lib.RANDOM`` is a
  source-less TopSpeed routine, so absolute positions are not bit-reproducible
  -- but the layout *algorithm* is, and the emergent shape is the same.
"""

from __future__ import annotations

import math

MAXDIMEN = 8

# The fixed-point unit ("1.0").  The original used 4096 = 2**12: coordinates
# were 16-bit signed INTEGER, and Normalize kept the figure within +-Norm, so
# 12 bits held the value and the upper ~4 bits (3 magnitude + sign) were
# head-room for summing neighbour vectors in Contract before re-normalizing.
# That head-room is moot now that arithmetic is unbounded (see the note below),
# and 4096 also *caps the resolution* at ~12 bits, which is why the layout still
# looked "16-bit".  Raised to 2**24 for genuinely fine relaxation and
# projection; it is a clean global scale factor (Spin, Punish, Squeeze, Contract
# all use it as a ratio), so the shapes are unchanged, only smoother.
#
# Why 2**24 and not higher: it stays inside 32-bit for a future port to C/JS.
# Coordinates are +-NORM, and Contract accumulates up to ~8 neighbour vectors
# before Normalize, so ~8*NORM = 2**27 must fit a signed 32-bit int (it does).
# Squares in VectorLength reach 8*NORM**2 = 2**51, which needs a 64-bit
# intermediate -- exactly what the original did (I_MUL_I -> LONGINT).
#
# The fine resolution does slow the dimension "fall" a little: the coarse 12-bit
# rounding used to snap tiny high-dimension components to zero, which happened to
# help the collapse -- an *unintended* side effect of the old fixed point, not a
# design.  Now Punish alone shrinks them, so ikosa2 reaches 3-D around step ~895
# instead of ~545.  It still falls, just smoother.  Sessions saved at this NORM
# are incompatible with the old 4096 scale, which is fine.
NORM = 1 << 24  # fixed-point "1.0"  (was IntVector.Norm = 4096)

# Integer width for the port: 32 bit, everywhere.
#
# TopSpeed's INTEGER was 16 bit, but Scale already computed through
# MacFns.LI_DIV_I, i.e. a LONGINT intermediate, and every coordinate is kept
# inside +-NORM by Normalize anyway -- so the narrow type never showed except
# in corners like Iri's seed positions.  Rather than reproduce 16-bit wraparound
# in some places and not others, the port is uniformly 32 bit.  Python ints do
# not overflow, so int32() is only needed where the original's overflow is part
# of the observable behaviour.
INT32_MIN, INT32_MAX = -0x80000000, 0x7FFFFFFF

_dim = 3  # Dimensions, module-local as in the original


def set_dimensions(dim: int) -> None:
    global _dim
    _dim = 3 if dim <= 0 else dim


def get_dimensions() -> int:
    return _dim


def new_vector() -> list[int]:
    return [0] * MAXDIMEN


def int32(x: int) -> int:
    """Wrap *x* into a 32-bit signed integer.

    Only for the few places where the original's overflow is visible behaviour
    rather than an accident; see the note on integer width above.
    """
    return (x + 0x80000000) % 0x100000000 - 0x80000000


def idiv(a: int, b: int) -> int:
    """Integer division truncating toward zero (C / CPU-IDIV semantics)."""
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


def scale(x: int, mul: int, div: int) -> int:
    """``Scale(x, mul, div) = x*mul DIV div`` (truncating toward zero)."""
    return idiv(x * mul, div)


def sqr(x: int) -> int:
    return x * x


def sqrt(x: int) -> int:
    return math.isqrt(x) if x > 0 else 0


def zero_vector(vec: list[int]) -> None:
    for i in range(_dim):
        vec[i] = 0


def random_vector(vec: list[int], rng, rng_range: int) -> None:
    r = abs(rng_range)
    for i in range(_dim):
        vec[i] = (rng.randrange(2 * r) - r) if r else 0  # Lib.RANDOM(2*range)-range


def scale_vector(vec: list[int], mul: int, div: int) -> None:
    for i in range(_dim):
        vec[i] = scale(vec[i], mul, div)


def dot_product(vec: list[int], w: list[int]) -> None:
    # component-wise fixed-point multiply (name kept from the original)
    for i in range(_dim):
        vec[i] = scale(vec[i], w[i], NORM)


def add_vector(vec: list[int], w: list[int]) -> None:
    for i in range(_dim):
        vec[i] += w[i]


def sub_vector(vec: list[int], w: list[int]) -> None:
    for i in range(_dim):
        vec[i] -= w[i]


def vector_length(v: list[int]) -> int:
    s = 0
    for i in range(_dim):
        s += v[i] * v[i]
    return sqrt(s)


def norm_vector(v: list[int]) -> None:
    length = vector_length(v)
    if length == 0:
        v[1] = 1
        length = 1
    scale_vector(v, NORM, length)
