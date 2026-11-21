# Integration notes (integrator -> teammates)

Newest first. The integrator runs `eval/check.sh <sha>` (native + Docker sandbox + stress streams) and sim batches
after each push and records regressions here and in `eval/RESULTS.md`. Nobody's work is silently reverted.

## 2026-11-21 (early) — integrator: juke reverted, stale jet-hop bug, policy restart

- **Juke (0.3-1.0 s reversals beyond 80 m) is OFF by default** (`MECH_JUKE_RANGE`, default 1e9; "80" re-enables).
  It cut incoming damage in the duel harness, but in full squad matches it cost kills: paired 64-seed A/B on the
  same commit, juke off +0.47 (95% CI +0.06..+0.86). Our own hit rate while juking is the likely cause.
- **Stale jet-hop state** (e12b612): if the brain changed goal mid-hop, `m["jet"]` stayed set forever and nav never
  replanned again (straight-line steering into pits/walls). Now cleared once the hop ends or is abandoned.
  `MECH_NAVLOG=1` prints a nav state line per second to stderr.
- main re-forks the policy process if it dies mid-match (up to 3x); `eval/crash_bot.py` in the gate.
- Shared-machine budget: `eval/compare.py` now runs `nice -n 10` with `--jobs 2` (≈ 4 busy processes).

## 2026-11-21 (early) — integrator: zone failures found and fixed; possible sim collision artifacts

- Fixed (b890076, 9cfbfd2): big mechs (6-10 cubes) beside tall buildings retried a 35 m jet hop they couldn't
  afford (nav started hops at 60 % of the needed energy under urgency, planned 2.0 energy/m vs ~2.4 real) and sat
  25-31 s outside the zone. Hops now need 2.4/m with no urgency discount, impossible hops are dropped, failed hops
  trigger replans with smaller jet caps and finally as a smaller mech; combat stops spending lightning energy while
  nav waits at a hop base. FFA zone episodes in 32 seeds: 3 -> 0.
- **For sim (possible collision artifacts, please check):** squad seed 123 (both runs): our mech at (22.6, 233.1)
  stands at z 0.7 under bridge prism #5 (base 9.65 m → 8.95 m clearance < 9 m mech height) and can never move
  again (x,y frozen for 26 s while jumping/boosting). Squad seed 111: our mech at (-9.7, 54.7, 0.3) is inside
  building prism #99 (base −2.86, top 24.81). The rulebook says lower overhangs are walls and you never end up
  inside a wall, so the real server should not allow either; maybe mech-mech push / knockback skips the wall test?


- Nav is live: `bot/arena.py` + committed `bot/navbake.npz` (1 MB, rebuilt with `tools/nav/bake.py`), details and
  timings in `docs/nav.md`. `Arena.load` ~140 ms. Tests: `python -m unittest discover -s tests/nav`.
- `arena.plan / path_len` are **budgeted and resumable** (reverse A*, searches cached per goal): a pending
  search returns `[goal]` / `1.35 x straight line` and finishes over the next calls. Keep goals stable
  (same point for a few ticks) to benefit. `path_len` costs <= ~2 ms per call; `navigate.eta` uses 1.5 ms.
- New on `Arena` (all optional): `can_see(obs_feet, tgt_feet, obs_cubes, tgt_cubes)` (vision rule, trees count),
  `can_shoot(shooter_feet, tgt_feet, ...)` -> clear aim point on the body or None (stops at the target cylinder, so a
  target hugging a wall counts), `exposure(points, threats)`, `flank_positions(pos, target, rng, other_threats=)`,
  `hold_spots(center, radius, threats)`, `nearest_cover` accepts a list of threats, `walkable/standable/clearance`,
  `plan_full` (waypoints with 'walk'/'jet' hops), `jet_energy(climb)`, `size_class(cubes)`.
- New in `navigate`: `safe_route(state)` -> `{point, eta, leave_by, inside_now, t_edge}` for the zone (point =
  walkable spot inside the NEXT circle with a margin; `leave_by` = latest match time to start moving);
  `edge_time(zone, p, t)`; `zone_circle_at(zone, t)`.
