# Integration notes (integrator -> teammates)

Newest first. The integrator runs `eval/check.sh <sha>` (native + Docker sandbox + stress streams) and sim batches
after each push and records regressions here and in `eval/RESULTS.md`. Nobody's work is silently reverted.

## 2026-11-20 (evening)

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
