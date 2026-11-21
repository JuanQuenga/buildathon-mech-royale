# Review: Mech Royale entry (for the human and the coordinator)

## Please submit
Newest first. Each tag passed the native gate on the MacBook (`NATIVE_ONLY=1 eval/check.sh <tag>`: unit tests,
recorded stream, slow-policy and crash tests, big and late stress streams, 0 missed replies). Run the Docker gate
before submitting.

| Tag | Commit | Single hypothesis it tests (vs good-6 = main + cube_greed, official 4.96) | Expected official |
| --- | --- | --- | --- |
| `good-7` | 3dd9bcd | **seek**: when healthy (≥80 % HP) with a secondary weapon and nothing else to do, walk to the nearest remembered house bot instead of holding, so kills come one at a time before the squad escalates (sim +0.22 vs greed, 96 seeds) | 5.1 |
| `good-8` | 696e4ec | **fresh**: after each kill heal out of sight, and start new fights only at ≥85 % HP (sim +0.20 vs greed) | 5.1 |

Submitted already: good-5 (37f5786, good-4 + good-3 brain, scoring), good-6 (5e2b91e) = 4.96.

## Recommended final entry
`good-6` (5e2b91e), official **4.96**, until something beats it officially.

## What the bot does
Python bot (`bot/`): a forked policy process with a hard 26 ms reply guard. Per observation: threat assessment →
brain intent (zone rotation, fight/retreat, heal cycle, loot, supply drop, hold) → navigation (path planner, jet hops)
→ combat (led gun, laser state machine, lightning) → inventory (weapon take/swap, upgrades). Details in
`docs/HANDOFF.md`, `docs/combat.md`, `docs/nav.md`.

## Evidence so far
- Official: good-4 4.58, good-3 4.88 (same 48 fixed seeds). The sim rated them equal (squad 3.66 vs 3.59), so small
  sim differences do not predict official ones; only official runs decide.
- Sim calibration (MacBook, good-4, 48 seeds): default squad 3.69; gun cadence 5 ticks 3.29; all-engage at 360 s
  3.38; **one extra attacker per two losses (join_per_loss=0.5) 4.88**. Escalation speed is the lever that moves the
  sim toward the official level; the official 4.58 sits between the default and 0.5.
