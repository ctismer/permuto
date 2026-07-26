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
  - `ui/` — PySide6 2D N-D-projection viewer, editor, /I mode, PNG renderer
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
  Phase 2 (parity with the original) is complete; next is the pythonic
  refactor. `docs/PORT-GAPS.md` is no longer a work plan but the record of
  what the original did.
- Read `docs/ARCHITECTURE.md` — it has the verified formats and the
  fixed-point rotation/projection/relaxation maths.
- Port style: the strict-1:1 rule has done its job and no longer binds — the
  golden tests against `nod/` and the 1995 `.ply` files are what keeps a
  refactor honest, so they must stay green. Coordinates stay `int` (the
  original is deliberately float-free; `studies/kugel` is the one exception,
  it was float in 1991 too). Keep `core/` UI-free (PySide6 now, a possible
  TypeScript/web viewer later, are just frontends).
- Origin is DOS / CP437; `legacy/**` is kept byte-exact via `.gitattributes`.
- Run `python -m pytest` to check the port against the originals.
- Tests exist so features don't break, so **test from the UI where possible**:
  drive the widget with real keystrokes (`viewer.run(..., _drive=...)`), grab
  the picture, assert what the user expects to see. Internals get a test only
  where the UI can't reach them. A test that only restates the construction
  code is chaff — delete it. The golden tests against `legacy/` stay untouched;
  they are what makes refactoring safe.
