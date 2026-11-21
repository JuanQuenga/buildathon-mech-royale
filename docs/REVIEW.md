# Review: Mech Royale entry (for the human and the coordinator)

## Please submit
Newest first. Each tag passed the native gate on the MacBook (`NATIVE_ONLY=1 eval/check.sh <tag>`: unit tests,
recorded stream, slow-policy and crash tests, big and late stress streams, 0 missed replies). Run the Docker gate
before submitting.

| Prio | Tag | Commit | Single hypothesis it tests | Expected official |
| --- | --- | --- | --- | --- |
| 1 | `good-10` | 1cd7676 | **Laser first** (compare with good-6 = greed, 4.96): when choosing the first secondary, value a laser above lightning. Sim: +0.55 over greed (gun+laser ≈6.0 points vs gun+lightning ≈4.5, gun+mortar ≈2.8) | 5.2 |
| 2 | `good-11` | ddbc83a | **Laser first + never take a mortar, on top of seek** (compare with good-7 = seek, 5.00) | 5.2 |
| 3 | `good-14` | 2db6e00 | **good-3's navigation on top of seek** (compare with good-7, 5.00). good-5 (good-4 + good-3's brain) scored 4.46 vs good-3's 4.88, 4× the noise, so good-4's non-brain changes look costly. Main suspect: jet hops now wait standing still (move 0,0) for the full energy, with no urgency discount. All tags since good-4 carry this navigate.py | 5.3 |
| 4 | `good-12` | 025bc42 | **Scaling on top of seek** (compare with good-7): consider supply drops (3 cubes + full HP) ahead of hiding to heal and ahead of opportunistic fights, travel up to 70 s to them, and raise crate (18→32) and drone (45→60) values | 5.1 |
| 5 | `good-13` | a57b78e | **Picky fights on top of seek** (compare with good-7): in squad rounds, use the stricter unknown/FFA opportunity rule (engage ratio 0.6, no other mech within 150 m unless the target is busy). good-3 (4.88) spent most rounds in "unknown" mode with these rules, while good-4 (4.58) switched to squad rules | 5.0 |

The plan is to hill-climb on official runs. Tag-to-tag noise is about ±0.1 (chaos control), and my sim's paired noise is ±0.4 at 96 seeds. Every variant is one profile (`DEFAULT_PROFILE` in `bot/brain.py`), and profiles compose (`seek+scale`).

Official so far: good-7 5.00, good-6 4.96, good-3 4.88/4.85, good-8 (fresh) 4.79, good-9 (chaos control) 4.79, good-4 4.58, good-5 4.46.

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
