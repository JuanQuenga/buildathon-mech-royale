# Handoff (MacBook agent → next agent), 11-21 ~05:20 ET

## Current best
**good-31 (1f7fa6f) = 5.56 official** (12th of ~160 at the time). Branch `var/F-steady`, built on main with
`DEFAULT_PROFILE = "laser+nav3x+fixx+steadyx"`:
- `laser`: cube_greed + a laser valued above lightning as the first secondary
- `nav3x`: frozen good-3 navigation module `bot/navigate3.py` (main.py swaps it in)
- `fixx`: good-4's stale jet-hop fix ported into navigate3 (`hopfix3`)
- `steadyx`: engage strafe reversals every 3–5 s (normal: 1.2–2.4 s) ← the step change (+0.35 over good-22)

## Queue (docs/REVIEW.md "Please submit", all natively gated, tags pushed)
1. good-35 (370d88e): good-31 + rage (stack)
2. good-36 (1ca1a5a): reversals every 6–10 s
3. good-37 (0ebc659): no sideways movement while engaging
4. good-38 (a9a0bd3): never reverse (orbit)
5–7. good-32/33/34 are on the rage base without steady strafe (range 170 m / laser hunt / duel discipline). Rebase
   them onto the new best before using them (e.g. `laser+nav3x+fixx+steadyx+snipex`).

## How variants work
`bot/brain.py: DEFAULT_PROFILE` picks a profile; profiles compose with `+` (deltas in `PROFILES`: `ragex`, `hidex`,
`snipex`, `lhuntx`, `hretx`, `stillx`, `slowx`, `orbitx`, `steadyx`, `jukex`, `fixx`, `nav3x`, `perchx`, `capx`,
`hopcx`, ...). `MECH_PROFILE=...` overrides locally. To make a tag: create a branch from main, change only the
`DEFAULT_PROFILE` line, gate it, tag it. main itself stays `"base"`. Nav-related switches are read by
navigate3 from `brain.P` (`strafe_mode`, `jet_cap`, `hopfix3`, `combat_hop`).

## Official results (48 fixed seeds; tag-to-tag noise ≈ ±0.1)
| Tag | Score | What |
| --- | --- | --- |
| good-31 | **5.56** | good-22 + steady strafe (3–5 s reversals) |
| good-27 | 5.25 | good-22 + rage (hunt by memory/sound, engage ratio 1.6, fight from 40 % HP, berserk) |
| good-22 | 5.21 | laser + nav3 + stale-hop fix |
| good-15 | 5.19 | laser + nav3 |
| good-30 | 5.19 | good-22 + juke (0.3–1.0 s reversals) |
| good-14 | 5.17 | seek + nav3 |
| good-10 | 5.10 | greed + laser first |
| good-17 | 5.06 | good-14 + scale (drops first, crate/drone values) |
| good-26 | 5.04 | good-22 + hide (break LOS from every house bot) |
| good-7 / good-11 | 5.00 / 5.00 | seek / seek + laser + no mortar |
| good-6 / good-25 | 4.96 / 4.96 | greed / good-22 + combat hops |
| good-3 | 4.88, 4.85 | (rerun of the same commit) |
| good-16 | 4.88 | ground-only routes |
| good-8 / good-9 | 4.79 / 4.79 | fresh (heal after kill) / chaos control (good-3, scan phase shifted) |
| good-4 / good-5 | 4.58 / 4.46 | old nav / good-4 + good-3 brain |

**Lessons:** movement in fights and navigation dominate. Stricter hop-energy rules −0.4; ground-only −0.29; combat
hops −0.25; juke ±0; steady strafe +0.35. Behaviour knobs (seek, fresh, scale, hide, rage, laser) are worth ≤ 0.15.

## Planned follow-ups (not started unless noted)
- Explore the strafe direction further on the good-31 base (good-36/37/38 queued). Also: strafe only when the
  enemy aims at us; time reversals to enemy shots/laser charge; shoot-then-move (stand still while the gun/laser
  fires at long range, move between shots). The likely mechanism is our own accuracy (torso slew lag + lead error
  on reversals).
- Airborne-target gun lead: it uses gravity only, while real house bots jet-hop ~30 % of the time. This is a
  hit-rate fix in the same family. Not started.
- Rebase good-32/33/34 onto the steady base.

## Tooling (MacBook paths; Linux defaults still work)
- Env: `MECH_KIT=<mechfight-kit dir>`, `MECH_PY=<python with numpy>`; `MECH_REPLAY` for the sample replay.
- Native gate: `NATIVE_ONLY=1 eval/check.sh <ref>` (the Docker gate is the default on Linux). The `native_slow` test
  flaked once or twice at load ~5 on the laptop (1 late reply); a rerun passed.
- **The sim cannot rank variants:** paired noise is ±0.4 at 96 seeds, and the same profile scored 5.38 and 5.09 on
  two runs. It was wrong about good-3 vs good-4, juke, fresh, laser-on-seek and steady. Use it for crashes and FFA
  sanity only. Calibration: `--squad join_per_loss=0.6` puts good-4 near its official level.
- FFA sanity (sim, 64 seeds, lineup `bot*1,builtin:expert*5,builtin:hard*5,builtin:brawler*3,builtin:sniper*2`):
  the nav3/laser/rage/hide profiles all scored 10.7–11.0 vs 10.2 for seek.
- The public cast (`wss://watch.joinbuilders.org/live`, `/state`) streams FFA Showdowns of the top-16 practice
  teams, with a full `result` record per mech (kills, damage by weapon, first-weapon time, cubes, upgrades). The feed
  backfills from tick 0 on connect. Seen: top practice bots take their first weapon at 0–5 s (ours ~12 s), and the
  practice #1 (azing) died first in that FFA.