- Nav uses jump+jet hops when the planner says so (roofs, the stadium bowl: the field is a pit, spawning there
  needs a hop out). It waits at the hop base for energy unless `urgency >= 0.8`. `NavOut.blocked` is True while
  recovering from a stall; replans happen inside nav.
- `los` with trees costs ~3x `shot_clear` (p50 ~90 us vs ~40 us); prefer `shot_clear` / `can_shoot` for shots.
- `navigate.zone_eta_at(state, x, y[, z])`: seconds of walking from ANY spot into the next circle (travel-time
  field nav builds in the background each phase; straight line x 1.3 until settled). Cheap (~10 us): use it to
  vet loot/cover/chase targets against the zone. `Arena.reach_spot(item, horiz, vert)` gives a standable spot
  within pickup reach (nav already uses it when a goal can't be stood on).

## 2026-11-20 (late) — combat -> nav: evasion measured

Sim (`sim/py tests/combat/duel_harness.py evade`): damage per second the built-in `expert` gun deals to us while
we only move, 3 × 15 s per cell. Strafe = reverse every 1.2–2.5 s (what `_engage_dir` does now); juke = reverse
every 0.3–1.0 s at random; `+dodge` = follow `threats.dodge` when its urgency > 0.15.

| our legs | 60 m | 120 m | 180 m |
| --- | --- | --- | --- |
| stand | 107 | 93 | 72 |
| strafe 1.2–2.5 s | 109 | 77 | 61 |
| strafe + dodge | 89 | 61 | 47 |
| **juke 0.3–1.0 s** | 95 | **56** | **27** |
| juke + jump | 103 | 64 | 27 |
| juke + dodge | 94 | 68 | 46 |

Suggestion: in `engage`/`retreat` with enemies in LOS beyond ~80 m, reverse the lateral direction at random
0.3–1.0 s intervals and don't blend the bullet dodge into it (reacting to bullets makes us predictable);
keep dodging mortar shells: new `threats.dodge_shell` / `shell_urgency` carry the shell-only evasive vector
(`threats.dodge` still mixes bullets + shells + laser chargers, unchanged). Under ~60 m nothing helps much:
break LOS or win the trade.

## 2026-11-20 (late) — combat -> integrator/nav

- Added fields (subclasses, nothing renamed): `threats.ThreatsX` adds `contacts, dodge_urgency, mode_guess,
  squad_evidence, killable, safe_dirs, face_yaw, n_can_hit, incoming_damage, rear_threat, shorted_until`;
  `threats.EnemyX` adds `aim, cubes, radius, height, flip_rate, since_flip, flip_min_gap, agility, jumpy, airborne,
  rear_exposed, age, charge_t, holds_mortar, hp_frac, bearing, model_dps`; `combat.CombatOutX` adds `weapon, p_hit,
  laser_charging, laser_charge, dumping, damaging, reason`. Full list and semantics: `docs/combat.md`.
- Nav: `CombatOutX.laser_charging` = our movement is halved this decision (server rule). Combat never starts a
  charge when `intent.mode in (retreat, heal)` or `urgency >= 0.7`, but an ongoing charge is held until a good
  release (or dumped into the sky when `allow_fire` turns False). `threats.dodge` + `dodge_urgency` (0..1) is the
  combined evasive unit vector (bullets: perpendicular to the path; shells: away from the predicted blast).
- Brain: `combat.duel_estimate(state, enemy_threat)` -> `win_p, ttk_me, ttk_them`; `combat.recommend_loadout({"zone_radius": r,
  "enemy_weapons": [...]})`; `combat.summary(state)` (per-weapon shots/hits/damage) is worth adding to `brain.summary`.
  Sim duels: gun-only loses 1-9 to gun+laser at 100 m and 0-10 to gun+lightning at 40 m; equal loadouts win 9-10/10
  vs the sim's expert tier. A second weapon early is the biggest combat lever.
- Combat respects: `allow_fire`, `target_id` (NPC only when targeted or shooting us), `shoot_crate` (crates only
  then), `face` (when nothing to shoot and no danger), `mode == engage` + `target_id` -> laser pre-charge behind
  cover if seen < 2 s ago.

## 2026-11-20 (late evening)

- **Deadline guard is now a forked child process** (fb2966c). The policy (all modules) runs in a niced child;
  the parent only reads stdin, forwards the newest obs, and replies with the child's action or a fallback at
  26 ms. Reason: with the thread guard, a long numpy/C call held the GIL and the parent missed its own cutoff
  (bot-internal max 42 ms on one pinned core). Consequences for you: nothing prints to stdout from the child
  (it's redirected to stderr anyway); module state lives in the child; `MECH_GUARD=thread` restores the old mode.
- **Timing on the stress streams (eval/make_stress_stream.py: 15 visible mechs + 12 npcs, 80 projectiles, 40
  pickups, 1 CPU docker)**: combat `threats.assess` p99 13 ms / max 18 ms is now the biggest cost (was 0.8 ms
  in the placeholder). Please cap per-tick work (e.g. shot_clear only for the 4–6 most relevant enemies,
  projectile checks vectorised or limited to those within ~150 m and closing). Target p99 < 4 ms there.
  `navigate.step` p99 3 ms / max 4 ms: fine. Brain's own cost came from calling `arena.nearest_cover` every
  tick (3 ms each): now cached.
- Real sim matches (fixture-like loads): whole-policy p99 ~9–20 ms. Fine for now, but every ms we add raises
  the fallback rate on busy late-game ticks.

- **New Intent field `max_speed`** (m/s, None = no cap). Nav: clamp `move` length to `max_speed / walk_speed`
  and don't boost. The brain sets it to ~4.5 m/s in `hold` (moving under `sound.step_speed` = 5 m/s is silent:
  no step sounds for others to hear).

- **Request to sim (what eval/compare.py will call):** something like
  `python3 sim/run_matches.py --bot "<cmd that starts our bot>" --mode squad|ffa --seeds 0-19 --jobs N --out f.jsonl`
  with one JSON line per match: `seed, mode, place, score (16-place), death_t, death_cause
  (zone|weapon kind|npc|fall|unknown), kills, cubes, hp_at_end, missed_replies, bot_stderr_tracebacks`, and
  `MECH_STATS=<file>` exported to the bot process (main.py writes its timing/decision stats there at exit).
  FFA mode: ideally 16 copies of an opponent pool (example bot, our older tags, simple variants) so we can
  pit candidate vs baseline. Any interface is fine — I'll adapt; just please document it in `sim/README.md`.

- **Shared working tree.** All four of us edit the same checkout, so plain `git pull --rebase` fails whenever
  someone has unstaged edits. Use `git pull --rebase --autostash origin main` then `git push origin main`, and
  `git add <your paths>` only.
- **Run the gate on commits, not the working tree:** `eval/check.sh [sha]` builds a temporary worktree of that
  commit, so half-finished edits in the shared tree don't pollute results.
- `bot/navbake.npz` (nav) is untracked. The image only contains committed files under `bot/` and `arena/`: if
  `Arena.load` needs it, commit it (watch the 20 MB repo cap) or generate it in `bot/build_cache.py` at image build
  time (writes to `/app/cache`, see docs/INTERFACES.md). `Arena.load` must still work without it.
- Brain calls `navigate.eta(state, goal_xyz)` (optional; falls back to `arena.path_len / walk_speed`, then
  straight line × 1.25). It is called at most ~once per decision for the zone target, cached 1 s per 8 m cell.
- Brain uses `Threats.attackers`, `EnemyThreat.can_hit_me / visible / dist / hp / weapons / last_seen_t`. Combat:
  please keep `attackers` = ids that damaged us in the last ~3 s (the brain's fight-or-flight logic depends on it).
- Intent fields combat should honour: `allow_fire` (False while healing: dealing damage resets regen),
  `target_id` (may be an NPC drone id in `mode="loot"`: drones are worth 2 cubes), `shoot_crate`, `face`.
- Intent fields nav should honour: `goal` (None = hold / strafe), `mode` (`engage` with `target_id` +
  `desired_range`; `retreat` / `heal` = goal is cover or away from `avoid`), `urgency` (≥ 0.8 = zone emergency,
  boost allowed), `allow_boost`.
