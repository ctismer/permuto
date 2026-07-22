# Polytop / Permutograph — Modula-2 (1990–95) → Python port

Christian Tismer's polytope / permutograph viewer. The original working copy
was deleted years ago; it survived only as `Poly.cry` — a ZIP encrypted with
the author's own 1987 `Crypt.pas` XOR tool — attached to a 1997 mail to
Dr. T. Chellathurai ("Vijay"). Recovered in 2026 from the Thunderbird archive
and decrypted (password `christian`).

We are now **porting it to Python (PySide6)**, keeping the Modula-2 original
alongside for reference until the port is complete.

## Layout
- `src/permuto/` — the Python port
  - `perms.py`, `gen/` (genperm, operate, num2, pipeline), `formats/` — **done, verified**
  - `core/` — NodeMgr, PM, PmProgs, IntVector, PCalc (next)
  - `ui/` — PySide6 2D N-D-projection viewer (next)
- `tests/` — golden tests: regenerate `legacy/modula/nod/*` and compare
- `docs/ARCHITECTURE.md` — reverse-engineering notes, formats, the maths, the plan
- `legacy/` — the recovered Modula-2 original (delete when the port is done)
  - `modula/` — `*.mod`/`*.def`, `nod/`, `plots/`, `*.awk`, `permuto.bat`, DOS artifacts
  - `Poly_decrypted.zip` — pristine baseline; `Poly.cry`, `Crypt.pas` — provenance
  - `mail-fragments/` — the individually e-mailed SPA fragments (duplicates)

## Working notes
- Read `docs/ARCHITECTURE.md` first — it has the verified formats and the
  fixed-point rotation/projection/relaxation maths.
- Port style: **strict 1:1 first**, verified against the `nod/` golden files;
  keep coordinates `int` (the original is deliberately float-free). Refactor
  to idiomatic Python only in phase 2. Keep `core/` UI-free (PySide6 now, a
  possible TypeScript/web viewer later, are just frontends).
- Origin is DOS / CP437; `legacy/**` is kept byte-exact via `.gitattributes`.
- Run `python -m pytest` to check the port against the originals.
