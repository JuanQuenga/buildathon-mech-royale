# Review: Mech Royale entry (for the human and the coordinator)

## Please submit
The table order is the queue. Every tag listed passed the **full Linux gate** (`eval/check.sh <tag>`: unit tests,
native + Docker with the exact sandbox flags, big and late stress streams, slow-policy and crash guards, 0 missed
replies) on 11-21 ~05:15 ET.

| Prio | Tag | Commit | Single hypothesis it tests | Expected official |
| --- | --- | --- | --- | --- |
| 1 | `good-35` | 370d88e | **Stack**: good-31 (steady strafe, 5.56) + rage. Profile `laser+nav3x+fixx+ragex+steadyx` | 5.6 |
| 2 | `good-39` | 72710d6 | good-31 + **boost-run the engage strafe** (19.5 vs 11.7 m/s) while energy > 80, off below 50 (keeps a jet reserve). Top-16 bots boost 27–44 % of their firing time in the cast; if house bots under-lead, lateral speed is what makes them miss. Sim: squad +0.38 ± 0.58, FFA +0.33 ± 2.0 (no collapse). Profile `…steadyx+sboostx` | 5.65 |
| 3 | `good-36` | 1ca1a5a | good-31 with even slower strafe reversals (every 6–10 s) | 5.6 |
| 4 | `good-38` | a9a0bd3 | good-31 with no reversals at all (orbit one way) | 5.55 |
| 5 | `good-37` | 0ebc659 | good-31 with no sideways movement while engaging (hold range only; projectile dodge kept) | 5.5 |
| 6 | `good-40` | 633caaf | good-31 + gun lead for airborne targets from their observed vertical acceleration (jetting +12 m/s² up to the 8.9 m/s cap, ballistic −g, clamped at the ground; the old lead used −g/2 while rising and missed jetting targets by up to 5 m). Profile `…steadyx+airx` | 5.6 |
| 7 | `good-41` | eff7dd6 | good-31 + full sideways motion while closing or opening range (diagonal approach instead of mostly radial). Profile `…steadyx+widex` | 5.55 |
| 8 | `good-42` | 6d78ab0 | good-31 + break contact when a 2nd hunter is in sight (the steady-base version of good-34). Profile `…steadyx+hretx` | 5.5 |

Superseded (rage base without steady strafe; gated but less informative now, run only if the queue is empty):
`good-32` (0947af6, 170 m laser standoff), `good-33` (18ce57f, laser hunt to 120 s, no mortar), `good-34` (709fd65,
break contact at the 2nd hunter). Steady-base versions follow as good-39+.

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
