"""Graph generation: the original ``genperm | operate | num2`` pipeline."""

from .genperm import all_permutations
from .operate import apply_cycle, operate_line
from .number import number
from .permutograph import neighbors, operator_groups
from .pipeline import Permutograph, build

__all__ = [
    "all_permutations",
    "apply_cycle",
    "operate_line",
    "number",
    "neighbors",
    "operator_groups",
    "Permutograph",
    "build",
]
