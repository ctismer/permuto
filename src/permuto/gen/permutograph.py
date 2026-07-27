"""Build the permutograph structure with operator identity preserved.

Unlike a loaded ``.nod`` (pure topology), this keeps, for every node, the
permutation string and, per edge, which *operator* produced it — needed for
node labels and operator-coloured edges.
"""

from __future__ import annotations


from .operate import apply_cycle


def operator_groups(operators: list[str]) -> list[list[str]]:
    """Split the operator tokens into groups on ``+``; each group is one
    operator (a sequence of position cycles)."""
    groups: list[list[str]] = []
    cur: list[str] = []
    for tok in operators:
        if tok == "+":
            groups.append(cur)
            cur = []
        else:
            cur.append(tok)
    groups.append(cur)
    return groups


def neighbors(perm: str, operators: list[str]) -> list[tuple[int, str]]:
    """Return ``(operator_index, neighbour_permutation)`` for each operator."""
    out: list[tuple[int, str]] = []
    for k, group in enumerate(operator_groups(operators), start=1):
        p = perm
        for cycle in group:
            p = apply_cycle(p, cycle)
        out.append((k, p))
    return out
