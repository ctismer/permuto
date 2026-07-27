"""The two AWK tools beside the main pipeline: factorisation (trunc.awk) and
the "Vier Werte, 3 Plätze" graph (vierdrei.awk).

Both have their original output in nod/, and both use numeric labels, so the
edge sets can be compared directly against the 1990 files -- no isomorphism
argument needed.
"""

from collections import Counter

import pytest

from permuto import LimitExceeded
from permuto.core import Graph
from permuto.formats import read_nod
from permuto.gen.factorize import factorize, truncate_lines
from permuto.gen.vierdrei import (
    MODE_ALL,
    MODE_NEITHER,
    MODE_NO_DIFFERENT,
    MODE_NO_EQUAL,
    vierdrei,
)

PGL6 = ("123456", ["12", "+", "23", "+", "34", "+", "45", "+", "56"])


def edges_of(g):
    """Edge set keyed by the numeric labels, which is what the .nod holds."""
    return {tuple(sorted((int(g.nodes[n].perm), int(g.nodes[j].perm))))
            for n in g.nodes for j in g.nodes[n].neighbours}


def edges_of_nod(path):
    return {tuple(sorted((a, b))) for a, nbrs in read_nod(path).links.items()
            for b in nbrs}


# --- vierdrei ----------------------------------------------------------

def test_vierdrei_reproduces_the_original_file(nod_dir):
    original = nod_dir / "vierdrei.nod"
    if not original.exists():
        pytest.skip("vierdrei.nod missing")
    assert edges_of(vierdrei(MODE_ALL)) == edges_of_nod(original)


def test_vierdrei_is_the_hamming_graph():
    """Nodes differ in exactly one place, "für jeden Platz die drei anderen
    möglichen Werte" -- so 4^3 nodes of degree 3*3."""
    g = vierdrei(MODE_ALL)
    assert g.nnodes == 64
    assert set(nd.nlink for nd in g.nodes.values()) == {9}
    for nd in g.nodes.values():
        for j in nd.neighbours:
            differing = sum(a != b for a, b in zip(nd.perm, g.nodes[j].perm))
            assert differing == 1


@pytest.mark.parametrize("mode,nodes,dropped", [
    (MODE_ALL, 64, "nothing"),
    (MODE_NO_EQUAL, 60, "the 4 all-equal nodes 111..444"),
    (MODE_NO_DIFFERENT, 40, "the 4*3*2 = 24 all-different nodes"),
    (MODE_NEITHER, 36, "both groups"),
])
def test_filter_modes_drop_what_they_claim(mode, nodes, dropped):
    """The modes exist "um Struktur sehen zu können" in a graph the author
    found unreadable."""
    g = vierdrei(mode)
    assert g.nnodes == nodes, f"mode {mode} should drop {dropped}"
    labels = {nd.perm for nd in g.nodes.values()}
    if mode in (MODE_NO_EQUAL, MODE_NEITHER):
        assert not any(len(set(lab)) == 1 for lab in labels)
    if mode in (MODE_NO_DIFFERENT, MODE_NEITHER):
        assert not any(len(set(lab)) == 3 for lab in labels)


def test_unknown_mode_is_refused():
    with pytest.raises(LimitExceeded):
        vierdrei(4)


# --- factorisation -----------------------------------------------------

def test_factorising_pgl6_reproduces_pgl6_4(nod_dir):
    """"Dadurch wird pgl6 nach pgl6-4 faktorisiert" -- and pgl6-4.nod still
    holds the truncated labels themselves, not renumbered nodes."""
    original = nod_dir / "pgl6-4.nod"
    if not original.exists():
        pytest.skip("pgl6-4.nod missing")
    g = Graph.build(*PGL6, init=False)
    assert edges_of(factorize(g, 2)) == edges_of_nod(original)


def test_factorising_merges_nodes_sharing_a_prefix():
    g = Graph.build(*PGL6, init=False)
    assert g.nnodes == 720
    f = factorize(g, 2)
    assert f.nnodes == 30            # 6*5 distinct two-character prefixes
    assert {nd.perm for nd in f.nodes.values()} == \
        {a + b for a in "123456" for b in "123456" if a != b}
    # 720 nodes over 30 classes, and no class links to itself
    assert all(nd.num not in nd.neighbours for nd in f.nodes.values())


def test_truncate_lines_is_the_awk_transformation():
    """trunc.awk operates on .pg text so the result can go through num2."""
    assert truncate_lines(["123456 213456 123456 132456"], 2) == ["12 21 12 13"]
    assert truncate_lines(["abc def"], 1) == ["a d"]


def test_factorising_an_unlabelled_graph_is_refused(nod_dir):
    """A .nod load keeps only topology; the original would have collapsed the
    whole thing into one node without a word."""
    g = Graph.load_nod(nod_dir / "pgl3.nod", init=False)
    with pytest.raises(LimitExceeded):
        factorize(g, 2)
