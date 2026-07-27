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

# How many edges a node may have.  ``NodeMgr.MaxLinks`` was 12 because the
# links lived in a fixed array of that size and the operator table held six
# operators of at most two arms each (pm.def:56).  The array is a list now, so
# this is only a ceiling -- doubled, and PM derives its operator count from it
# rather than repeating the arithmetic.
MAX_LINKS = 24


@dataclass
class Link:
    """One end of one edge: where it goes, and what it is doing.

    An edge is stored twice, once at each end, and the two ends genuinely
    differ: the same edge is ``L_INPUT`` where the SPA wave enters and
    ``L_OUTPUT`` where it leaves, which is what the direction discs read.

    Everything an edge knows lives here.  It used to be spread over four
    containers sharing an index -- ``links``/``opno`` on the node and
    ``lines``/``broken`` on its state -- in *two* index conventions, ``broken``
    counting from 1 and ``lines`` from 0.  ``PM.Disconnect`` shifted the first
    pair and not the second, so after a disconnect the marks described other
    edges (``docs/PORT-GAPS.md`` section 0).  With one object there is no index
    left to get wrong.
    """

    to: int                      # the neighbour's number, 1-based
    op: int = 0                  # which operator made this edge, 0 if unknown
    status: int = L_FREE         # LineStatus, while a program runs
    broken: bool = False         # cut by hand in the program menu


@dataclass
class NodeState:
    step: int = 0
    active: bool = False
    dead: bool = False
    sum: int = 0
    display: int = 0


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
    links: list[Link] = field(default_factory=list)
    perm: str = ""
    state: NodeState = field(default_factory=NodeState)
    iri: IriState = field(default_factory=IriState)

    @property
    def nlink(self) -> int:
        """``NodeType.nlink`` -- the original had to carry the count beside a
        fixed array; here it is simply how many links there are."""
        return len(self.links)

    @property
    def neighbours(self) -> list[int]:
        """Just the node numbers, for the callers that want nothing else."""
        return [link.to for link in self.links]

    def remove_link(self, k: int) -> None:
        """Drop link *k* (1-based).  Everything that edge knew goes with it."""
        del self.links[k - 1]


class Graph:
    def __init__(self) -> None:
        self.nodes: dict[int, Node] = {}
        self.dimensions: int = 3
        self.n_operators: int = 0  # >0 when built with operator identity

    @property
    def nnodes(self) -> int:
        """``NodeMgr.NNodes`` -- how many nodes there are.

        The original had to count them beside a fixed array.  Here it is the
        length of the dict and nothing else: the two never disagreed, checked
        across load, build, collapse, Iridium's growth and pack_nodes.
        """
        return len(self.nodes)

    # -- construction --------------------------------------------------
    @classmethod
    def load_nod(cls, path, *, dimensions: int = iv.MAXDIMEN, seed: int = 0,
                 init: bool = True) -> "Graph":
        """Load topology only (permutation labels / operators are lost)."""
        from ..formats import read_nod

        base = read_nod(path)
        g = cls()
        for num in sorted(base.links):
            g.nodes[num] = Node(num=num,
                                links=[Link(to=j) for j in base.links[num]])
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
                nd.links.append(Link(to=j, op=opk))
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
        for i, link in enumerate(nd.links, start=1):
            if link.to == n2:
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
        before = len(self.nodes)          # the count, before the dict is rebuilt
        kept = [nd for nd in self.ordered() if nd.num != 0]
        if len(kept) == before:
            return 0
        renumber = {nd.num: i for i, nd in enumerate(kept, start=1)}
        self.nodes = {}
        for new_num, nd in enumerate(kept, start=1):
            nd.num = new_num
            for link in nd.links:                  # follow the renumbering
                link.to = renumber.get(link.to, 0)
            nd.links = [link for link in nd.links if link.to]
            self.nodes[new_num] = nd
        return before - len(kept)

    def random_init(self, seed: int = 0) -> None:
        from . import layout

        iv.set_dimensions(self.dimensions)
        rng = random.Random(seed)
        for nd in self.ordered():
            iv.random_vector(nd.pos, rng, iv.NORM)
        layout.frame(self)
