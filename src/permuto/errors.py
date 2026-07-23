"""Error types, shared by the domain core and the file formats.

The Modula-2 original had no error handling worth the name: `NodeMgr.LimitCheck`
closed the graphics mode and called ``HALT`` in the middle of a session,
`UserIO.ReadInt` clipped out-of-range values without a word, `ReadNodes` stopped
at the first unreadable byte, and `LoadPoly` validated nothing at all.  None of
that survives the port (see ``docs/PORT-GAPS.md`` §0).

The rule here: **the core raises and stays consistent, the UI catches and
reports.**  Nothing below the UI terminates the process, and no bad input is
silently bent into shape -- if a value cannot be used, saying so is part of the
job.

This module sits at package level rather than in ``core`` on purpose: it has no
imports of its own, so both ``permuto.core`` and ``permuto.formats`` can use it
without an import cycle.
"""

from __future__ import annotations


class PermutoError(Exception):
    """Base class for every error the core raises deliberately."""


class LimitExceeded(PermutoError):
    """A value left its permitted range.

    Replaces ``NodeMgr.LimitCheck``, which printed
    ``Error: <what> is not in the range <min> to <max>`` and then killed the
    program.  Same message, but the caller gets to decide what happens next.
    """

    def __init__(self, what: str, value: int, low: int, high: int) -> None:
        super().__init__(f"{what} is not in the range {low} to {high} (got {value})")
        self.what = what
        self.value = value
        self.low = low
        self.high = high


class InvalidBase(PermutoError):
    """The base permutation is not usable.

    Too long (> ``MAXDIMEN``), or it would generate more nodes than allowed.
    Note that repeated characters are *legal* -- ``pm5_221.mod`` deliberately
    uses ``11223``, "der kleine fürs Telefon".
    """


class InvalidCycle(PermutoError):
    """An operator cycle is not usable for the current base.

    Cycles address 1-based *positions*, so every character must lie in
    ``'1' .. '<len(base)>'``.  The empty cycle is valid and means "unused".
    """


class FileFormatError(PermutoError):
    """A file could not be read as the format it claims to be.

    Carries where the trouble is, because "cannot load" alone is useless when a
    1990s binary turns out to be half a file.
    """

    def __init__(self, path, detail: str, *, where: str | None = None) -> None:
        location = f" at {where}" if where else ""
        super().__init__(f"{path}: {detail}{location}")
        self.path = path
        self.detail = detail
        self.where = where


class NodeNotFound(PermutoError):
    """A node was addressed that does not exist.

    In the original this was a silent no-op: `Iri.SeekNode` returned 0 for an
    unknown label and the command simply did nothing, with no way to tell a
    typo from a refusal.
    """


class ProgramStateError(PermutoError):
    """A program was started from a state it cannot run in.

    The original's one instance of this: ParSum needs a finished SPA run
    ("Must run SPA before PARSUM").
    """


def limit_check(what: str, value: int, low: int, high: int) -> int:
    """Range check in place of ``NodeMgr.LimitCheck``; returns *value*.

    Raises :class:`LimitExceeded` instead of halting the program.
    """
    if not low <= value <= high:
        raise LimitExceeded(what, value, low, high)
    return value
