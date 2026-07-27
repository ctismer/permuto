"""Faithful port of ``num2.awk`` (kr0te, 28.11.91).

Replace permutation strings by 1-based node numbers, assigned in order of
first appearance of each line's FIRST field (which is ``genperm``'s output
order).  Every field that names a known node is replaced by its number.
"""

from __future__ import annotations



def number(pg_lines: list[str]) -> list[str]:
    nodes: dict[str, int] = {}
    for line in pg_lines:
        fields = line.split()
        if not fields:
            continue
        key = fields[0]
        if key not in nodes:
            nodes[key] = len(nodes) + 1
    out: list[str] = []
    for line in pg_lines:
        fields = line.split()
        out.append(" ".join(str(nodes[w]) if w in nodes else w for w in fields))
    return out
