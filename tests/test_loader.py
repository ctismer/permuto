"""What a name on the command line resolves to.

`permuto show alle6` may mean a bundled sample, a file here, a build recipe or
a saved session, and each of those opens a different program: a `.pgd` rebuilds
the permutograph with a live operator table, a `.nod` restores the 1995
coordinates in polytop mode, a `.pms` resumes where someone left off.  These
are the rules that decide which -- decisions with reasons, so each reason gets
a test.
"""

import os
import shutil

import pytest

from permuto import loader
from permuto.core.graph import Graph
from permuto.formats import PlySession, write_pms
from permuto.loader import load_graph, make_session, resolve_file, write_session
from permuto.session import new_permutograph_session

SAMPLES = loader._nod_dir()


def _pair(directory, stem="alle6"):
    """Put a graph that has both a build recipe and its result into *directory*
    under *stem* -- alle6, the one bundled sample that has both."""
    for ext in (".nod", ".pgd"):
        shutil.copy(os.path.join(SAMPLES, "alle6" + ext), directory / (stem + ext))
    return directory / (stem + ".nod"), directory / (stem + ".pgd")


# -- which file a name means -------------------------------------------------

def test_a_typed_extension_is_honoured_wherever_the_file_lives(tmp_path):
    """Ask for a .nod and you get that .nod.  It used to depend on where the
    file was: by path the .pgd sibling displaced it, by name in the samples it
    did not -- the same typed extension, two different graphs and two different
    modes.  Only a bare name is ambiguous enough to need a preference."""
    nod, pgd = _pair(tmp_path)
    assert resolve_file(str(nod)) == str(nod)
    assert resolve_file(str(pgd)) == str(pgd)
    assert resolve_file("alle6.nod").endswith("alle6.nod")
    assert resolve_file("alle6.pgd").endswith("alle6.pgd")


def test_a_bare_name_prefers_the_recipe_over_its_own_result(tmp_path):
    """`show alle6` is ambiguous, and there the .pgd wins: it rebuilds the
    permutograph with the operator table, which the .nod has thrown away."""
    assert resolve_file("alle6").endswith("alle6.pgd")
    _pair(tmp_path)
    assert resolve_file(str(tmp_path / "alle6")).endswith("alle6.pgd")


def test_a_graph_just_built_is_found_by_its_bare_name(tmp_path, monkeypatch):
    """`permuto build knot ...` writes knot.pg/.nod/.pgd here, so `permuto show
    knot` has to look here.  It only ever looked in the samples directory, so
    the two commands did not compose."""
    monkeypatch.chdir(tmp_path)
    nod, pgd = _pair(tmp_path, "knot")
    assert resolve_file("knot") == pgd.name    # a name in, a name out
    pgd.unlink()
    assert resolve_file("knot") == nod.name


def test_a_name_that_is_nowhere_resolves_to_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert resolve_file("no-such-graph") is None
    assert resolve_file("no-such-graph.nod") is None


def test_the_samples_ship_with_the_package_and_legacy_is_the_fallback(monkeypatch):
    """Installed from a wheel there is no legacy/ -- the samples travel inside
    the package.  In a source checkout that has not built them, the recovered
    1995 originals stand in, so both see the same graphs."""
    assert SAMPLES.endswith(os.path.join("permuto", "data", "nod"))
    assert os.path.isfile(os.path.join(SAMPLES, "alle6.nod"))

    real_isdir = os.path.isdir
    monkeypatch.setattr(os.path, "isdir",
                        lambda p: False if p == SAMPLES else real_isdir(p))
    fallback = os.path.normpath(loader._nod_dir())
    assert fallback.endswith(os.path.join("legacy", "modula", "nod"))
    assert real_isdir(fallback), "the checkout still has the originals"


# -- what comes back ---------------------------------------------------------

