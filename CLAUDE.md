# Polytop / Permutograph (Modula-2, 1990–1995)

Christian Tismer's polytope / permutograph project. The original working copy was
deleted years ago; the only surviving copy was `Poly.cry` — a ZIP encrypted with the
author's own 1987 `Crypt.pas` XOR tool — attached to a 1997 mail to Dr. T. Chellathurai
("Vijay"). Recovered in 2026 from the Thunderbird archive and decrypted (password
`christian`, a Turbo-Pascal password-seeded XOR stream cipher).

## Layout
- `PolyProject/` — the decrypted project, extracted verbatim from `Poly_decrypted.zip`
  - `*.mod` / `*.def` — Modula-2 sources; main program is `polytop.mod`
  - `*.obj`, `*.map`, `*.pr`, `polytop.exe`, `ham1.exe`, `kugel.exe` — DOS build artifacts (disposable)
  - `nod/` — polytope / permutograph data files (dodecahedron, icosahedron, …)
  - `plots/` — PostScript / plot output (`*.ps`, `*.ply`)
  - `rna/` — AWK / RNA experiments
- `Poly_decrypted.zip` — the decrypted ZIP, untouched "ground truth" baseline
- `Poly.cry`, `Crypt.pas` — the encrypted attachment and the original cipher (provenance)
- `pmprogs.def`/`pmprogs.mod`, `nodemgr.def`, `utilitie.def` (repo root) — SPA fragments
  pulled from a separate 1997 mail; duplicates of files already inside `PolyProject/`.

## Notes for cleanup
- Origin is DOS / CP437: filenames and umlauts may need normalization (e.g. `dreif<cp437>nf.nod`).
- Modula-2 dialect is Turbo/TopSpeed style (`FROM x IMPORT y`, `(* *)` comments).
- Keep `Poly_decrypted.zip` as the pristine baseline; do cleanup work on `PolyProject/`.
- Likely modern build target: GNU Modula-2 (`gm2`).
