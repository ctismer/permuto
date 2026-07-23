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
from ..formats import read_nod


@dataclass
class NodeState:
    step: int = 0
    active: bool = False
    dead: bool = False
    sum: int = 0
    display: int = 0
    broken: Set[int] = field(default_factory=set)  # 1-based link indices


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
        base = read_nod(path)
        g = cls()
        g.nnodes = base.nnodes
        for num in sorted(base.links):
            nd = Node(num=num, links=list(base.links[num]))
            nd.nlink = len(nd.links)
            g.nodes[num] = nd
        g.set_dimensions(dimensions)
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

    def random_init(self, seed: int = 0) -> None:
        iv.set_dimensions(self.dimensions)
        rng = random.Random(seed)
        for nd in self.ordered():
            iv.random_vector(nd.pos, rng, iv.NORM)
