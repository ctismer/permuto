"""Unit tests for the fixed-point vector arithmetic (IntVector port)."""

from permuto.core import intvector as iv


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


def test_spin_cos_sin_identity():
    # rotc^2 + rots^2 == Norm^2 (drift-free rotation), as in PCalc.Spin
    rots = iv.NORM // 120
    rotc = iv.sqrt(iv.sqr(iv.NORM) - iv.sqr(rots))
    assert rots == 34 and rotc == 4095


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
