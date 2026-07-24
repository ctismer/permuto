"""Layout-engine behaviour: normalize centres & scales, and the relaxation
makes the embedding dimension "fall" toward the object's true dimension."""

from conftest import modula_dir

from permuto.core import intvector as iv
from permuto.core import layout
from permuto.core.graph import Graph


def test_normalize_centres_and_scales():
    path = modula_dir() / "nod" / "wuerfel.nod"
    g = Graph.load_nod(path, dimensions=3, seed=1)
    layout.normalize(g)
    iv.set_dimensions(3)
    # centroid ~ 0
    for d in range(3):
        c = sum(nd.pos[d] for nd in g.nodes.values())
        assert abs(c) <= 5 * g.nnodes
    # max length ~ NORM
    mx = max(iv.vector_length(nd.pos) for nd in g.nodes.values())
    assert abs(mx - iv.NORM) <= iv.NORM // 10


def test_dimension_falls_to_true_dimension():
    # the icosahedron (42 nodes) is genuinely 3-D; relaxed from 8-D it falls to 3-D
    path = modula_dir() / "nod" / "ikosa2.nod"
    g = Graph.load_nod(path, dimensions=iv.MAXDIMEN, seed=1)
    assert g.dimensions == 8
    for _ in range(800):
        layout.relax_step(g, alg="rubber")
        if g.dimensions <= 3:
            break
    assert g.dimensions <= 3, f"icosahedron stuck at {g.dimensions}"
