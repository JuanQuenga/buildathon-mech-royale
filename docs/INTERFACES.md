# Module interfaces (stable contract)

Owner: integrator (brain/main). **Signatures and existing field meanings below are frozen.** Adding fields is fine
(tell the integrator in `docs/INTEGRATION_NOTES.md`); renaming/removing is not. All types live in `bot/state.py`.

Conventions: meters / seconds / radians, x east, y north, z up, yaw CCW from +x, positions are **feet**.
Python 3.13 in the image (`python:3.13-slim`, pinned by digest). Standard library + **numpy 2.5.5** (installed
system-wide in the image). Native testing: `/home/juan/.t3/scratch/2026-11-20-you-are-the-coordinator-for-8d9ce8ed/venv/bin/python` has numpy;
system `python3` (3.14) does not. Use relative imports inside `bot/` (`from .state import ...`).

## Call order per observation (bot/main.py, `Pilot.decide`)

```
state.update(obs)                                  # integrator: memory, tracks, damage log, regen timer
threats = threats.assess(state)          -> Threats   # combat
intent  = brain.choose_intent(state, threats) -> Intent  # integrator
nav     = navigate.step(state, intent, threats) -> NavOut   # nav     : move, boost, jump
cmb     = combat.step(state, intent, threats)   -> CombatOut # combat  : aim, fire, reload
inv     = brain.inventory(state, intent)        -> InvOut    # integrator: pick, take, drop
action  = assembled + sanitized by main (tick echoed, numbers finite, move clamped)
```

Exactly one module owns each action field. Every call is wrapped: an exception returns that module's previous
output (logged to stderr, rate-limited). After `SOFT_BUDGET` (18 ms since the obs was read) remaining modules are
skipped and their previous outputs reused. The policy runs in a worker thread; if it hasn't answered by
`HARD_CUTOFF` (30 ms) main replies with the previous continuous controls (move/boost/aim) and no fire.
**Per-module target: p99 < 3 ms, max < 10 ms on 1 CPU.** Expensive work (path planning) must be cached /
amortised across ticks (keep it in `state.scratch["<module>"]`).

## `bot/arena.py` — nav

```python
class Arena:
    @classmethod
    def load(cls, map_dir: str) -> "Arena"        # called once on hello, BEFORE `ready`; must take < 4 s on 1 CPU
    def height(x, y) -> float                      # terrain only, bilinear
    def ground_z(x, y, z_hint=None) -> float       # top walkable surface (roof/bridge/terrain) at/below z_hint
    def los(a_xyz, b_xyz) -> bool                  # sight line (buildings + terrain; trees approximated)
    def shot_clear(a_xyz, b_xyz) -> bool           # projectile/beam ray clear (trees never block shots)
    def plan(start_xyz, goal_xyz) -> list[xyz]     # waypoints excl. start incl. goal; [] = unreachable
    def path_len(start_xyz, goal_xyz) -> float     # metres along plan(); math.inf if unreachable
    def nearest_cover(pos, threat_pos, max_dist=60) -> xyz | None   # reachable spot hidden from threat eye
    def inside_solid(p_xyz) -> bool
```

The map is fixed and also committed at `arena/v2/` (copied into the image at `/app/arena`). If you want
build-time precomputation, add `bot/build_cache.py <arena_dir> <out_dir>`: the Dockerfile already runs it if it
exists, writing to `/app/cache` (read-only at runtime). `Arena.load` must still work if the cache is missing or
stale (verify file sizes / a hash of `hello.map.dir` files) — the runtime map is `hello.map.dir`.

## `bot/threats.py` — combat

`assess(state) -> Threats`: `enemies: list[EnemyThreat]` (mechs and npcs, with `dist`, `visible`, `los`,
`can_hit_me`, `facing_me`, `charging`, `danger`, `dps_on_me`), `incoming: list[ProjectileRisk]`
(`t_impact`, `miss_dist`, `dodge`), `dodge` (suggested unit evasive move or None), `attackers` (ids that hit us in
the last ~3 s), `total_danger`, `beam_risk`. `state.tracks` (id -> `Track`) already holds memory of every mech/npc
ever seen (pos/vel/hp/weapons/aim, damage to/from us); build on it rather than duplicating.

## `bot/navigate.py` — nav

`step(state, intent, threats) -> NavOut(move, boost, jump, eta, blocked)`.
Contract: go to `intent.goal` (None = hold position / small evasive moves). Respect `intent.urgency`
(≥ 0.7: boost/jet allowed to save life, e.g. zone) and `intent.allow_boost`. Apply `threats.dodge` when a
projectile will hit. When `intent.mode == "engage"` and `intent.target_id` is set, keep `intent.desired_range`
to the target, strafing. Report `blocked=True` if no progress for ~1.5 s (brain will re-plan). `eta` = seconds
along the path to goal at current speed.

Also please expose `navigate.eta(state, goal_xyz) -> float` (seconds; inf if unreachable) — the brain calls it
for zone timing (cached per goal is fine).

## `bot/combat.py` — combat

`step(state, intent, threats) -> CombatOut(aim, fire, reload, target_id)`.
Contract: shoot `intent.target_id` if set and shootable, else best target of opportunity — but **only if
`intent.allow_fire`** (healing needs 5 s of no dealing damage). Ignore NPCs unless they are the target or are
shooting us. When not shooting, aim toward `intent.face` (yaw to keep the front arc toward the threat) if given.
`intent.shoot_crate` = crate id the brain wants broken when no enemy is around. Laser trigger: releasing fires —
when `allow_fire` turns False mid-charge, decide deliberately (letting go fires the beam). Reload when it's safe.

## `bot/brain.py` — integrator

`init(state)`, `choose_intent(state, threats) -> Intent`, `inventory(state, intent) -> InvOut`,
`summary(state) -> dict` (end-of-match stats for eval). `Intent.mode` ∈
`rotate | loot | engage | retreat | heal | hold | capture`.

## Stdout / logs

Nothing but protocol on stdout. Logs to stderr only, sparingly (matches do not show stderr). At exit main prints a
`stats {...}` JSON line to stderr (latency p50/p99/max, fallbacks, per-module errors and p99), and writes it to the
file named by env `MECH_STATS` if set (the sim/eval uses that).

## Running

```
python3 -u bot/main.py                                         # from repo root
python3 <kit>/check/check.py -- python3 -u bot/main.py
docker build -t mech-bot . && python3 <kit>/check/check.py --map-dir /arena -- docker run --rm -i --network none \
  --cpus 1 --memory 512m --memory-swap 512m --pids-limit 128 --cap-drop ALL --read-only \
  --tmpfs /tmp:rw,size=64m --user 65534:65534 -v "<kit>/arena:/arena:ro" mech-bot
```

Env knobs: `MECH_HARD_CUTOFF_MS` (30), `MECH_SOFT_BUDGET_MS` (18), `MECH_STATS` (path), `MECH_DEBUG` (=1 attaches
debug drawings from `brain.debug`).
