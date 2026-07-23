# Handover — permuto (Modula-2 → Python port)

Read this first, then `docs/ARCHITECTURE.md` and `git log --oneline`.

> **Scope correction (2026-07-24).** An earlier version of this file claimed
> phase 1 was "complete" and filed the interactive layer, the operator editor
> and `Iri` as "intentionally not ported". That was this project's own wrong
> judgement, not a decision — all three are required. **The port is not
> feature-complete.** See `docs/PORT-GAPS.md` for the verified gap list, which
> is the current work plan. Refactoring is deferred until parity is reached.

## Where we are
- The permutograph **viewer core** works end to end (generate → relax →
  project → draw), plus the SPA/ParSum program mode.
- Branch `port/python-scaffold`, HEAD `449fd31` — **not pushed**; `main` is the
  pristine recovery import.
- Working tree clean. ~33 tests: `python -m pytest`.

## Done (ported + tested, strict 1:1)
- **gen/** `genperm` / `operate` / `num2` — regenerates 11 original graphs
  byte-for-byte (golden tests).
- **core/** `intvector` (fixed point, `Norm=4096`, `Scale` trunc-to-zero),
  `graph` (NodeMgr model + `.nod` loader + permutograph `build`/`from_pgd`
  keeping permutation labels & operator numbers), `layout` (PCalc: contract ×5,
  squeeze, punish, normalize, spin, canshrink + main-loop cadence),
  `spa` (full PmProgs: SPA + ParSum + per-edge line states).
- **ui/** PySide6 viewer (`show`): relax+spin, node labels, operator-coloured
  edges, algorithm switch, program mode (SPA/ParSum, click = start node);
  offscreen PNG renderer (`render`); PostScript export (`export` = SavePicture).
- **docs/** ARCHITECTURE.md (formats, fixed-point maths, layout heuristic,
  scope). Demo renders in `docs/demo/`.

## Not ported — REQUIRED, this is the work list
The interactive layer (menu, keys, single-step, file + program submenus), the
**operator editor** and the rest of `PM`'s runtime editing (Connect/Disconnect/
Collapse/Uncollapse), the `.ply` binary format, the missing drawing details,
the `makeikos` geodesic generator, and **Iridium** (`Iri` / `P_SPTA`).
Full detail and byte-level formats: `docs/PORT-GAPS.md`.

Genuinely out of scope (verified standalone experiments): `kugel`, `ham1`,
`h`, `pmtest`, `pm5`.

## Run
```bash
pip install -e .                 # or prefix commands with PYTHONPATH=src
python -m pytest                 # ~33 green
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