def test_a_recipe_is_rebuilt_and_agrees_with_the_graph_it_recorded(tmp_path):
    """alle6.pgd says `1234 12 + 23 + 34 + 41 + 13 + 24`; rebuilding from it
    must give the graph alle6.nod recorded in 1995 -- same size, same degrees.
    (Node numbering is not comparable; the permutations decide it, not the file
    order.)"""
    built = load_graph("alle6")              # the recipe wins for a bare name
    stored = load_graph("alle6.nod")         # the typed extension gets the .nod
    assert built.nnodes == stored.nnodes == 24
    degrees = sorted(nd.nlink for nd in built.nodes.values())
    assert degrees == sorted(nd.nlink for nd in stored.nodes.values())
    assert degrees == [6] * 24


def test_operators_build_without_looking_at_the_disk(tmp_path, monkeypatch):
    """`show 1234 12 + 23 + 34` names no file at all -- the first word is a
    base permutation, and nothing is read."""
    monkeypatch.chdir(tmp_path)              # nothing here to find
    g = load_graph("1234", operators=["12", "+", "23", "+", "34"])
    assert g.nnodes == 24


def test_a_name_that_is_nothing_says_what_was_looked_for(tmp_path, monkeypatch):
    """The original halted; this one has to say which four things it tried."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError) as exc:
        load_graph("no-such-graph")
    msg = str(exc.value)
    assert "no-such-graph" in msg
    assert ".pgd" in msg and ".nod" in msg and ".pms" in msg


# -- sessions ----------------------------------------------------------------

def test_a_session_is_recognised_by_what_is_in_it_not_what_it_is_called(
        tmp_path, monkeypatch):
    """A session saved without an extension is still a session: the first
    fifteen bytes say so.  Without that, it would be read as a .nod and fail on
    the first line."""
    g = Graph.build("123", ["12", "+", "23"], seed=1)
    plain = tmp_path / "xanti"                       # no extension at all
    write_pms(plain, PlySession(graph=g, mode="permuto", base="123",
                                iteration=42))
    assert plain.read_bytes()[:15] == b"permuto session"

    monkeypatch.chdir(tmp_path)
    s = make_session("xanti")
    assert s.permuto and s.iteration == 42


def test_a_file_that_only_happens_to_have_the_name_is_not_a_session(
        tmp_path, monkeypatch):
    """Content, not name -- so a file of that name which is not one is not
    mistaken for one."""
    (tmp_path / "notes").write_text("just some notes about xanti\n")
    monkeypatch.chdir(tmp_path)
    assert loader._session_path("notes") is None


def test_a_saved_session_comes_back_under_the_bare_name_it_was_saved_as(
        tmp_path, monkeypatch):
    """Save appends .pms to a bare name, so opening has to try it -- otherwise
    the name you saved under is not a name you can reopen."""
    s = new_permutograph_session("1234", ["12", "+", "23", "+", "34"])
    s.iteration = 77
    written = write_session(s, tmp_path / "mine")
    assert written.name == "mine.pms"

    monkeypatch.chdir(tmp_path)
    back = make_session("mine")
    assert back.permuto and back.iteration == 77
    assert back.graph.nnodes == s.graph.nnodes


def test_a_session_beats_a_graph_of_the_same_name(tmp_path, monkeypatch):
    """Someone who saved `alle6.pms` next to `alle6.nod` wants their session,
    not the sample it started from."""
    g = Graph.build("123", ["12", "+", "23"], seed=1)
    write_pms(tmp_path / "alle6.pms", PlySession(graph=g, mode="permuto",
                                                 base="123", iteration=5))
    _pair(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert make_session("alle6").iteration == 5


def test_everything_that_can_be_opened_is_recognised_as_openable(
        tmp_path, monkeypatch):
    """The CLI has to tell `show <file> 3` (a seed) from `show <base> <ops>`
    (an operator list) before it opens anything, and it asks this.  A session
    file is openable, so a seed behind one must not turn into an operator."""
    g = Graph.build("123", ["12", "+", "23"], seed=1)
    write_pms(tmp_path / "mine.pms", PlySession(graph=g, mode="permuto",
                                                base="123"))
    _pair(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert loader.can_open("mine.pms")
    assert loader.can_open("mine")               # save appended the extension
    assert loader.can_open("alle6.nod")
    assert loader.can_open("alle6")
    assert loader.can_open("ikosa2")             # a bundled sample
    assert not loader.can_open("1234")           # a base permutation, not a file
