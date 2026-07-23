# Handover — permuto (Modula-2 → Python port)

Read this first, then `docs/ARCHITECTURE.md` and `git log --oneline`.

## Where we are
- **Phase 1 is complete**: the faithful permutograph viewer works end to end
  (generate → relax → project → draw), plus the SPA/ParSum program mode.
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

## Not ported (intentional — say the word to add)
Auxiliary standalone programs: `Iri` (Iridium / `P_SPTA`), `kugel`, `ham1`,
`h`, `pmtest`, `pm5`; and PM's interactive editing + the DOS menu (a UI concern).

## Run
```bash
pip install -e .                 # or prefix commands with PYTHONPATH=src
python -m pytest                 # ~33 green
python -m permuto show pgl4      # keys: s c a l o p · click = start · r q
python -m permuto render pgl5 out.png 700
python -m permuto export pgl4 out.ps 600
```

## Next — phase 2
Refactor to idiomatic Python **once behaviour is locked**, keeping the golden
tests green (coordinates are `int` on purpose in phase 1). Keep `core/` UI-free.
Then optional **phase 3** = TypeScript/browser on that clean core. Smaller
possible items: node/operator legend in the viewer, ParSum display polish, or
porting `Iri`.

## Gotchas
- `/rewind` restores files but does **not** touch git. If disk and HEAD
  disagree, trust the disk and re-commit (that is how HEAD `449fd31` came to be).
- `Lib.RANDOM` is source-less → absolute node positions are not
  bit-reproducible; the *algorithm* is faithful and the emergent shape matches.
