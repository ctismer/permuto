"""The geodesic icosahedron generator, checked against the 1990 originals.

Node *numbering* cannot be reproduced (it was Thompson AWK's hash order), so
the check is graph isomorphism against `nod/ikosa1..12.nod` -- which is the
stronger statement: it says the port builds the same object, not merely the
same statistics.
"""

from collections import Counter

import pytest

from permuto import LimitExceeded
from permuto.formats import read_nod
from permuto.gen.geodesic import MAX_FREQ, geodesic, geodesic_labels, make_key

FREQUENCIES = list(range(1, 13))          # the twelve that exist as .nod files


# --- isomorphism for sphere triangulations -----------------------------
#
# In a triangulation every edge lies in exactly two faces, so once a single
# triangle is mapped the rest follows: walk each mapped edge to its second
# face and the third vertex is forced.  That makes the whole isomorphism
# determined by the image of one triangle, and there are only 12 degree-5
# nodes to try it from.

def adjacency(graph):
    return {n: set(v) for n, v in graph.items()}


def _third(adj, a, b, exclude):
    """The vertex completing triangle (a, b, ·) other than *exclude*.

    In a triangulation an edge has exactly two such vertices, so excluding one
    leaves exactly one -- anything else means this is not a triangulation.
    """
    common = (adj[a] & adj[b]) - {exclude}
    return common.pop() if len(common) == 1 else None


def _any_triangle(adj, a):
    """Some triangle through *a*, to seed the mapping from."""
    for b in adj[a]:
        for c in adj[a] & adj[b]:
            return a, b, c
    return None


def _try_map(adj1, adj2, seed1, seed2):
    """Extend the seed triangle correspondence over the whole graph."""
    mapping = dict(zip(seed1, seed2))
    if len(set(mapping.values())) != 3:
        return None
    queue = [(seed1[0], seed1[1], seed1[2]),
             (seed1[1], seed1[2], seed1[0]),
             (seed1[2], seed1[0], seed1[1])]
    seen = set()
    while queue:
        a, b, c = queue.pop()
        if (a, b, c) in seen:
            continue
        seen.add((a, b, c))
        if len(adj1[a]) != len(adj2[mapping[a]]):
            return None
        d = _third(adj1, a, b, c)
        if d is None:
            continue
        d2 = _third(adj2, mapping[a], mapping[b], mapping[c])
        if d2 is None:
            return None
        if d in mapping:
            if mapping[d] != d2:
                return None
        else:
            if d2 in mapping.values():
                return None
            mapping[d] = d2
        queue += [(a, d, b), (b, d, a)]
    return mapping if len(mapping) == len(adj1) else None


def isomorphic(adj1, adj2):
    if len(adj1) != len(adj2):
        return False
    if Counter(map(len, adj1.values())) != Counter(map(len, adj2.values())):
        return False
    a = min((n for n in adj1 if len(adj1[n]) == 5), default=min(adj1))
    seed = _any_triangle(adj1, a)
    if seed is None:                    # not a triangulation -> nothing to seed
        return False
    a, b, c = seed
    for a2 in (n for n in adj2 if len(adj2[n]) == len(adj1[a])):
        for b2 in adj2[a2]:
            for c2 in adj2[a2] & adj2[b2]:
                if _try_map(adj1, adj2, (a, b, c), (a2, b2, c2)):
                    return True
    return False


def as_adjacency(g):
    return {n: set(nd.neighbours) for n, nd in g.nodes.items()}


# --- the actual tests --------------------------------------------------

@pytest.mark.parametrize("freq", FREQUENCIES)
def test_matches_the_original_icosahedron_file(freq, nod_dir):
    original = nod_dir / f"ikosa{freq}.nod"
    if not original.exists():
        pytest.skip(f"{original.name} missing")
    ours = as_adjacency(geodesic(freq))
    theirs = adjacency(read_nod(original).links)
    assert isomorphic(ours, theirs), \
        f"frequency {freq}: generated graph differs from {original.name}"


@pytest.mark.parametrize("freq", FREQUENCIES)
def test_counts_follow_the_geodesic_formulas(freq):
    g = geodesic(freq)
    edges = sum(nd.nlink for nd in g.nodes.values()) // 2
    assert (g.nnodes, edges) == (10 * freq**2 + 2, 30 * freq**2)
    # only the twelve original corners keep degree 5; Euler then forces V-E+F=2
    assert Counter(nd.nlink for nd in g.nodes.values())[5] == 12
    assert all(nd.nlink in (5, 6) for nd in g.nodes.values())


def test_shared_edges_glue_faces_together():
    """The naming scheme's whole purpose: a node on a face boundary must get
    the same name from both faces, or the dome falls apart into 20 pieces.
    Frequency 1 is the icosahedron itself -- 12 nodes, not 20*3."""
    assert len(geodesic_labels(1)) == 12
    # a point halfway along the edge between corners 1 and 2 is 'ab' whether
    # it is reached from face (1,2,3) or face (1,2,4)
    assert make_key(1, 2, 3, 1, 1, 0) == make_key(1, 2, 4, 1, 1, 0) == "ab"


def test_labels_are_the_readable_form_the_author_wanted():
    """"Changed numbering to the use of character strings that show up
    nicely" -- barycentric coordinates written as repeated corner letters, so
    at frequency f a corner is its letter f times over."""
    assert geodesic_labels(1)[:12] == list("abcdefghijkl")
    labels = geodesic_labels(3)
    assert labels[:12] == [c * 3 for c in "abcdefghijkl"]   # the pure corners
    assert "aab" in labels and "abc" in labels              # edge and interior
    assert all(len(lab) == 3 for lab in labels)             # weights sum to freq
    assert set("".join(labels)) <= set("abcdefghijkl")


@pytest.mark.parametrize("freq", [0, -1, MAX_FREQ + 1])
def test_impossible_frequencies_are_refused(freq):
    with pytest.raises(LimitExceeded):
        geodesic(freq)
