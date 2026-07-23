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

from ..errors import FileFormatError


@dataclass
class PgdCommand:
    prog: str
    name: str
    base: str
    operators: List[str]


def read_pgd(path) -> PgdCommand:
    """Read the one-line generating command ``<prog> <name> <base> <ops...>``.

    The original never read these back -- ``permuto.bat`` only wrote them, as a
    record of how a graph had been made ("Durch umkopieren in eine Batch-Datei
    laesst sich der Aufruf wiederholen").  So there is no original behaviour to
    be faithful to here, and a short line must not turn into an IndexError.
    """
    tokens = Path(path).read_bytes().decode("latin-1").split()
    if len(tokens) < 3:
        raise FileFormatError(
            path,
            f"expected at least '<prog> <name> <base>', got {len(tokens)} token(s)",
        )
    return PgdCommand(
        prog=tokens[0], name=tokens[1], base=tokens[2], operators=tokens[3:]
    )


def read_int_pairs(path) -> List[Tuple[int, int]]:
    """Read the leading ``(from, to)`` node-number pairs of a ``.nod`` file.

    Mirrors ``NodeMgr.ReadNodes`` / ``FIO.RdCard``: numbers are read until the
    first non-numeric token, which is then ignored along with the rest.  That
    is deliberate, not sloppiness -- about a third of the hand-made ``.nod``
    files end in a German prose comment ("Dies ist ein Ikosaeder der Frequenz
    3"), written in CP437, hence the latin-1 decode.  Checked across all 95
    legacy files: nothing but prose ever follows, so no edge is lost this way.

    Unlike the original we do complain when the numbers themselves are wrong:
    an odd count means a dangling node number, i.e. a truncated file, which
    ``ReadNodes`` would have accepted as a slightly smaller graph.
    """
    text = Path(path).read_bytes().decode("latin-1")
    nums: List[int] = []
    lineno = 0
    for lineno, line in enumerate(text.splitlines(), start=1):
        stop = False
        for tok in line.split():
            try:
                nums.append(int(tok))
            except ValueError:
                stop = True
                break
        if stop:
            break
    if not nums:
        raise FileFormatError(path, "no node numbers found")
    if len(nums) % 2:
        raise FileFormatError(
            path,
            f"odd number of node numbers ({len(nums)}) -- edges come in "
            f"(from, to) pairs, so the file looks truncated",
            where=f"line {lineno}",
        )
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
