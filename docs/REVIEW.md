# Review: Mech Royale entry (for the human and the coordinator)

## Please submit
Newest first. Each tag passed the native gate on the MacBook (`NATIVE_ONLY=1 eval/check.sh <tag>`: unit tests,
recorded stream, slow-policy and crash tests, big and late stress streams, 0 missed replies). Run the Docker gate
before submitting.

| Prio | Tag | Commit | Single hypothesis it tests | Expected official |
| --- | --- | --- | --- | --- |
| 1 | `good-27` | 6720a56 | **Radical aggression** on good-22 (5.21): hunt house bots remembered within 60 s and 400 m, or toward recent gunfire; engage ratio 1.1→1.6; start fights from 40 % HP; seek from 50 % HP; heal below 40 %; never retreat unless the TTK ratio is above 4 | 5.3 |
| 2 | `good-26` | 4fb78205 | **Radical survival-first** on good-22: in squad rounds break line of sight from every visible house bot (shared vision is how the squad finds us), spare passive bots, never hunt, no drones, heal from 80 %; fight only mechs that hunt us. Sim: alive 188 s vs ~115 s but 4.23, because sim house bots never die without us before the final zone. This tests whether the real squad loses bots to the zone/drones mid-game | 4.5–5.8 |
| 3 | `good-30` | 23e597be | **Juke** on good-22: strafe reversals every 0.3–1.0 s beyond 80 m (normal: 1.2–2.4 s). Movement changes have the largest official effects (±0.25–0.4); the sim rejected juke (−0.47), but the sim has been wrong about movement before | 5.3 |
| 4 | `good-31` | 1f7fa6fa | **Steady strafe** on good-22: reversals every 3–5 s (better own aim, a more predictable target). The opposite of good-30 | 5.2 |
| 5 | `good-19` | 692371d | **Explore for a laser** until 120 s while armed without one, never take a mortar (sim: gun+lightning ≈4.5 vs gun+laser ≈6) | 5.25 |
| 6 | `good-23` | 810982c | **Berserk** on good-22 (laser + nav3 + hop fix): in squad/unknown rounds never retreat unless the TTK ratio is above 4. 90 % of sim deaths happen in retreat mode, and retreating in the open from gunners at 80–100 m does not break contact (sim seed 11: 30 s of retreat/heal/engage dithering, 1095 → 69 HP) | 5.2 |
| 7 | `good-20` | 375d715 | **More aggression** on good-15 (laser + good-3 nav, 5.19): engage ratio 1.1→1.6, start fights from 40 % HP (was 60 %), heal below 40 % (was 55 %). The heal-more variant (good-8) lost 0.17 | 5.3 |
| 8 | `good-18` | ec61cd7 | **Break contact when a second hunter is in sight** (unless the target is below 30 % HP): the sim's deaths are 2–7 hunters converging | 5.2 |
| 9 | `good-21` | 2f800aa | **Seek by memory and by sound** on good-15: walk to remembered house bots, or toward gunfire heard in the last 6 s (110 m along the bearing) | 5.3 |
| 10 | `good-24` | 7788a2d | **Never take a mortar, and give up a run for a weapon under fire after 6 s** on good-22. In the sim gun+mortar matches score ≈2.8, and one 12 s run onto a roof under fire went 1355 → 275 HP | 5.25 |

**Conditional: insert right after good-26 only if good-26 (hide) scores ≥ 5.3.**

| Tag | Commit | Hypothesis |
| --- | --- | --- |
| `good-28` | adbc3804 | Hybrid: hide (as good-26) until 240 s, then play good-22 normally |
| `good-29` | 190dcca7 | Hybrid: hide until 6 mechs are dead (≤10 alive), then play good-22 normally |

Submitted: good-25 (combat hops) 4.96, dropped. Base for new tags: good-22's profile `laser+nav3x+fixx`.

Official so far: good-22 5.21, good-25 4.96, good-15 5.19, good-17 5.06, good-16 4.88, good-14 5.17, good-10 5.10, good-7 5.00, good-11 5.00, good-6 4.96, good-3 4.88/4.85, good-8 4.79, good-9 (chaos control) 4.79, good-4 4.58, good-5 4.46.

## Recommended final entry
`good-22` (ac81dc0, laser first + good-3 navigation + stale-hop fix), official **5.21**, until something beats it officially.

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
