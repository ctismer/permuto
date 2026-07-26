"""Turning a name on the command line into something to look at.

``permuto show pgl4`` may mean a bundled sample graph, a file in the current
directory, a saved session, or a base plus operators to build from -- the
original had one rule per file type and a fixed directory; this is that rule
set, kept UI-free so the CLI and the headless renderer do not have to import a
widget to resolve a filename.
"""

from __future__ import annotations

import os
import pathlib

from .core import intvector as iv
from .core.graph import Graph
from .formats import load_session, read_pgd, save_session
from .formats.plyfile import PlySession
from .session import Mode, Session, new_permutograph_session


def _nod_dir():
    """Where the named sample graphs live.

    Prefer the copy bundled with the package (so ``pip install`` + ``permuto
    show pgl4`` just works), and fall back to the recovered originals under
    ``legacy/`` when running from a source checkout.
    """
    here = os.path.dirname(__file__)
    bundled = os.path.join(here, "data", "nod")
    if os.path.isdir(bundled):
        return bundled
    return os.path.join(here, "..", "..", "legacy", "modula", "nod")


def resolve_file(p: str):
    """Return the .pgd/.nod path for a name or file, or None if none exists."""
    candidates = []
    if os.path.exists(p):
        candidates.append(p)
        if p.endswith(".nod") and os.path.exists(p[:-4] + ".pgd"):
            candidates.insert(0, p[:-4] + ".pgd")
    else:
        base = os.path.join(_nod_dir(), p)
        for ext in (".pgd", ".nod"):
            if os.path.exists(base + ext):
                candidates.append(base + ext)
        if p.endswith((".pgd", ".nod")) and os.path.exists(os.path.join(_nod_dir(), p)):
            candidates.insert(0, os.path.join(_nod_dir(), p))
    return candidates[0] if candidates else None


def load_graph(name_or_path, *, dimensions: int = iv.MAXDIMEN,
               seed: int = 0, operators=None) -> Graph:
    """Resolve a spec to a Graph (file, or base + operators to build)."""
    if operators is not None:
        return Graph.build(str(name_or_path), list(operators),
                           dimensions=dimensions, seed=seed)
    chosen = resolve_file(str(name_or_path))
    if chosen is None:
        raise FileNotFoundError(
            f"nothing found for {name_or_path!r}: no session (.pms/.ply), "
            f"no graph (.pgd/.nod), and no operators to build one")
    if chosen.endswith(".pgd"):
        return Graph.from_pgd(chosen, dimensions=dimensions, seed=seed)
    return Graph.load_nod(chosen, dimensions=dimensions, seed=seed)


def _session_path(p: str):
    """Return the session file for *p*, trying ``.pms``/``.ply`` too, or None.

    So ``show xanti`` finds ``xanti.pms`` -- symmetric with save, which appends
    ``.pms`` to a bare name.
    """
    for cand in (p, p + ".pms", p + ".ply"):
        if not os.path.isfile(cand):
            continue
        if cand.endswith((".pms", ".ply")):
            return cand
        with open(cand, "rb") as f:
            if f.read(15) == b"permuto session":
                return cand
    return None


def make_session(name_or_path, *, seed: int = 1, operators=None) -> Session:
    """Build the initial :class:`~permuto.session.Session` for the viewer.

    A base + operators (or a ``.pgd``) yields permutograph mode, with a live
    ``PM``; a plain ``.nod`` yields polytop mode; a saved session file
    (``.pms`` / ``.ply``) is loaded and resumed where it left off.
    """
    if operators is not None:
        return new_permutograph_session(str(name_or_path), list(operators))
    p = str(name_or_path)
    session_file = _session_path(p)
    if session_file is not None:
        return session_from_file(session_file)
    chosen = resolve_file(p)
    if chosen and chosen.endswith(".pgd"):
        cmd = read_pgd(chosen)
        return new_permutograph_session(cmd.base, cmd.operators)
    g = load_graph(name_or_path, seed=seed)
    return Session(graph=g, mode=Mode.POLYTOP)


def session_from_file(path) -> Session:
    """Resume a saved session -- ``.pms`` or ``.ply``, told apart by content.

    Anything salvaged from a truncated file is left in ``load_warnings`` for
    the frontend to show; no rescaling happens here, because ``Session`` frames
    whatever coordinates it is given.
    """
    loaded = load_session(path)
    mode = Mode.PERMUTO if loaded.pm is not None else Mode.POLYTOP
    session = Session(graph=loaded.graph, mode=mode, pm=loaded.pm)
    session.iteration = loaded.iteration          # restore where it left off
    session.load_warnings = list(loaded.warnings)
    return session


def write_session(session: Session, path) -> pathlib.Path:
    """Save *session*, and return the file actually written.

    Binary ``.ply`` is read-only legacy here, so whatever extension was typed,
    what gets written is a text ``.pms``.
    """
    pm = session.pm
    sess = PlySession(
        graph=session.graph, permuto=session.permuto,
        mode="permuto" if session.permuto else "polytop",
        base=pm.base if pm else "",
        optable=[list(r) for r in pm.optable] if pm else [],
        last_edit_line=pm.last_edit_line if pm else 0,
        iteration=session.iteration)
    return save_session(pathlib.Path(path).with_suffix(".pms"), sess,
                        binary=False)
