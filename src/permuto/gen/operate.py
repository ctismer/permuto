"""Faithful port of ``operate.awk`` (kr0te, 10.10.91).

An *operator* is a sequence of cycles (digit strings) applied to the
POSITIONS of a permutation string; ``+`` separates several operators.
For one input permutation, :func:`operate_line` returns the original
followed by, for each operator, the pair ``(original, transformed)`` --
i.e. the edge list for that node, one neighbour per operator.

Example (base ``123``, operators ``12 + 23``)::

    operate_line("123", ["12", "+", "23"]) == "123 213 123 132"
"""

from __future__ import annotations



def apply_cycle(res: str, cycle: str) -> str:
    """Apply one cyclic place-swap to ``res``.

    Positions are 1-based; source characters are read from the state at the
    start of the cycle (``wrk``), exactly like the AWK inner loop.
    """
    wrk = res
    z = cycle
    for _ in range(len(cycle)):
        frm = z[0]
        z = z[1:] + frm  # rotate the cycle string left
        to = z[0]
        ch = wrk[int(frm) - 1]
        res = res[: int(to) - 1] + ch + res[int(to):]
    return res


def operate_line(arg: str, operators: list[str]) -> str:
    res = arg
    parts: list[str] = []
    for z in operators:
        if z == "+":  # end of one operator: emit (arg, res), restart from arg
            parts.append(arg)
            parts.append(res)
            res = arg
        else:  # apply all cycles of the current operator in sequence
            res = apply_cycle(res, z)
    parts.append(arg)
    parts.append(res)
    return " ".join(parts)
