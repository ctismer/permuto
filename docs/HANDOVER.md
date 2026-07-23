# Handover — permuto (Modula-2 → Python port)

Read this first, then `docs/ARCHITECTURE.md` and `git log --oneline`.

> **Scope correction (2026-07-24).** An earlier version of this file claimed
> phase 1 was "complete" and filed the interactive layer, the operator editor
> and `Iri` as "intentionally not ported". That was this project's own wrong
> judgement, not a decision — all three are required. **The port is not
> feature-complete.** See `docs/PORT-GAPS.md` for the verified gap list, which
> is the current work plan. Refactoring is deferred until parity is reached.

## Where we are
- Branch `port/python-scaffold`; `main` is the pristine recovery import.
  Working tree clean, 156 tests: `python -m pytest`.
- **Local only — there is no remote.** The repository exists on one disk, and
  so does the only known copy of the recovered 1990s original.
- The **domain core is complete**; what remains is essentially all UI.

## Done (ported + tested)
- **gen/** `genperm` / `operate` / `num2` — regenerates 11 original graphs
  byte-for-byte; `geodesic` (makeikos), `factorize` (trunc), `vierdrei`.
- **core/** `intvector` (fixed point, `Norm=4096`, 32-bit — see its header),
  `graph` (NodeMgr model, `.nod` loader, permutograph build, `pack_nodes`),
  `layout` (PCalc), `spa` (PmProgs: SPA + ParSum + line states),
  `pm` (base + operator table, naming, build, runtime editing),
  `iri` (the Iridium/SIMONE simulation).
- **formats/** `.pg`/`.nod`/`.pgd` readers, `.ply` binary sessions, PostScript.
- **errors** — a real error hierarchy where the original halted or kept quiet.
- **ui/** PySide6 viewer (`show`), PNG renderer (`render`), PostScript export.

### Verified against the original data, not just invariants
- `PM` reproduces permutations, edges **and** operator numbers of all eight
  1995 `.ply` files; `.ply` round-trips byte-identically apart from
  uninitialised padding in `pg24.ply`.
- The geodesic generator is isomorphic to all twelve `ikosa1..12.nod`.
- `vierdrei` and the factorisation match their `.nod` edge sets exactly.

## What remains — mostly UI
The interactive shell (modes `/PG` and `/I`, menu, keys, **single-step**,
status lines, the `UserIO` input primitives), the **operator editor**, the file
and program submenus, the missing drawing details with EGA sizes scaled, and
the Iridium `/I` mode on top of the finished simulation. Plus two open
questions: a text session format instead of the binary `.ply` for saving, and
shipping the PostScript preamble.
Full detail and byte-level formats: `docs/PORT-GAPS.md`.

Genuinely out of scope (verified standalone experiments): `kugel`, `ham1`,
`h`, `pmtest`, `pm5`.

## Run
```bash
pip install -e .                 # or prefix commands with PYTHONPATH=src
python -m pytest                 # 156 green
python -m permuto show pgl4      # keys: s c a l o p · click = start · r q
python -m permuto render pgl5 out.png 700
python -m permuto export pgl4 out.ps 600
```

## Next — phase 2 = completeness (NOT refactoring)
Work through `docs/PORT-GAPS.md` until the port does everything the original
did. Two standing rules:
* **Parity first.** The original is the floor, not the target; improvements
  come after parity, so don't redesign on the way.
* **Real error handling** is the one deliberate deviation: the original
  HALTed, silently clipped, or ignored bad input (see PORT-GAPS §0). The port
  raises a `PermutoError` from the UI-free core and reports it in the UI.

Only afterwards: **phase 3** = pythonic refactor, then optionally
TypeScript/browser on the cleaned core.

## Gotchas
- `/rewind` restores files but does **not** touch git. If disk and HEAD
  disagree, trust the disk and re-commit (that is how HEAD `449fd31` came to be).
- `Lib.RANDOM` is source-less → absolute node positions are not
  bit-reproducible; the *algorithm* is faithful and the emergent shape matches.
  Note this applies to the `.nod` path only: in permutograph mode the start
  layout comes from the link numbers, so those rebuilds *are* reproducible.
- The AWK generators' node numbering is likewise not reproducible (Thompson
  AWK hash order), so those are checked by isomorphism — see PORT-GAPS §8.
- Integer width is **32 bit** throughout; do not reintroduce TopSpeed's 16-bit
  wraparound. `core/intvector` explains why and offers `int32()` for the few
  places where the original's overflow is observable.
- `legacy/modula/s.exe` is PolyTop **V1.3** "now under the name SimOne", an
  older build than `polytop.exe` (V1.4) — not a source of extra features. Its
  copyright line names the second author, Gerhard G. Thomas.
