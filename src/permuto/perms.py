"""Faithful port of the Modula-2 module ``perms`` (perms.def / perms.mod).

``next_perm`` advances a sequence to the next permutation in dictionary
(lexicographic) order, in place, exactly like the original
``perms.NextPerm``.  It returns ``wrap`` = ``True`` when it rolls over from
the last permutation back to the first.
"""

from __future__ import annotations



def next_perm(s: List) -> bool:
    """Advance ``s`` to the next lexicographic permutation, in place.

    Returns ``True`` when wrapping from the last permutation to the first
    (mirrors the ``VAR wrap : BOOLEAN`` result of ``perms.NextPerm``).
    """
    n = len(s)
    if n == 0:
        return True
    i = n - 1
    while True:
        if i == 0:
            wrap = True
            break
        if s[i - 1] < s[i]:
            j = n - 1
            while s[j] <= s[i - 1]:
                j -= 1
            s[j], s[i - 1] = s[i - 1], s[j]
            wrap = False
            break
        i -= 1
    # s[i..n-1] are in reverse order; reversing yields the minimal suffix
    j = n - 1
    while i < j:
        s[i], s[j] = s[j], s[i]
        i += 1
        j -= 1
    return wrap
