"""Faithful port of ``GenPerm.mod``: all permutations of a string.

Mirrors ``REPEAT print; NextPerm UNTIL PermStr = OrigStr``: emit the base
permutation first, then step lexicographically (cyclically) until we return
to it.  For a base that is already sorted ascending this yields the full
lexicographic sequence; for any other base it starts there and wraps.
"""

from __future__ import annotations


from ..perms import next_perm


def all_permutations(base: str) -> list[str]:
    s = list(base)
    orig = list(base)
    out: list[str] = []
    while True:
        out.append("".join(s))
        next_perm(s)
        if s == orig:
            break
    return out
