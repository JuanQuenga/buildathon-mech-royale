# Review: Mech Royale entry (for the human and the coordinator)

## Please submit
Newest first. Each tag passed the native gate on the MacBook (`NATIVE_ONLY=1 eval/check.sh <tag>`: unit tests,
recorded stream, slow-policy and crash tests, big and late stress streams, 0 missed replies). Run the Docker gate
before submitting.

| Prio | Tag | Commit | Single hypothesis it tests | Expected official |
| --- | --- | --- | --- | --- |
| 1 | `good-9` | e6718e7 | **Chaos control**: good-3 with only the idle torso-scan phase shifted (behaviour-neutral). Its distance from good-3 (4.88/4.85) is the tag-to-tag noise: any behaviour change re-rolls all 48 trajectories | 4.6–5.1 |

More tags (scaling, stacked seek+fresh, picky, laser) follow after the sim screens finish (~2:10 AM).

Submitted: good-5 4.46, good-6 4.96, good-7 (seek) 5.00, good-8 (fresh) scoring.

## Recommended final entry
`good-7` (3dd9bcd, seek), official **5.00**, until something beats it officially.

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
