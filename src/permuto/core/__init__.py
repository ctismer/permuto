"""Domain core (UI-free): fixed-point vectors, graph model, layout, SPA.

Ports of IntVector, NodeMgr, PCalc and PmProgs.  Kept free of any UI
dependency so PySide6 (now) and a later TypeScript/web viewer are just
frontends.
"""

from . import intvector, layout, spa
from .graph import Graph, Node, NodeState

# Re-exported for convenience; they live at package level (permuto.errors) so
# that formats/ can raise them too without an import cycle.
from ..errors import (
    FileFormatError,
    InvalidBase,
    InvalidCycle,
    LimitExceeded,
    NodeNotFound,
    PermutoError,
    ProgramStateError,
    limit_check,
)

__all__ = [
    "intvector", "layout", "spa",
    "Graph", "Node", "NodeState",
    "PermutoError", "LimitExceeded", "InvalidBase", "InvalidCycle",
    "FileFormatError", "NodeNotFound", "ProgramStateError", "limit_check",
]
