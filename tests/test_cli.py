"""The command line, as `permuto ...` is actually typed.

Only what the argument parser itself decides is tested here -- what the
commands then produce is covered where it is made (the golden generation
tests, test_render, test_postscript, test_kugel, test_pms).
"""

import pytest

from permuto.__main__ import main  # noqa: E402


@pytest.fixture
def opened(monkeypatch):
    """Record what the viewer would have been opened with, without opening it."""
    pytest.importorskip("PySide6")
    from permuto.ui import viewer

    calls = []
    monkeypatch.setattr(viewer, "run",
                        lambda *a, **kw: calls.append(("run", a, kw)) or 0)
    monkeypatch.setattr(viewer, "run_iridium",
                        lambda *a, **kw: calls.append(("iridium", a, kw)) or 0)
    return calls


def test_show_tells_a_file_name_from_a_base_permutation(opened):
    """`show ikosa2 3` is a graph and a seed; `show 1234 12 + 23` is a base and
    its operators.  No argument parser can decide that -- it hangs on whether
    the first word resolves to a file -- so it stays hand-written and tested."""
    main(["show", "ikosa2", "3"])
    main(["show", "1234", "12", "+", "23", "+", "34"])
    main(["show", "ikosa2"])
    (_, a1, k1), (_, a2, k2), (_, a3, k3) = opened
    assert (a1[0], k1["seed"], k1["operators"]) == ("ikosa2", 3, None)
    assert (a2[0], k2["seed"]) == ("1234", 1)
    assert k2["operators"] == ["12", "+", "23", "+", "34"]
    assert (a3[0], k3["seed"], k3["operators"]) == ("ikosa2", 1, None)


@pytest.mark.parametrize("argv", [[], ["/PG"], ["/pg"], ["--pg"]])
def test_the_permutograph_mode_starts_from_every_spelling(opened, argv):
    """`polytop /PG`: base 1234 with 12/23/34, and no arguments means the
    same thing."""
    assert main(argv) == 0
    (_, args, kw), = opened
    assert args[0] == "1234"
    assert kw["operators"] == ["12", "+", "23", "+", "34"]


@pytest.mark.parametrize("word", ["iridium", "iri", "/i", "/I", "--iridium"])
def test_every_spelling_of_the_iridium_mode(opened, word):
    assert main([word]) == 0
    assert opened[0][0] == "iridium"


def test_a_misspelt_flag_is_refused_instead_of_ignored(tmp_path, capsys):
    """The old parser collected anything starting with `--` into a set and
    asked it for the flags it knew, so `--labls` drew a picture without labels
    and said nothing.  PORT-GAPS section 0: never swallow bad input."""
    out = tmp_path / "r.png"
    assert main(["render", "pgl4", str(out), "5", "--labls"]) != 0
    assert "labls" in capsys.readouterr().err
    assert not out.exists(), "nothing may be written for a command we refused"


def test_an_unknown_command_is_refused(capsys):
    assert main(["nonsense"]) != 0
    assert capsys.readouterr().err, "and says why"
