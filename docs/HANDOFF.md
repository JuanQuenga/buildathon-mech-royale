# Handoff (Linux agent), 11-21 ~10:20 ET

Read `docs/REVIEW.md` first: it holds the submit queue (the coordinator syncs to it at :07/:27/:47), the official
results, family means, the FFA analysis and the final-entry recommendation. This file is the working state.

## Where things stand
- **Practice board:** our best draw is good-31 = 5.56 (rank ~21 of 250; the cut (32nd) is ~5.27 and rising; leader
  kyoto-max 6.31). The base policy (`laser+nav3x+fixx+steadyx`) has a true mean of **5.34** (9 official draws,
  SD 0.13). No single-knob variant has beaten it beyond noise.
- **Official noise:** behaviour-neutral re-rolls of one policy: SD ≈ 0.13 per 48-match run (the sim overstates it at
  0.27). One run resolves effects ≳ 0.3; identical builds repeat to ±0.03.
- **Practice scoring:** 16 − place only. House bots never fight each other, so points = our kills before we die
  (sim: 98 % of points). We die at ~100–110 s after ~5 kills. The lever is damage taken / survival time.
- **Structural branch:** good-54 = base + `peekx` (fight from cover with the laser) is at the top of the queue.
  If it beats the base mean by ≳ 0.25, re-roll it once (`eval/make_rerolls.sh "laser+nav3x+fixx+steadyx+peekx" 17 32`
  makes gated re-roll tags) and make it the new base; consider extending peek to gun duels.
- **FFA final candidate:** good-53 = base + `openholdx` (never start a fight while unarmed in the first 45 s unless
  the round is known squad) + `ffahidex` (FFA-only survival-first while > 5 alive). Evidence: real showdowns (our
  three opening deaths were fights we started unarmed; FFA placement follows damage taken, not dealt), FFA self-play
  ffahide +0.26 ± 0.48 (200 matches), openhold sim-neutral, openhold practice 5.35 (no cost).

## Running / queued background jobs (all detached; check `ps -eo args | grep run_matches`)
- FFA self-play chain on cores 0–2 (`taskset`), 25-seed chunks into `mech-royale/work/sim/sp_<v>_<seed>.jsonl`,
  `.done` marker when finished: v6 (ffahide 5 vs 3 alive) → v7 (good-53 combo vs base, 200 matches) → v8 (peek vs base).
  Summarise with `python3 eval/selfplay.py <files>`; per-match paired differences are the honest CI (seats in one
  match are not independent).
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
