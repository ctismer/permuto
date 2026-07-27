"""The ``permuto`` pipeline: base permutation + operators -> .pg / .nod.

Equivalent to ``permuto.bat``::

    genperm <base> | awk -f operate.awk <ops> > <name>.pg
    awk -f num2.awk < <name>.pg              > <name>.nod
    echo permuto <name> <base> <ops>         > <name>.pgd
"""

from __future__ import annotations

from dataclasses import dataclass

from .genperm import all_permutations
from .number import number
from .operate import operate_line


@dataclass
class Permutograph:
    base: str
    operators: list[str]
    perms: list[str]  # genperm output, in order
    pg: list[str]     # edge list with permutation strings
    nod: list[str]    # same, with node numbers


def build(base: str, operators: list[str]) -> Permutograph:
    perms = all_permutations(base)
    pg = [operate_line(p, operators) for p in perms]
    nod = number(pg)
    return Permutograph(
        base=base, operators=list(operators), perms=perms, pg=pg, nod=nod
    )
