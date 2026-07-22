"""Graph generation: the original ``genperm | operate | num2`` pipeline."""

from .genperm import all_permutations
from .operate import apply_cycle, operate_line
from .number import number
from .pipeline import Permutograph, build

__all__ = [
    "all_permutations",
    "apply_cycle",
    "operate_line",
    "number",
    "Permutograph",
    "build",
]
