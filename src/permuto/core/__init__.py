"""Domain core (UI-free): fixed-point vectors, graph model, layout, SPA.

Ports of IntVector, NodeMgr, PCalc and PmProgs.  Kept free of any UI
dependency so PySide6 (now) and a later TypeScript/web viewer are just
frontends.
"""

from . import intvector, layout, spa
from .graph import Graph, Node, NodeState

__all__ = ["intvector", "layout", "spa", "Graph", "Node", "NodeState"]
