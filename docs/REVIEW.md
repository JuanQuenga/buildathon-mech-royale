# Review: Mech Royale entry (for the human and the coordinator)

## Please submit
Newest first. Each tag passed the native gate on the MacBook (`NATIVE_ONLY=1 eval/check.sh <tag>`: unit tests,
recorded stream, slow-policy and crash tests, big and late stress streams, 0 missed replies). Run the Docker gate
before submitting.

| Prio | Tag | Commit | Single hypothesis it tests (compare with good-27 = rage, 5.25) | Expected official |
| --- | --- | --- | --- | --- |
| 1 | `good-31` | 1f7fa6fa | (queued already) steady strafe on good-22 | 5.2 |
| 2 | `good-32` | 0947af6 | **Range**: holding a laser, fight mechs from 170 m (normal: 28 m with lightning, 90 m with gun+laser). Tests whether the house tiers' aim falls off with range while our hitscan laser does not (sim +0.19, noise) | 5.35 |
| 3 | `good-33` | 18ce57f | **First weapon**: explore for a laser until 120 s while armed without one, never take a mortar (sim: gun+laser ≈6 points vs gun+lightning ≈4.5, gun+mortar ≈2.8) | 5.3 |
| 4 | `good-34` | 709fd65 | **Duel discipline**: break contact whenever a second hunter is in sight (unless the target is below 30 % HP). This check now overrides rage's never-retreat. Contrasts "one hunter at a time" with rage | 5.25 |

Dropped as superseded by rage (which includes aggro, berserk and seek-by-sound): good-18, good-19, good-20, good-21, good-23 and good-24.
The hybrids good-28/29 were skipped (hide 5.04). Base for new tags: good-27's profile `laser+nav3x+fixx+ragex`.

Official so far: good-27 5.25, good-22 5.21, good-30 5.19, good-26 5.04, good-25 4.96, good-15 5.19, good-17 5.06, good-16 4.88, good-14 5.17, good-10 5.10, good-7 5.00, good-11 5.00, good-6 4.96, good-3 4.88/4.85, good-8 4.79, good-9 (chaos control) 4.79, good-4 4.58, good-5 4.46.

## Recommended final entry
`good-27` (6720a56, rage: laser first + good-3 nav + hop fix + aggressive hunting), official **5.25**, until something beats it officially.

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
