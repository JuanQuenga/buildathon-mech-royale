# Review: Mech Royale entry (for the human and the coordinator)

## Please submit
Newest first. Each tag passed the native gate on the MacBook (`NATIVE_ONLY=1 eval/check.sh <tag>`: unit tests,
recorded stream, slow-policy and crash tests, big and late stress streams, 0 missed replies). Run the Docker gate
before submitting.

| Prio | Tag | Commit | Single hypothesis it tests | Expected official |
| --- | --- | --- | --- | --- |
| 1 | `good-35` | 370d88e | **Stack**: good-31 (steady strafe, 5.56) + rage. Profile `laser+nav3x+fixx+ragex+steadyx` | 5.6 |
| 2 | `good-36` | 1ca1a5a | good-31 with even slower strafe reversals (every 6–10 s) | 5.6 |
| 3 | `good-37` | 0ebc659 | good-31 with no sideways movement while engaging (hold range only; projectile dodge kept) | 5.5 |
| 4 | `good-38` | a9a0bd3 | good-31 with no reversals at all (orbit one way) | 5.55 |
| 5 | `good-32` | 0947af6 | (rage base, no steady strafe) laser standoff 170 m; rebase onto the new best if worth testing | — |
| 6 | `good-33` | 18ce57f | (rage base) explore for a laser until 120 s, never take a mortar | — |
| 7 | `good-34` | 709fd65 | (rage base) break contact at the 2nd hunter | — |

Official so far: **good-31 5.56**, good-27 5.25, good-22 5.21, good-30 5.19, good-26 5.04, good-25 4.96, good-15 5.19, good-17 5.06, good-16 4.88, good-14 5.17, good-10 5.10, good-7 5.00, good-11 5.00, good-6 4.96, good-3 4.88/4.85, good-8 4.79, good-9 (chaos control) 4.79, good-4 4.58, good-5 4.46.

## Recommended final entry
**`good-31` (1f7fa6f, profile `laser+nav3x+fixx+steadyx`: laser first + good-3 nav + stale-hop fix + steady strafe), official 5.56.**

## What the bot does
Python bot (`bot/`): a forked policy process with a hard 26 ms reply guard. Per observation: threat assessment →
brain intent (zone rotation, fight/retreat, heal cycle, loot, supply drop, seek, hold) → navigation (path planner,
jet hops) → combat (led gun, laser state machine, lightning) → inventory (weapon take/swap, upgrades). Details in
`docs/HANDOFF.md`, `docs/combat.md`, `docs/nav.md`.

**Variants are profiles.** `bot/brain.py: DEFAULT_PROFILE` selects one (the submitted image has no env). Profiles
compose with `+` (e.g. `laser+nav3x`), and `MECH_PROFILE=...` overrides locally. Each tag is a one-line commit on
a `var/*` branch that flips `DEFAULT_PROFILE`, so `main` keeps `base`. `nav3x` swaps in `bot/navigate3.py`, a frozen
copy of good-3's navigation.

## Evidence so far
- **Official runs are the instrument.** An identical resubmission moves the score ±0.03. A behaviour-neutral
  perturbation (good-9) moved it −0.08. So tag-to-tag noise is about ±0.1.
- **The sim cannot rank variants.** Paired noise is ±0.4 at 96 seeds, and the same profile on the same seeds scored
  5.38 and 5.09 on two runs. The sim also rated good-4 ≥ good-3, which reality reversed. Use it for crashes, FFA
  sanity and large effects only.
- **Navigation is a real-game lever.** good-4's jet-hop energy rules cost score: good-5 (good-4 + good-3 brain)
  scored 4.46 vs good-3's 4.88, and reverting navigate.py gave +0.17 on seek (good-14) and +0.09 on laser (good-15).
- **Post-good-4 brain work helped:** hunter model, weapon-first, pickup-memory fix, 2-death FFA guess and
  cube_greed together scored 4.96 (good-6) vs 4.58 (good-4).
- **Laser first** gave +0.14 on greed (good-10) and 0 on seek (good-11).
- **Seek** gave +0.04 (good-7). **Fresh** (heal after kill, new fights at 85 % HP) gave −0.17 (good-8).
- Sim calibration: escalation speed is the lever (`--squad join_per_loss=0.6` puts good-4 near its official
  level). The sim's FFA scores for the nav3 profiles are not worse than the old nav.
