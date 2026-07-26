"""Node / graph model — the port of ``NodeMgr`` data structures + ``ReadNodes``.

A permutograph is loaded from a ``.nod`` file into 1-based numbered nodes with
undirected, deduped, sorted adjacency (see ``formats.read_nod``).  Positions
are N-dimensional integer vectors; they start random and are relaxed by the
layout engine (``core.layout``).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Set

from . import intvector as iv

# NOTE: ``formats`` is imported inside load_nod, not here: formats/plyfile.py
# needs Graph and Node, so a module-level import would close a cycle.


# LineStatus (NodeMgr): edge state used by the PmProgs programs / display
L_FREE, L_INPUT, L_OUTPUT, L_LOCKED = 0, 1, 2, 3


@dataclass
class NodeState:
    step: int = 0
    active: bool = False
    dead: bool = False
    sum: int = 0
    display: int = 0
    broken: Set[int] = field(default_factory=set)  # 1-based link indices
    lines: List[int] = field(default_factory=list)  # LineStatus per link


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
    pos: List[int] = field(default_factory=iv.new_vector)
    old: List[int] = field(default_factory=iv.new_vector)
    color: int = 7
    nlink: int = 0
    links: List[int] = field(default_factory=list)  # 1-based neighbour numbers
    opno: List[int] = field(default_factory=list)
    perm: str = ""
    state: NodeState = field(default_factory=NodeState)
    iri: IriState = field(default_factory=IriState)


class Graph:
    def __init__(self) -> None:
        self.nodes: Dict[int, Node] = {}
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
    def build(cls, base: str, operators: List[str], *,
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
            seen: Dict[int, int] = {}
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

    def ordered(self) -> List[Node]:
        return [self.nodes[i] for i in sorted(self.nodes)]

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
