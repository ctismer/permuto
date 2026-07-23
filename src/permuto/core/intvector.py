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
from typing import List

MAXDIMEN = 8
NORM = 4096  # fixed-point "1.0"  (IntVector.Norm)

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


def new_vector() -> List[int]:
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


def zero_vector(vec: List[int]) -> None:
    for i in range(_dim):
        vec[i] = 0


def random_vector(vec: List[int], rng, rng_range: int) -> None:
    r = abs(rng_range)
    for i in range(_dim):
        vec[i] = (rng.randrange(2 * r) - r) if r else 0  # Lib.RANDOM(2*range)-range


def scale_vector(vec: List[int], mul: int, div: int) -> None:
    for i in range(_dim):
        vec[i] = scale(vec[i], mul, div)


def dot_product(vec: List[int], w: List[int]) -> None:
    # component-wise fixed-point multiply (name kept from the original)
    for i in range(_dim):
        vec[i] = scale(vec[i], w[i], NORM)


def add_vector(vec: List[int], w: List[int]) -> None:
    for i in range(_dim):
        vec[i] += w[i]


def sub_vector(vec: List[int], w: List[int]) -> None:
    for i in range(_dim):
        vec[i] -= w[i]


def vector_length(v: List[int]) -> int:
    s = 0
    for i in range(_dim):
        s += v[i] * v[i]
    return sqrt(s)


def norm_vector(v: List[int]) -> None:
    length = vector_length(v)
    if length == 0:
        v[1] = 1
        length = 1
    scale_vector(v, NORM, length)
