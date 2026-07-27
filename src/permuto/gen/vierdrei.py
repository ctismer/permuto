"""Port of ``vierdrei.awk`` (kr0te, 10.11.90) -- "Vier Werte, 3 Plätze".

A different family from the permutographs: nodes are all ``4³`` strings from
``111`` to ``444``, and two nodes are joined when they differ in exactly one
place -- "für jeden Platz die drei anderen möglichen Werte", so every node has
9 edges.  That is the Hamming graph H(3,4), and ``nod/vierdrei.nod`` is its
64-node, 288-edge output.

The author found it hard to look at -- "Der Graph sieht sehr merkwürdig aus.
Wir bilden daher Teilgraphen um Struktur sehen zu können" -- hence the modes,
which drop the nodes whose three places are all equal and/or all different.
"""

from __future__ import annotations


from ..errors import LimitExceeded

VALUES = 4
PLACES = 3

MODE_ALL = 0            # everything
MODE_NO_EQUAL = 1       # drop the all-equal nodes (111, 222, ...)
MODE_NO_DIFFERENT = 2   # drop the all-different ones
MODE_NEITHER = 3        # both filters


def vierdrei_edges(mode: int = MODE_ALL) -> list[tuple[str, str]]:
    """Edge list as sorted label pairs, following the original's loop exactly.

    The awk version builds edges directly rather than enumerating nodes ("Aufbau
    der Ecken brauchen wir nicht"), so a filtered mode simply never mentions the
    unwanted nodes.
    """
    if mode not in (MODE_ALL, MODE_NO_EQUAL, MODE_NO_DIFFERENT, MODE_NEITHER):
        raise LimitExceeded("vierdrei mode", mode, MODE_ALL, MODE_NEITHER)

    drop_equal = mode in (MODE_NO_EQUAL, MODE_NEITHER)
    drop_different = mode in (MODE_NO_DIFFERENT, MODE_NEITHER)

    edges = set()
    for a in range(1, VALUES):
        for b in range(a + 1, VALUES + 1):
            for j in range(1, VALUES + 1):
                for k in range(1, VALUES + 1):
                    take = True
                    if drop_equal:
                        take &= not ((a == j and j == k) or (b == j and j == k))
                    if drop_different:
                        take &= (((a == j) or (j == k) or (k == a))
                                 and ((b == j) or (j == k) or (k == b)))
                    if not take:
                        continue
                    for u, v in ((f"{a}{j}{k}", f"{b}{j}{k}"),
                                 (f"{j}{a}{k}", f"{j}{b}{k}"),
                                 (f"{j}{k}{a}", f"{j}{k}{b}")):
                        edges.add((u, v) if u <= v else (v, u))
    return sorted(edges)


def vierdrei(mode: int = MODE_ALL):
    """Build the graph as a :class:`~permuto.core.graph.Graph`, labels kept."""
    from ..core.graph import Graph, Link, Node

    edges = vierdrei_edges(mode)
    labels = sorted({u for e in edges for u in e})
    number = {lab: i for i, lab in enumerate(labels, start=1)}

    g = Graph()
    for lab, num in number.items():
        g.nodes[num] = Node(num=num, perm=lab)
    for u, v in edges:
        g.nodes[number[u]].links.append(Link(to=number[v]))
        g.nodes[number[v]].links.append(Link(to=number[u]))
    for nd in g.nodes.values():
        nd.links.sort(key=lambda link: link.to)
    return g
