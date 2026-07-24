"""Unit tests for the fixed-point vector arithmetic (IntVector port)."""

import pytest

from permuto.core import intvector as iv


@pytest.fixture(autouse=True)
def restore_dimensions():
    """``Dimensions`` is module state in the original and in the port alike, so
    a test that changes it would otherwise leak into whatever runs next."""
    saved = iv.get_dimensions()
    yield
    iv.set_dimensions(saved)


def test_scale_truncates_toward_zero():
    assert iv.scale(7, 1, 2) == 3
    assert iv.scale(-7, 1, 2) == -3      # toward zero, not -4
    assert iv.scale(4096, 34, 4096) == 34


def test_sqrt_is_floor():
    assert iv.sqrt(16) == 4
    assert iv.sqrt(17) == 4
    assert iv.sqrt(0) == 0


def test_vector_length():
    iv.set_dimensions(2)
    assert iv.vector_length([3, 4, 0, 0, 0, 0, 0, 0]) == 5


def test_spin_rotation_is_drift_free():
    # PCalc.Spin builds a rotation from rots = Norm/120 (small-angle sine) and
    # rotc = sqrt(Norm^2 - rots^2).  The point is that sin^2 + cos^2 stays at
    # Norm^2 so repeated spins do not shrink or grow the figure.  Assert that
    # identity to within integer-sqrt truncation -- not the intermediate values.
    rots = iv.NORM // 120
    rotc = iv.sqrt(iv.sqr(iv.NORM) - iv.sqr(rots))
    hypot_sq = iv.sqr(rotc) + iv.sqr(rots)
    # rotc is the floor of the true cosine, so the sum is <= Norm^2 but within
    # the rounding of one unit in rotc: (rotc+1)^2 must exceed Norm^2.
    assert hypot_sq <= iv.sqr(iv.NORM)
    assert iv.sqr(rotc + 1) + iv.sqr(rots) > iv.sqr(iv.NORM)


def test_spin_preserves_length_approximately():
    from permuto.core import layout
    from permuto.core.graph import Graph, Node
    g = Graph()
    g.nnodes = 1
    g.nodes[1] = Node(num=1, pos=[1000, 500, 2000, 0, 0, 0, 0, 0])
    g.set_dimensions(3)
    before = iv.vector_length(g.nodes[1].pos)
    layout.spin(g)
    after = iv.vector_length(g.nodes[1].pos)
    assert abs(after - before) <= 3  # only fixed-point rounding
