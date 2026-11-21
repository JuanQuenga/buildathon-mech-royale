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
