# Review: Mech Royale entry (for the human and the coordinator)

## Please submit
Newest first. Each tag passed the native gate on the MacBook (`NATIVE_ONLY=1 eval/check.sh <tag>`: unit tests,
recorded stream, slow-policy and crash tests, big and late stress streams, 0 missed replies). Run the Docker gate
before submitting.

| Prio | Tag | Commit | Single hypothesis it tests (compare with good-14 = seek + good-3 nav, 5.17, unless noted) | Expected official |
| --- | --- | --- | --- | --- |
| 1 | `good-16` | f8decf1 | **Ground-only routes**: no planned jet hops, no roof weapons. Navigation is a proven real-game lever: removing good-4's hop-energy rules was worth +0.17/+0.4. Do hops help at all? (sim: 2 zone deaths in 16 matches, a risk) | 5.2 |
| 2 | `good-17` | 195a423 | **Scaling**: supply drops (3 cubes + full HP) ahead of healing in cover and opportunistic fights, up to 70 s away; crate 18→32, drone 45→60 | 5.2 |
| 3 | `good-18` | ec61cd7 | **Break contact when a second hunter is in sight** (unless the target is below 30 % HP): the sim's deaths are 2–7 hunters converging | 5.2 |
| 4 | `good-19` | 692371d | **Explore for a laser** until 120 s while armed without one, never take a mortar (sim: gun+lightning ≈4.5 vs gun+laser ≈6) | 5.25 |
| 5 | `good-20` | 375d715 | **More aggression** on good-15 (laser + good-3 nav, 5.19): engage ratio 1.1→1.6, start fights from 40 % HP (was 60 %), heal below 40 % (was 55 %). The heal-more variant (good-8) lost 0.17 | 5.3 |
| 6 | `good-21` | 2f800aa | **Seek by memory and by sound** on good-15: walk to remembered house bots, or toward gunfire heard in the last 6 s (110 m along the bearing) | 5.3 |
| 7 | `good-12` | 025bc42 | (old nav) seek + scale, compare with good-7. Superseded by good-17 | — |
| 8 | `good-13` | a57b78e | (old nav) seek + picky, compare with good-7 | — |

Official so far: good-15 5.19, good-14 5.17, good-10 5.10, good-7 5.00, good-11 5.00, good-6 4.96, good-3 4.88/4.85, good-8 4.79, good-9 (chaos control) 4.79, good-4 4.58, good-5 4.46.

## Recommended final entry
`good-15` (7cce2c2, laser first + good-3 navigation), official **5.19**, until something beats it officially.

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
