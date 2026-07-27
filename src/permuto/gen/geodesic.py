"""Port of ``makeikos.awk`` (kr0te, 08.11.90 / 02.05.92) -- geodesic icosahedra.

Each face of an icosahedron is subdivided into ``freq²`` small triangles and
the result inflated onto the sphere, giving the familiar geodesic dome: a
graph with ``10·freq² + 2`` nodes, ``30·freq²`` edges and ``20·freq²`` faces,
in which exactly the twelve original corners keep degree 5 while every new
node has degree 6.

The trick that makes the faces fit together is the node naming.  A node inside
face ``(a, b, c)`` is named by its barycentric coordinates, written out as
repeated corner letters::

                   ccc   ccd   cdd   ddd
                acc   bcc   bcd   bdd
             aac   abc   bbc   bbd
          aaa   aab   abb   bbb

Because the corners of a face are always taken in ascending order, a node on a
shared edge gets the same name from both faces and the two triangles glue
themselves together -- the author's own explanation: "es muß der Randbereich
der Dreiecke, der ja mehrmals berechnet wird, immer die gleichen Namen haben,
damit die Dreiecke nachher auch zusammenhängen."

**Node numbering is not reproducible.** The original numbered nodes in the
order they fell out of ``for (tr in Tri)`` / ``for (i in Edges)``, i.e. the
hash order of Thompson AWK's associative arrays.  That order is visible in the
legacy data -- in ``ikosa1.nod`` the first face's edges ``(a,b), (b,c), (a,c)``
come out as ``1 2 / 3 2 / 1 3``, which is neither sorted nor insertion order --
and cannot be recovered without TAWK's hash function.  We number
deterministically instead (corners first, then by name), which yields the same
graph up to relabelling; the tests check that against the original files.
"""

from __future__ import annotations


from ..errors import LimitExceeded

MAX_FREQ = 14  # 10*14^2+2 = 1962 nodes, just inside NodeMgr's MaxNodesTot

# The base icosahedron, exactly as init_iko() wires it: 12 corners, 30 edges.
ICOSAHEDRON_EDGES: tuple[tuple[int, int], ...] = (
    (1, 2), (2, 3), (3, 1),
    (1, 6), (1, 4), (2, 4), (2, 5), (3, 5), (3, 6),
    (1, 7), (4, 7), (6, 7), (2, 8), (4, 8), (5, 8), (3, 9), (5, 9), (6, 9),
    (4, 10), (7, 10), (8, 10), (5, 11), (8, 11), (9, 11), (6, 12), (9, 12), (7, 12),
    (10, 11), (11, 12), (12, 10),
)

_LETTERS = "abcdefghijkl"


def icosahedron_faces() -> list[tuple[int, int, int]]:
    """The 20 faces, as ascending corner triples.

    Found the way the original does it -- every triple whose three edges all
    exist -- which yields each face once, already sorted.
    """
    edges = {(min(a, b), max(a, b)) for a, b in ICOSAHEDRON_EDGES}
    corners = sorted({n for e in edges for n in e})
    faces = [
        (i, j, k)
        for x, i in enumerate(corners)
        for j in corners[x + 1:]
        for k in corners[corners.index(j) + 1:]
        if (i, j) in edges and (j, k) in edges and (i, k) in edges
    ]
    return faces


def make_key(a: int, b: int, c: int, na: int, nb: int, nc: int) -> str:
    """``make_key`` -- barycentric name, e.g. ``(1,2,3, 2,1,0)`` -> ``"aab"``.

    Zero-weight corners are left out, so a node on edge a-b is named the same
    whichever of the two adjoining faces produces it.
    """
    parts = [letter * n
             for letter, n in ((_LETTERS[a - 1], na),
                               (_LETTERS[b - 1], nb),
                               (_LETTERS[c - 1], nc)) if n > 0]
    return "".join(parts)


def _fill_face(a: int, b: int, c: int, freq: int) -> list[tuple[str, str]]:
    """``fill_triangle`` -- the upward sub-triangles of one face.

    The downward ones need no separate work: they are bounded by edges these
    already contribute.
    """
    out: list[tuple[str, str]] = []
    for i in range(freq):
        for j in range(freq - i):
            k1 = make_key(a, b, c, freq - i - j, i, j)
            k2 = make_key(a, b, c, freq - (i + 1) - j, i + 1, j)
            k3 = make_key(a, b, c, freq - i - (j + 1), i, j + 1)
            out += [(k1, k2), (k2, k3), (k1, k3)]
    return out


def geodesic_edges(freq: int = 1) -> list[tuple[str, str]]:
    """All edges of the geodesic icosahedron, as sorted label pairs."""
    if freq < 1:
        raise LimitExceeded("geodesic frequency", freq, 1, MAX_FREQ)
    if freq > MAX_FREQ:
        raise LimitExceeded("geodesic frequency", freq, 1, MAX_FREQ)
    seen: set[tuple[str, str]] = set()
    for a, b, c in icosahedron_faces():
        for u, v in _fill_face(a, b, c, freq):
            seen.add((u, v) if u <= v else (v, u))
    return sorted(seen)


def geodesic_labels(freq: int = 1) -> list[str]:
    """Node labels in the port's deterministic order: corners first, then the
    rest by name.  Corners are the single-letter-repeated names."""
    labels = {u for e in geodesic_edges(freq) for u in e}
    return sorted(labels, key=lambda s: (len(set(s)), s))


def geodesic(freq: int = 1):
    """Build the geodesic icosahedron as a :class:`~permuto.core.graph.Graph`.

    Labels are kept in ``Node.perm`` so the viewer can show them, the way
    ``makeikos.awk``'s second parameter asked for "the original unmapped node
    labels ... character strings that show up nicely".
    """
    from ..core.graph import Graph, Link, Node

    labels = geodesic_labels(freq)
    number: dict[str, int] = {lab: i for i, lab in enumerate(labels, start=1)}

    g = Graph()
    g.nnodes = len(labels)
    for lab, num in number.items():
        g.nodes[num] = Node(num=num, perm=lab)
    for u, v in geodesic_edges(freq):
        for a, b in ((number[u], number[v]), (number[v], number[u])):
            g.nodes[a].links.append(Link(to=b))
    for nd in g.nodes.values():
        nd.links.sort(key=lambda link: link.to)
        # colour by degree: the twelve original corners (5) stand out from the
        # subdivision nodes (6), which is what makes the icosahedron visible
        nd.color = 4 if nd.nlink == 5 else 7
    return g
