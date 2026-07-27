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


def test_spin_preserves_length():
    """``PCalc.Spin`` builds its rotation from ``rots = Norm/120`` and
    ``rotc = sqrt(Norm^2 - rots^2)``, so that sin^2 + cos^2 stays at Norm^2 and
    repeated spins neither shrink nor grow the figure."""
    from permuto.core import layout
    from permuto.core.graph import Graph, Node
    g = Graph()
    # at the scale the layout actually works in -- a few hundred units would
    # drown in the truncation of the fixed-point multiply
    g.nodes[1] = Node(num=1, pos=[iv.NORM // 2, iv.NORM // 4, iv.NORM // 3,
                                  0, 0, 0, 0, 0])
    g.set_dimensions(3)
    before = iv.vector_length(g.nodes[1].pos)
    for _ in range(50):
        layout.spin(g)
    after = iv.vector_length(g.nodes[1].pos)
    assert abs(after - before) < before // 1000, "the figure drifts as it spins"
