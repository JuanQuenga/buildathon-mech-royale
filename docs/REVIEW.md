# Review: Mech Royale entry (for the human and the coordinator)

## Please submit
Newest first. Each tag passed the native gate on the MacBook (`NATIVE_ONLY=1 eval/check.sh <tag>`: unit tests,
recorded stream, slow-policy and crash tests, big and late stress streams, 0 missed replies). Run the Docker gate
before submitting.

| Prio | Tag | Commit | Single hypothesis it tests | Expected official |
| --- | --- | --- | --- | --- |
| 1 | `good-22` | ac81dc0 | **good-15 + the stale jet-hop fix** (good-4's one nav fix that prevented zone deaths) ported into the good-3 navigation. Sim: zone deaths 3→1 in 96 matches, +0.40 ± 0.47 | 5.25 |
| 2 | `good-17` | 195a423 | **Scaling**: supply drops (3 cubes + full HP) ahead of healing in cover and opportunistic fights, up to 70 s away; crate 18→32, drone 45→60 | 5.2 |
| 3 | `good-19` | 692371d | **Explore for a laser** until 120 s while armed without one, never take a mortar (sim: gun+lightning ≈4.5 vs gun+laser ≈6) | 5.25 |
| 4 | `good-20` | 375d715 | **More aggression** on good-15 (laser + good-3 nav, 5.19): engage ratio 1.1→1.6, start fights from 40 % HP (was 60 %), heal below 40 % (was 55 %). The heal-more variant (good-8) lost 0.17 | 5.3 |
| 5 | `good-23` | 810982c | **Berserk** on good-22 (laser + nav3 + hop fix): in squad/unknown rounds never retreat unless the TTK ratio is above 4. 90 % of sim deaths happen in retreat mode, and retreating in the open from gunners at 80–100 m does not break contact (sim seed 11: 30 s of retreat/heal/engage dithering, 1095 → 69 HP) | 5.2 |
| 6 | `good-18` | ec61cd7 | **Break contact when a second hunter is in sight** (unless the target is below 30 % HP): the sim's deaths are 2–7 hunters converging | 5.2 |
| 7 | `good-21` | 2f800aa | **Seek by memory and by sound** on good-15: walk to remembered house bots, or toward gunfire heard in the last 6 s (110 m along the bearing) | 5.3 |
| 8 | `good-24` | 7788a2d | **Never take a mortar, and give up a run for a weapon under fire after 6 s** on good-22. In the sim gun+mortar matches score ≈2.8, and one 12 s run onto a roof under fire went 1355 → 275 HP | 5.25 |
| 9 | `good-12` | 025bc42 | (old nav) seek + scale, compare with good-7. Superseded by good-17 | — |
| 10 | `good-13` | a57b78e | (old nav) seek + picky, compare with good-7 | — |

good-16 (ground-only) was submitted at 3:29. good-22 is the stacking candidate (laser + nav3 + hop fix): put it next.
good-24 is now last: the sim says no-mortar is −0.72 (noise ±0.4).
Base for new tags: good-22's profile `laser+nav3x+fixx`. Bases for the older queued tags are named in each row.

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
