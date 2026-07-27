# Polytop / Permutograph — Modula-2 (1990–95) → Python port

Christian Tismer's polytope / permutograph viewer. The original working copy
was deleted years ago; it survived only as `Poly.cry` — a ZIP encrypted with
the author's own 1987 `Crypt.pas` XOR tool — attached to a 1997 mail to a
colleague ("Vijay"). Recovered in 2026 from the Thunderbird archive and
decrypted (password `christian`). The XOR scheme and that password were never
meant as real security — it was more a light test of whether the recipient could
cope with decrypting it at all.

We are now **porting it to Python (PySide6)**, keeping the Modula-2 original
alongside for reference until the port is complete.

## Layout
- `src/permuto/` — the Python port, **feature-complete** (parity reached)
  - `perms.py`, `gen/` (genperm, operate, num2, pipeline), `formats/`
  - `core/` — NodeMgr, PM, PmProgs, IntVector, PCalc, Iri — UI-free
  - `session.py` — modes, menu state and main loop, also UI-free
  - `menus.py`, `scene.py`, `editor.py`, `loader.py` — which key does what,
    what is in the picture, the operator cursor, and what a name on the command
    line resolves to; all UI-free
  - `ui/` — PySide6: `permutograph_view`, `iridium_view`, `base_view`,
    `keys` (the only module that knows Qt key codes), `render` (five drawing
    loops over a `Scene`), `prompt`
  - `studies/` — standalone experiments: `kugel` (the 1991 colour study).
    Keep these free of viewer imports, in both directions.
- `tests/` — golden tests: regenerate `legacy/modula/nod/*` and compare
- `docs/ARCHITECTURE.md` — reverse-engineering notes, formats, the maths, the plan
- `legacy/` — the recovered Modula-2 original (delete when the port is done)
  - `modula/` — `*.mod`/`*.def`, `nod/`, `plots/`, `*.awk`, `permuto.bat`, DOS artifacts
  - `Poly_decrypted.zip` — pristine baseline; `Poly.cry`, `Crypt.pas` — provenance
  - `mail-fragments/` — the individually e-mailed SPA fragments (duplicates)

## Working notes
- **Start here:** `docs/HANDOVER.md` — current state and what's next.
  Phase 2 (parity with the original) is complete; phase 3, the pythonic
  refactor, is under way on the branch `phase3-refactor` — check it out before
  reading the code. `docs/PORT-GAPS.md` is no longer a work plan but the record
  of what the original did, and of where the port deliberately differs (§0).
- Read `docs/ARCHITECTURE.md` — it has the verified formats and the
  fixed-point rotation/projection/relaxation maths.
- Port style: the strict-1:1 rule has done its job and no longer binds — the
  golden tests against `nod/` and the 1995 `.ply` files are what keeps a
  refactor honest, so they must stay green. Coordinates stay `int` (the
  original is deliberately float-free; `studies/kugel` is the one exception,
  it was float in 1991 too). Keep `core/` UI-free (PySide6 now, a possible
  TypeScript/web viewer later, are just frontends).
- Python floor is **3.10** and the code says so: `match`/`case` where a value
  runs against named cases, and the current annotation spellings — `list[int]`,
  `dict[str, int]`, `X | None`, `Sequence` from `collections.abc`. Nothing
  imports from `typing` any more; don't reintroduce `List`/`Optional`.
- Origin is DOS / CP437; `legacy/**` is kept byte-exact via `.gitattributes`.
  Two consequences worth knowing before you lose an hour:
  - **Never search `legacy/` with plain `grep`.** In a UTF-8 locale macOS grep
    calls those files binary and then reports *no match*, silently, exit 1 —
    it looks exactly like "the word isn't there". Use `git grep`, `rg`, or
    `grep -a`. Reading them in Python needs `encoding="cp437"`.
  - For readable `git diff`/`git show` on them, set the textconv once per
    clone: `git config diff.cp437.textconv "iconv -f cp437 -t utf-8"`
    (`.gitattributes` already routes the sources to it; the stored bytes are
    untouched).
- Run `python -m pytest` to check the port against the originals.
- Tests exist so features don't break, so **test from the UI where possible**:
  drive the widget with real keystrokes (`viewer.run(..., _drive=...)`), grab
  the picture, assert what the user expects to see. Internals get a test only
  where the UI can't reach them. A test that only restates the construction
  code is chaff — delete it. The golden tests against `legacy/` stay untouched;
  they are what makes refactoring safe.
