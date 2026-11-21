# Review: Mech Royale entry (for the human and the coordinator)

## Please submit
Newest first. Each tag passed the native gate on the MacBook (`NATIVE_ONLY=1 eval/check.sh <tag>`: unit tests,
recorded stream, slow-policy and crash tests, big and late stress streams, 0 missed replies). Run the Docker gate
before submitting.

| Prio | Tag | Commit | Single hypothesis it tests | Expected official |
| --- | --- | --- | --- | --- |
| 1 | `good-15` | 7cce2c2 | **good-10 (laser first on greed, 5.10) + good-3 navigation** (the nav revert gave +0.17 on seek: good-14 5.17 vs good-7 5.00). Profile `laser+nav3x` | 5.25 |
| 2 | `good-12` | 025bc42 | seek + scale (supply drops first, crate/drone values up), compare with good-7 (it carries good-4's navigation) | 5.05 |
| 3 | `good-13` | a57b78e | seek + picky fight rules, compare with good-7 | 5.0 |

good-9 (chaos control) 4.79, good-4 4.58, good-5 4.46.

## Recommended final entry
`good-10` (1cd7676, laser first), official **5.10**, until something beats it officially.

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
