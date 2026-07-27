"""Every annotation has to name something that exists.

`from __future__ import annotations` means an annotation is never evaluated at
run time -- it is a string until somebody asks.  Nobody asks, so a name that
does not exist sits there silently: `perms.next_perm` was declared `s: List`
after the typing sweep removed the import, and neither the tests nor the
program ever noticed (`0c91793`..`696b592`).

This asks.  It is the cheapest possible type check and needs no tooling; mypy
does far more, but only where mypy is installed and run.
"""

import importlib
import inspect
import pkgutil
import typing

import pytest

import permuto


def _modules():
    """Every module of the package, importable ones only.

    `permuto.ui` and `permuto.studies` need PySide6; skip them where it is
    missing rather than reporting an import error as a bad annotation.
    """
    for info in pkgutil.walk_packages(permuto.__path__, prefix="permuto."):
        try:
            yield importlib.import_module(info.name)
        except ImportError:                       # pragma: no cover - optional Qt
            continue


ALL = sorted(_modules(), key=lambda m: m.__name__)
IDS = [m.__name__ for m in ALL]


@pytest.mark.parametrize("module", ALL, ids=IDS)
def test_every_annotation_in_the_module_resolves(module):
    """Functions, classes and their methods -- everything a reader would trust."""
    bad = []
    for name, obj in vars(module).items():
        if getattr(obj, "__module__", None) != module.__name__:
            continue                              # imported from elsewhere
        targets = [obj] if inspect.isfunction(obj) else []
        if inspect.isclass(obj):
            targets = [obj] + [v for v in vars(obj).values()
                               if inspect.isfunction(v)]
        for target in targets:
            try:
                typing.get_type_hints(target)
            except Exception as exc:              # NameError, mostly
                bad.append(f"{name}.{getattr(target, '__name__', '')}: {exc}")
    assert not bad, "annotations naming something undefined:\n  " + "\n  ".join(bad)
