"""The port's error handling -- the one place it deliberately beats the
original, which halted, clipped or ignored bad input (docs/PORT-GAPS.md §0)."""

import pytest

from permuto import FileFormatError, LimitExceeded
from permuto.core import limit_check
from permuto.formats import read_nod, read_pgd
from permuto.formats.nodfile import read_int_pairs


def test_limit_check_passes_through_and_reports_like_the_original():
    assert limit_check("node number", 5, 1, 10) == 5
    with pytest.raises(LimitExceeded) as exc:
        limit_check("node number", 11, 1, 10)
    # same wording as NodeMgr.LimitCheck, which used to HALT here
    assert "node number is not in the range 1 to 10" in str(exc.value)
    assert (exc.value.value, exc.value.low, exc.value.high) == (11, 1, 10)


def test_truncated_nod_is_rejected_instead_of_silently_shrinking(tmp_path):
    p = tmp_path / "half.nod"
    p.write_text("1 2 2 3 3\n")  # dangling 3: an edge lost its partner
    with pytest.raises(FileFormatError) as exc:
        read_int_pairs(p)
    assert "truncated" in str(exc.value)
    assert exc.value.where == "line 1"


def test_empty_nod_is_rejected(tmp_path):
    p = tmp_path / "prose.nod"
    p.write_text("Dies ist gar kein Graph\n")
    with pytest.raises(FileFormatError):
        read_int_pairs(p)


def test_trailing_german_comment_is_still_accepted(tmp_path):
    # ~a third of the legacy .nod files end in CP437 prose; that must keep working
    p = tmp_path / "commented.nod"
    p.write_bytes("1 2 2 3\nDies ist ein Ikosaeder der Frequenz 3\n".encode("cp437"))
    assert read_int_pairs(p) == [(1, 2), (2, 3)]
    assert read_nod(p).nnodes == 3


def test_short_pgd_names_the_problem(tmp_path):
    p = tmp_path / "stub.pgd"
    p.write_text("permuto pgl3\n")
    with pytest.raises(FileFormatError) as exc:
        read_pgd(p)
    assert "got 2 token(s)" in str(exc.value)


def test_legacy_nod_files_all_load(nod_dir):
    # the real corpus must stay readable -- 95 files, prose comments and all
    files = sorted(nod_dir.glob("*.nod"))
    assert len(files) > 50
    for f in files:
        assert read_nod(f).nnodes > 0
