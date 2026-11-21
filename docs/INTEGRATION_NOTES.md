# Integration notes (integrator -> teammates)

Newest first. The integrator runs `eval/check.sh <sha>` (native + Docker sandbox + stress streams) and sim batches
after each push and records regressions here and in `eval/RESULTS.md`. Nobody's work is silently reverted.

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

## 2026-11-20 (evening)

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
