"""permuto - a modern (PySide6) reincarnation of the 1990-95 Modula-2
Polytop/Permutograph viewer.

A faithful, verifiable port: the generation pipeline (``genperm`` ->
``operate`` -> ``num2``) is reproduced exactly and checked against the original
``.pg``/``.nod`` files as golden tests.  See ``docs/ARCHITECTURE.md`` for the
maths and formats, and ``docs/PORT-GAPS.md`` for what the port still owes the
original -- feature parity comes before any cleanup.
"""

from .errors import (
    FileFormatError,
    InvalidBase,
    InvalidCycle,
    LimitExceeded,
    NodeNotFound,
    PermutoError,
    ProgramStateError,
)

__version__ = "0.0.1"

__all__ = [
    "PermutoError", "LimitExceeded", "InvalidBase", "InvalidCycle",
    "FileFormatError", "NodeNotFound", "ProgramStateError",
]
