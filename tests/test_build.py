"""The permutograph builder keeps permutation labels and operator numbers,
and its topology matches the recovered .nod files."""

from conftest import modula_dir

from permuto.core.graph import Graph
from permuto.formats import read_nod


def test_build_labels_and_operators():
    g = Graph.build("123", ["12", "+", "23"], init=False)
    assert g.nnodes == 6
    assert g.n_operators == 2
    n1 = g.nodes[1]
    assert n1.perm == "123"
    # op1 (swap places 1,2) -> "213" = node 3 ; op2 (swap 2,3) -> "132" = node 2
    assert {lk.to: lk.op for lk in n1.links} == {3: 1, 2: 2}


def test_build_topology_matches_nod():
    g = Graph.build("123", ["12", "+", "23"], init=False)
    base = read_nod(modula_dir() / "nod" / "pgl3.nod")
    for i in g.nodes:
        assert sorted(g.nodes[i].neighbours) == base.links[i]
