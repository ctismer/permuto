"""Port of ``trunc.awk`` / ``trunc2.awk`` (kr0te, 29.05.92) -- factorisation.

Truncating every permutation string to its first *n* characters merges all
nodes that agree on those places, collapsing a permutograph onto a coarser
one: "Beispiel : trunc 2 pgl6.pg -- Dadurch wird pgl6 nach pgl6-4
faktorisiert."

This is `denke.txt`'s "Zerlegung in Subpermutographen" made operational.  The
surviving `nod/pgl6-4.nod` is such a result and still carries the truncated
labels rather than node numbers -- `12 21 12 13 ...` -- because the original
pipeline ran ``num2`` only afterwards.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..errors import LimitExceeded

DEFAULT_PLACES = 2  # trunc.awk's fallback when the parameter is not a number


def truncate_lines(lines: Iterable[str], places: int = DEFAULT_PLACES) -> list[str]:
    """``trunc.awk`` itself: shorten every whitespace-separated field.

    Operates on ``.pg`` text, so the result can go straight into
    :func:`permuto.gen.number.number` the way ``permuto.bat`` did.
    """
    if places < 1:
        raise LimitExceeded("truncation length", places, 1, 255)
    return [" ".join(field[:places] for field in line.split()) for line in lines]


def factorize(g, places: int = DEFAULT_PLACES):
    """Collapse a permutograph by truncating its node labels.

    Nodes sharing a truncated label become one; edges follow, and an edge that
    would join a class to itself disappears.  Returns a new graph whose
    ``perm`` labels are the truncated ones.

    Raises :class:`~permuto.errors.LimitExceeded` if the graph has no labels to
    truncate -- a ``.nod`` load keeps only topology, so there is nothing to
    factor by, and the original would silently have produced one giant node.
    """
    from ..core.graph import Graph, Link, Node

    if not any(nd.perm for nd in g.nodes.values()):
        raise LimitExceeded("labelled nodes to factorise", 0, 1, g.nnodes)
    if places < 1:
        raise LimitExceeded("truncation length", places, 1, 255)

    classes: dict = {}
    for nd in g.ordered():
        classes.setdefault(nd.perm[:places], []).append(nd.num)
    number = {label: i for i, label in enumerate(sorted(classes), start=1)}
    of_node = {num: number[label]
               for label, members in classes.items() for num in members}

    out = Graph()
    out.n_operators = g.n_operators
    for label, num in number.items():
        out.nodes[num] = Node(num=num, perm=label)

    for nd in g.ordered():
        a = of_node[nd.num]
        for link in nd.links:
            b = of_node[link.to]
            if a == b or b in out.nodes[a].neighbours:
                continue
            out.nodes[a].links.append(Link(to=b, op=link.op))
    return out
