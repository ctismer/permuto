import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def modula_dir() -> Path:
    """Locate the recovered Modula-2 sources, before or after the restructure."""
    for cand in (ROOT / "legacy" / "modula", ROOT / "PolyProject"):
        if (cand / "nod").is_dir():
            return cand
    raise RuntimeError("Modula sources (nod/) not found")


@pytest.fixture(scope="session")
def nod_dir() -> Path:
    return modula_dir() / "nod"
