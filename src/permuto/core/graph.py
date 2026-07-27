"""Node / graph model — the port of ``NodeMgr`` data structures + ``ReadNodes``.

A permutograph is loaded from a ``.nod`` file into 1-based numbered nodes with
undirected, deduped, sorted adjacency (see ``formats.read_nod``).  Positions
are N-dimensional integer vectors; they start random and are relaxed by the
layout engine (``core.layout``).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import intvector as iv

# NOTE: ``formats`` is imported inside load_nod, not here: formats/plyfile.py
# needs Graph and Node, so a module-level import would close a cycle.


# LineStatus (NodeMgr): edge state used by the PmProgs programs / display
L_FREE, L_INPUT, L_OUTPUT, L_LOCKED = 0, 1, 2, 3

MAX_LINKS = 12   # NodeMgr.MaxLinks -- how many edges a node has room for


@dataclass
class NodeState:
    step: int = 0
    active: bool = False
    dead: bool = False
    sum: int = 0
    display: int = 0
    broken: set[int] = field(default_factory=set)  # 1-based link indices
    lines: list[int] = field(default_factory=list)  # LineStatus per link


@dataclass
class IriState:
    """``NodeMgr.IriStatus`` -- the satellite's state in Iridium/SIMONE mode.

    Carried on every node because the original declared it inside ``NodeType``
    and ``.ply`` therefore stores it, even for graphs that never run Iridium.
    ``avail`` is fixed point with 10000 = fully charged; node numbers are
    1-based with 0 meaning "none".
    """

    avail: int = 0
    avbak: int = 0
    target: int = 0
    tarbak: int = 0
    message_num: int = 0
    message_color: int = 0
    sender_repeat: int = 0
    sender_target: int = 0
    sender_color: int = 0


@dataclass
class Node:
    num: int
    pos: list[int] = field(default_factory=iv.new_vector)
    old: list[int] = field(default_factory=iv.new_vector)
    color: int = 7
    nlink: int = 0
    links: list[int] = field(default_factory=list)  # 1-based neighbour numbers
    opno: list[int] = field(default_factory=list)
    perm: str = ""
    state: NodeState = field(default_factory=NodeState)
    iri: IriState = field(default_factory=IriState)

    def remove_link(self, k: int) -> None:
        """Drop link *k* (1-based), keeping every per-link array aligned.

        ``PM.Disconnect`` shifted ``links`` and ``opno`` but left ``state.lines``
        and ``state.broken`` at their old indices, although they address the
        same link numbers -- so after a Disconnect the marks referred to
        different edges (``docs/PORT-GAPS.md`` section 0).  Everything indexed
        by link lives here now, and shifts together.
        """
        del self.links[k - 1]
        if k - 1 < len(self.opno):
            del self.opno[k - 1]
        self.nlink = len(self.links)
        if k - 1 < len(self.state.lines):
            del self.state.lines[k - 1]
        self.state.broken = {i if i < k else i - 1
                             for i in self.state.broken if i != k}


class Graph:
    def __init__(self) -> None:
        self.nodes: dict[int, Node] = {}
        self.nnodes: int = 0
        self.dimensions: int = 3
        self.n_operators: int = 0  # >0 when built with operator identity

    # -- construction --------------------------------------------------
    @classmethod
    def load_nod(cls, path, *, dimensions: int = iv.MAXDIMEN, seed: int = 0,
                 init: bool = True) -> "Graph":
        """Load topology only (permutation labels / operators are lost)."""
        from ..formats import read_nod

        base = read_nod(path)
        g = cls()
        g.nnodes = base.nnodes
        for num in sorted(base.links):
            nd = Node(num=num, links=list(base.links[num]))
            nd.nlink = len(nd.links)
            g.nodes[num] = nd
        g.set_dimensions(dimensions)
        # "colors simply derived from nodenumbers" (SetupPolytope) -- a .nod
        # file has no permutations to colour by, so the numbering has to do,
        # in blocks of 6 or, past 24 nodes, of 24. The original's own comment
        # on the second case: "awkward".
        block = 6 if g.nnodes <= 24 else 24
        for nd in g.nodes.values():
            nd.color = 1 + (nd.num - 1) // block
        if init:
            g.random_init(seed)
        return g

    @classmethod
    def build(cls, base: str, operators: list[str], *,
              dimensions: int = iv.MAXDIMEN, seed: int = 0,
              init: bool = True) -> "Graph":
        """Build the permutograph from a base + operators, keeping the
        permutation string per node and the operator number per edge."""
        from ..gen import all_permutations, neighbors, operator_groups

        perms = all_permutations(base)
        num = {p: i + 1 for i, p in enumerate(perms)}
        g = cls()
        g.nnodes = len(perms)
        g.n_operators = len(operator_groups(operators))
        for i, p in enumerate(perms, start=1):
            nd = Node(num=i, perm=p)
            # as PM does: the colour says which character the perm starts with
            nd.color = base.index(p[0]) + 1 if p else 7
            seen: dict[int, int] = {}
            for opk, nb in neighbors(p, operators):
                j = num.get(nb)
                if j is None or j == i or j in seen:
                    continue
                seen[j] = opk
                nd.links.append(j)
                nd.opno.append(opk)
            nd.nlink = len(nd.links)
            g.nodes[i] = nd
        g.set_dimensions(dimensions)
        if init:
            g.random_init(seed)
        return g

    @classmethod
    def from_pgd(cls, pgd_path, **kw) -> "Graph":
        from ..formats import read_pgd

        c = read_pgd(pgd_path)
        return cls.build(c.base, c.operators, **kw)

    # -- helpers -------------------------------------------------------
    def set_dimensions(self, dim: int) -> None:
        self.dimensions = dim
        iv.set_dimensions(dim)

    def ordered(self) -> list[Node]:
        return [self.nodes[i] for i in sorted(self.nodes)]

    # -- edges ---------------------------------------------------------
    # These were PM.FindLink / IsLinked / LinksAvail / Disconnect in the
    # original, but they ask nothing about permutations -- they are the link
    # lists, which is NodeMgr's business and therefore the graph's.
    def find_link(self, n1: int, n2: int) -> int:
        """``PM.FindLink`` -- 1-based index of the link n1->n2, or 0."""
        nd = self.nodes.get(n1)
        if nd is None:
            return 0
        for i, j in enumerate(nd.links, start=1):
            if j == n2:
                return i
        return 0

    def is_linked(self, n1: int, n2: int) -> bool:
        """``PM.IsLinked`` -- note a node counts as linked to itself."""
        if n1 == n2:
            return True
        return self.find_link(n1, n2) > 0

    def links_avail(self, n1: int, n2: int) -> bool:
        """``PM.LinksAvail`` -- "check if both have an empty slot"."""
        return (self.nodes[n1].nlink < MAX_LINKS
                and self.nodes[n2].nlink < MAX_LINKS)

    def disconnect(self, n1: int, n2: int) -> bool:
        """``PM.Disconnect`` -- remove the edge from both sides. True if gone."""
        if n1 == n2 or not self.is_linked(n1, n2):
            return False
        for a, b in ((n1, n2), (n2, n1)):
            k = self.find_link(a, b)
            if k:
                self.nodes[a].remove_link(k)
        return True

    def pack_nodes(self) -> int:
        """``NodeMgr.PackNodes`` + ``MoveNode`` -- squeeze out deleted nodes.

        A node marked ``num = 0`` (rejected by ``PolytopFilter``) is removed and
        the rest renumbered densely, with every neighbour's link list rewritten
        to match.  Returns how many nodes were dropped.
        """
        kept = [nd for nd in self.ordered() if nd.num != 0]
        if len(kept) == len(self.nodes):
            return 0
        renumber = {nd.num: i for i, nd in enumerate(kept, start=1)}
        self.nodes = {}
        for new_num, nd in enumerate(kept, start=1):
            nd.num = new_num
            # drop links to removed nodes, keeping opno aligned
            pairs = [(renumber[j], nd.opno[k] if k < len(nd.opno) else 0)
                     for k, j in enumerate(nd.links) if j in renumber]
            nd.links = [j for j, _ in pairs]
            nd.opno = [op for _, op in pairs]
            nd.nlink = len(nd.links)
            self.nodes[new_num] = nd
        dropped = self.nnodes - len(kept)
        self.nnodes = len(kept)
        return dropped

    def random_init(self, seed: int = 0) -> None:
        from . import layout

        iv.set_dimensions(self.dimensions)
        rng = random.Random(seed)
        for nd in self.ordered():
            iv.random_vector(nd.pos, rng, iv.NORM)
        layout.frame(self)
