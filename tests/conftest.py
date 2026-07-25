import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture(scope="session", autouse=True)
def _qapplication():
    """Create one real QApplication for the whole session, before any Qt use.

    Without this, whichever Qt test runs first decides the application type: the
    headless renderer makes a QGuiApplication, and then the widget tests abort
    ("Cannot create a QWidget without QApplication").  Creating a QApplication
    up front lets both reuse it (QApplication is a QGuiApplication).
    """
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        yield None
        return
    app = QApplication.instance() or QApplication([])
    yield app


def modula_dir() -> Path:
    """Locate the recovered Modula-2 sources, before or after the restructure."""
    for cand in (ROOT / "legacy" / "modula", ROOT / "PolyProject"):
        if (cand / "nod").is_dir():
            return cand
    raise RuntimeError("Modula sources (nod/) not found")


@pytest.fixture(scope="session")
def nod_dir() -> Path:
    return modula_dir() / "nod"


def ply_files():
    """The surviving binary session files, saved by the original in 1995."""
    return sorted(modula_dir().rglob("*.ply"))
