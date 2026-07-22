"""Golden tests for the generation pipeline.

For every ``.pgd`` (the stored generating command) that also has the
matching ``.pg`` and ``.nod`` files, regenerate them with the Python port
and compare to the original 1990s output.  This locks the port to the
Modula-2/AWK behaviour (whitespace-normalised, line for line).
"""

from pathlib import Path

import pytest
from conftest import modula_dir

from permuto.formats import read_pgd
from permuto.gen import build


def _samples():
    nod = modula_dir() / "nod"
    out = []
    for pgd in sorted(nod.glob("*.pgd")):
        if pgd.with_suffix(".pg").exists() and pgd.with_suffix(".nod").exists():
            out.append(pgd)
    return out


def _norm(text: str):
    return [" ".join(line.split()) for line in text.splitlines() if line.strip()]


SAMPLES = _samples()


@pytest.mark.parametrize("pgd", SAMPLES, ids=[p.stem for p in SAMPLES])
def test_regenerate(pgd: Path):
    cmd = read_pgd(pgd)
    g = build(cmd.base, cmd.operators)
    assert _norm("\n".join(g.pg)) == _norm(pgd.with_suffix(".pg").read_text()), \
        f"{pgd.stem}: .pg mismatch"
    assert _norm("\n".join(g.nod)) == _norm(pgd.with_suffix(".nod").read_text()), \
        f"{pgd.stem}: .nod mismatch"


def test_have_samples():
    assert SAMPLES, "no .pgd/.pg/.nod sample triples found"
