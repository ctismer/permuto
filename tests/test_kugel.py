"""The 1991 colour study: palette, both dither passes, and the seam trick.

No Qt here -- the study produces palette indices and is testable on its own,
which is the point of keeping it out of ``ui``.
"""

from permuto.studies.kugel import MAX_COLOR, MIN_COLOR, PALETTE, render_sphere


def test_palette_is_a_warm_ramp_that_never_goes_grey():
    """Red leads the whole way and blue climbs fastest from nothing: deep red
    to warm pink-white.  A grey ramp would have made this a dithering demo
    instead of a colour study.  Entries 0 and 15 stay black and white --
    "schwarz und weiß bleiben" -- so the background is a true black."""
    assert (PALETTE[0], PALETTE[15]) == ((0, 0, 0), (255, 255, 255))
    ramp = PALETTE[MIN_COLOR:MAX_COLOR + 1]
    brightness = [sum(c) for c in ramp]
    assert brightness == sorted(brightness), "the ramp must get lighter"
    assert all(r >= b >= g for r, g, b in ramp), "red leads, green trails"
    assert ramp[0][1] == 0 and ramp[-1][1] > 150, "green spans nothing to plenty"


def _rendered(**kw):
    return render_sphere(60, 200, 200, **kw)


def test_only_palette_colours_are_used():
    for mode in (False, True):
        used = {c for row in _rendered(floyd=mode) for c in row}
        assert used <= {0} | set(range(MIN_COLOR, MAX_COLOR + 1))
        assert len(used) > 8, "a sphere in three colours would miss the point"


def test_the_octant_is_mirrored_eight_ways_without_a_seam():
    """One octant is computed and mirrored; the loops start two pixels early so
    the error buffer is already charged where the visible part begins.  If that
    failed, the octant boundaries would show as a jump along the diagonal."""
    for mode in (False, True):
        img = _rendered(floyd=mode)
        cx = cy = 100
        for dy in range(-59, 60):
            for dx in range(-59, 60):
                assert img[cy + dy][cx + dx] == img[cy + dx][cx + dy]
        # no seam: neighbours never jump more than one colour band, on the
        # diagonal as anywhere else
        for y in range(1, 199):
            for x in range(1, 199):
                c = img[y][x]
                if not c:
                    continue
                for nx, ny in ((x + 1, y), (x, y + 1)):
                    n = img[ny][nx]
                    if n:
                        assert abs(c - n) <= 2, f"seam at {x},{y}"


def test_the_two_passes_disagree_and_floyd_is_reproducible():
    ordered = _rendered(floyd=False)
    floyd = _rendered(floyd=True, seed=7)
    assert ordered != floyd, "the two dither passes must not coincide"
    assert floyd == _rendered(floyd=True, seed=7), "same seed, same picture"
    assert floyd != _rendered(floyd=True, seed=8), "the shake must be noise"


def test_brightest_at_the_centre_and_dark_at_the_rim():
    img = _rendered()
    assert img[100][100] == MAX_COLOR
    assert img[100][100 - 59] < img[100][100 - 30] < img[100][100]
