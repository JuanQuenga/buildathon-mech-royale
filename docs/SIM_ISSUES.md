# Simulator vs rulebook / replay disagreements

Append new items at the top. Say who found it, the evidence, and what our bot assumes.

## 2026-11-20 — nav

1. **Terrain slope rule is stricter in the sim than in the replay.** `sim/engine.py::_try_h` blocks a grounded
   step when the centre terrain rises faster than tan(50°) = 1.19 m/m over that tick's move. In the public replay
   house bots walk (grounded, no boost) over local bilinear slopes of 1.36 m/m end-to-end per 0.1 s and 1.57 m/m
   over 0.5 m windows (LiDAR spikes, stadium stands), e.g. mech 2 at t 26.1 s near (-219.6, 77.0). The server rule
   is probably based on a smoothed normal. Bot assumption: terrain edges up to 1.6 m per 1 m are walkable,
   steepness judged on a σ = 1 m smoothed surface (`tools/nav/bake.py`). Effect in the sim: mechs can get stuck
   on LiDAR spikes that the server lets them walk over.
2. **Agreements worth keeping:** wall collision radius 2.5 m exactly (replay min distance to a blocking edge
   2.50 m); jet rise speed pins at ~8.9-9.4 m/s; grounded z equals the bilinear terrain / prism top at the centre.
   House bots' jet hops spend ~2.4 energy per metre of rise (fixed 2 s jets), theory ~1.7.

## 2026-11-20 — combat

1. **Shot origin has no vertical offset (mortar, verified; gun, consistent).** `sim/engine.py::_shot_origin` puts
   the origin `radius + 0.5` m along the full 3-D aim. In the public replay (`mechanics-v2-16.jsonl.gz`) every
   mortar shell fired with a steady aim fits `origin = feet + (3·cos(pitch)·cos(yaw), 3·cos(pitch)·sin(yaw),
   height + 0.5)` with residuals < 0.1 m over 3.7 s of flight; with the 3-D offset the residual is exactly
   `−3·sin(pitch)` (−2.7 m at pitch 1.1). Gun bullets agree within the replay's 0.01 rad aim rounding (they are
   fired near pitch 0, so it barely matters for them). Bot assumption: horizontal-only offset
   (`bot/ballistics.py::shot_origin`). Test: `tests/combat/test_ballistics.py::test_replay_shells_follow_model`.
   Effect in the sim: high-pitch mortar shells start ~2.7 m higher than on the server.
2. **Fire tick parity (open question).** In the replay all 1061 gun fires, 57 mortar fires, 47 lightning zaps and
   40 laser charge starts happen on odd ticks (= the first sim tick after a decision); laser releases are on even
   ticks. Gun gaps per mech are 8, 10, 12 … ticks (never 5–7), but that replay runs a different balance (gun
   bullets fly 140 m/s, not 252), so a 0.4 s cooldown there would explain the gaps too. The sim accumulates
   cooldown and fires on whichever tick it is ready (a 0.24 s gun alternates ticks 1 and 2 of a decision).
   Bot assumption: a held trigger fires on tick 1 if `cooldown <= 0.05` else tick 2; the gun lead adds the extra
   tick (`combat.fire_tick`). Both readings are handled.
3. **Replay balance differs from the live config.** Replay gun speed is 140 m/s (live `hello.config`: 252); slew
   (gyros 1.3 × 4 rad/s), pitch rate 3 rad/s, pitch limits −0.7/1.3, mortar 72 m/s / g 22, gun spread ≈ 0.58° per
   axis (σ) and "no velocity inheritance" all match the rulebook. Always read numbers from `hello.config` /
   weapon `stats` (the bot does).
