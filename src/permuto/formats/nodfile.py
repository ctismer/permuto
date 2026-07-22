"""Readers for the on-disk formats.

``.pgd``  one line: ``<prog> <name> <base> <op tokens...>`` (generating command)
``.pg``   permutation edge list: per source, ``src nbr src nbr ...`` (strings)
``.nod``  same as ``.pg`` with permutation strings replaced by node numbers.
          When *loaded* (see ``NodeMgr.ReadNodes``) it is simply a flat,
          whitespace-separated stream of integers read in ``(from, to)`` pairs
          = undirected edges.  Operator identity is NOT preserved in ``.nod``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class PgdCommand:
    prog: str
    name: str
    base: str
    operators: List[str]


def read_pgd(path) -> PgdCommand:
    tokens = Path(path).read_text().split()
    return PgdCommand(
        prog=tokens[0], name=tokens[1], base=tokens[2], operators=tokens[3:]
    )


def read_int_pairs(path) -> List[Tuple[int, int]]:
    # Mirror NodeMgr.ReadNodes / FIO.RdCard: read leading cardinal pairs and
    # stop at the first non-numeric token (some hand-made .nod files carry a
    # trailing German comment, in CP437 -> decode as latin-1, never utf-8).
    text = Path(path).read_bytes().decode("latin-1")
    nums: List[int] = []
    for tok in text.split():
        try:
            nums.append(int(tok))
        except ValueError:
            break
    return list(zip(nums[0::2], nums[1::2]))


@dataclass
class Graph:
    """Undirected graph as built by ``NodeMgr.ReadNodes`` (deduped, sorted)."""

    nnodes: int = 0
    links: Dict[int, List[int]] = field(default_factory=dict)


def read_nod(path) -> Graph:
    g = Graph()
    for frm, to in read_int_pairs(path):
        if frm == to:
            continue
        for a, b in ((frm, to), (to, frm)):
            lst = g.links.setdefault(a, [])
            if b not in lst:
                lst.append(b)
    for a in g.links:
        g.links[a].sort()
    g.nnodes = len(g.links)
    return g
