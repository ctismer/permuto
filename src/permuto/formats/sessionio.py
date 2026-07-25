"""Load and save a session, picking the format.

``.pms`` (text) is the format we write now; ``.ply`` (binary) stays readable so
the eight 1995 files -- and any others still around -- keep working.  Loading
dispatches on what the file actually is, not just its name, so a mislabelled
file still loads.
"""

from __future__ import annotations

from pathlib import Path

from .plyfile import PlySession, read_ply, write_ply
from .pmsfile import MAGIC, read_pms, write_pms


def load_session(path) -> PlySession:
    """Read a session from ``.pms`` or ``.ply``, detecting which it is."""
    p = Path(path)
    head = p.read_bytes()[:len(MAGIC)]
    if head == MAGIC.encode("ascii"):
        return read_pms(p)
    return read_ply(p)


def save_session(path, session: PlySession, *, binary=None) -> None:
    """Write a session.  Text ``.pms`` by default; a ``.ply`` name (or
    ``binary=True``) writes the legacy binary format instead."""
    if binary is None:
        binary = str(path).lower().endswith(".ply")
    if binary:
        write_ply(path, session)
    else:
        write_pms(path, session)


def convert_ply_to_pms(ply_path, pms_path) -> None:
    """Migrate an old binary session to the text format."""
    write_pms(pms_path, read_ply(ply_path))
