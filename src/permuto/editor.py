"""The operator editor -- which cell of the table is being typed into, and the
rules for leaving it.  UI-free, like :mod:`permuto.session`.

``polytop.mod`` edited the table in place with ``UserIO.InputStr``: the cursor
sat in one cell, digits went straight into it, and a bad cycle simply would not
let you move on.  The port keeps those rules but puts them in an object, so a
frontend only has to map its keys onto :meth:`OperatorEditor.move` and paint
what :meth:`OperatorEditor.fields` describes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .errors import PermutoError


@dataclass(frozen=True)
class OpField:
    """Which cell of the operator table a cursor is in.

    ``op`` is ``None`` for the base line; otherwise ``op`` and ``cyc`` are
    1-based, the way the original numbered them (``Op 1`` and its three
    cycles).
    """

    op: Optional[int] = None
    cyc: Optional[int] = None

    @property
    def is_base(self) -> bool:
        return self.op is None


BASE_FIELD = OpField()

#: what :meth:`OperatorEditor.move` accepts
MOVES = ("up", "down", "first", "last")


def fields_of(pm) -> List[OpField]:
    """Every editable cell of *pm*, in cursor order: the base, then the
    operators row by row."""
    out = [BASE_FIELD]
    for i in range(len(pm.optable)):
        for j in range(len(pm.optable[i])):
            out.append(OpField(i + 1, j + 1))
    return out


def value_of(pm, fld: OpField) -> str:
    """What *fld* currently holds in *pm*."""
    if fld.is_base:
        return pm.base
    return pm.optable[fld.op - 1][fld.cyc - 1]


class OperatorEditor:
    """A cursor over ``pm``'s table plus the digits typed into the current cell.

    The buffer is only written back by :meth:`commit`, and a cell that will not
    validate keeps the cursor: that is the original's blocking validation, and
    it is why every move goes through ``commit`` first.
    """

    def __init__(self, pm):
        self.pm = pm
        self.field = BASE_FIELD
        self.buffer = pm.base
        self.base_before = pm.base

    @property
    def base_changed(self) -> bool:
        """Whether the base was edited -- a rebuild has to start from scratch."""
        return self.pm.base != self.base_before

    def fields(self) -> List[OpField]:
        return fields_of(self.pm)

    def value(self, fld: OpField) -> str:
        return value_of(self.pm, fld)

    # -- typing ----------------------------------------------------
    def type_digit(self, ch: str) -> None:
        self.buffer += ch

    def backspace(self) -> None:
        self.buffer = self.buffer[:-1]

    # -- the cursor ------------------------------------------------
    def commit(self) -> Optional[str]:
        """Write the buffer back; return an error message, or None if it took."""
        try:
            if self.field.is_base:
                self.pm.set_base(self.buffer)
            else:
                self.pm.set_cycle(self.field.op, self.field.cyc, self.buffer)
            return None
        except PermutoError as exc:
            return str(exc)

    def move(self, where: str) -> None:
        """Move the cursor: ``up``/``down`` by one, ``first``/``last`` to the
        ends -- ``last`` being the last cell anyone has filled in, not the last
        cell there is."""
        flds = self.fields()
        idx = flds.index(self.field)
        if where == "up":
            idx = max(0, idx - 1)
        elif where == "down":
            idx = min(len(flds) - 1, idx + 1)
        elif where == "first":
            idx = 0
        elif where == "last":
            idx = max((n for n, f in enumerate(flds)
                       if f.is_base or self.value(f)), default=0)
        else:
            raise ValueError(f"unknown move {where!r}, expected one of {MOVES}")
        self.field = flds[idx]
        self.buffer = self.value(self.field)
