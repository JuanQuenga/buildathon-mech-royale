# Handoff (Linux agent), 11-21 ~14:55 ET

Read `docs/REVIEW.md` first: status, official results, family means, the FFA analysis and the final-entry
recommendation. The submit queue itself is `coord/queue/mech.txt`. This file is the working state.

## Where things stand (14:55 ET)
- **Practice board:** best draw good-31 = 5.56, rank ~37; the cut (32nd) is 5.65 and rising. Base policy
  (`laser+nav3x+fixx+steadyx`) true mean 5.34 (SD 0.13 per draw). Best-supported variant: isolate (`+isolatex`),
  5.48 / 5.44 = 5.46. The queue (`coord/queue/mech.txt`, submitted automatically by the coordinator's runner) holds
  isolate re-rolls good-ri41…ri62: draws that can beat the cut.
- **Official findings today** (see REVIEW "Movement while fighting" and the results table): lateral movement while
  fighting the squad is worth ~1 point (standing 4.19, 6 m/s 4.77, base 5.34), more lateral is not better (widex
  5.23); breaking contact is bad (4.73); every other knob or structural idea landed within noise of 5.34.
- **The sim does not rank variants** (arm-first: sim +0.22 ± 0.12 over 300 paired seeds, official 5.23). Use it for
  crashes, regressions and mechanism diagnosis (traced runs with `MECH_DEBUG=1`), not for selection.
- **Scoring:** 16 − place only; the final zone (radius 0 by ~6:55) ends every match; survivors at 8:00 are ranked
  by HP. In the sim pure evasion survives to ~300 s and dies when the whole squad engages, never reaching the
  ~380 s window where house bots start dying to the zone, so practice points = our kills before death.
- **FFA final candidate:** good-55 = base + `openholdx` + `ffahide3x` (see REVIEW "Recommended final entry").

## How to submit and read scores
- Rewrite `coord/queue/mech.txt` (one pushed, gated tag per line, in priority order). Write a one-line prediction
  in `eval/RESULTS.md` before queueing. `coord/wait_result.sh mech <tag> 600` blocks until it scores;
  `coord/results/mech.latest.md` has the last 25 scores and the live board.

## Running / queued background jobs (all detached; check `ps -eo args | grep run_matches`)
- Nothing long-running except the isolate re-roll factory (`eval/make_rerolls.sh ... 47 62 good-ri`, log in
  `mech-royale/work/rerolls_iso2.log`). All self-play (v1–v8) and the 300-seed paired runs are finished; results are
  in REVIEW. Summarise self-play with `python3 eval/selfplay.py <files>` (per-match paired differences are the honest
  CI).
- Cast recorder (`eval/diag/cast/cap.mjs`) writes `mech-royale/work/cast/live3.jsonl` / `state3.jsonl` until ~13:00.
  We are not in the Top-16 Showdown lineup while ranked below 16th.

## Tools added today
- `eval/make_rerolls.sh <policy> <first> <last>`: gated re-roll tags `good-r<n>` (scan-phase deltas `r<n>x`).
- `sim/run_matches.py --ffa "var:<profile>*n,..."`: tracked self-play of our own variants; `eval/selfplay.py` table.
- `eval/diag/cast/*.py`: real showdown analysis (ffa, tl timeline, opening, rear, range, profile, move, lead).
- Bot stats now carry `mode_first`, `mode_flips` (round detector timing) and `peek_stat`.
- Switches added (all default off; profile deltas in `bot/brain.py: PROFILES`): `airx`, `sboostx`, `sboost50x`,
  `widex`, `discx`, `ffax`, `ffastandx`, `lookx`, `ffahidex`, `ffahide3x`, `openholdx`, `strictffax`, `peekx`,
  `chaos*x`, `r1x..r64x`.

## Gotchas
- Never `pkill -f` a pattern that appears in your own command line (it kills your shell, exit 144): kill by PID.
- Sim batches read `bot/` from their checkout: run long batches from a frozen worktree (`git worktree add --detach`).
- Gate (`eval/check.sh`) under heavy load can flake `native_slow` by one late reply; do not pin it with `taskset`
  onto cores that a sim batch saturates. Combat unit tests pin fire-suppressing switches off (`tests/combat/helpers.py`).
- Machine budget: ≤ 3 CPU-bound processes, temp files under `mech-royale/work/` (TMPDIR), not /tmp.
