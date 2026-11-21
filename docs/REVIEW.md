# Review: Mech Royale entry (for the human and the coordinator)

## Please submit
Newest first. Each tag passed the native gate on the MacBook (`NATIVE_ONLY=1 eval/check.sh <tag>`: unit tests,
recorded stream, slow-policy and crash tests, big and late stress streams, 0 missed replies). Run the Docker gate
before submitting.

| Tag | Commit | Single hypothesis it tests | Expected official |
| --- | --- | --- | --- |
| `good-6` | 5e2b91e | Everything on `main` since good-4 (hunter model, weapon-first, pickup-memory fix, 2-death FFA guess) **plus cube_greed** (grab kill-drop cubes before the next fight) beats good-4 in the real game | 4.7–5.0 |
| `good-5` | 37f5786 | good-4 with **good-3's brain.py** restored (nav/combat/main fixes kept). If it scores ≈ good-3 (4.88), the good-3→good-4 regression is in the brain changes (far/roof weapon trips, zone-field ETAs, inside-circle goal checks, early FFA guess) | 4.8 |

## Recommended final entry
`good-3` (f8db786), official **4.88**, until something beats it officially.

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
