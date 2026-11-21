# Combat and threat model (`bot/combat.py`, `bot/threats.py`, `bot/ballistics.py`)

Owner: combat. Standard library only. Tests: `python3 -m unittest discover -s tests/combat` (48 tests, no numpy, ~2 s).
Sim measurements: `sim/py tests/combat/duel_harness.py hitrate|duel ...` (needs numpy, uses `sim/`).

## Interfaces

| Call | Returns | Notes |
| --- | --- | --- |
| `threats.assess(state)` | `ThreatsX` (subclass of `state.Threats`, only adds fields) | never raises; falls back to a bare enemy list |
| `combat.step(state, intent, threats)` | `CombatOutX` (subclass of `state.CombatOut`) | never raises; on error: hold fire, keep current aim |
| `combat.duel_estimate(me, enemy, dist=None)` | `{win_p, ttk_me, ttk_them, my_dps, their_dps}` | `me` = `WorldState` or dict; `enemy` = `EnemyThreat` or dict |
| `combat.weapon_value(kind, ctx)` / `loadout_value(kinds, ctx)` / `recommend_loadout(ctx)` | float / float / `[((a, b), value)]` | ctx keys: `zone_radius`, `dist`, `enemy_weapons`, `other` |
| `combat.summary(state)` | per-weapon shots / hits / damage this match | eval; `MECH_COMBAT_STATS_DIR=<dir>` also dumps it every 50 decisions |

Fields added on top of the frozen interface:

- `ThreatsX`: `contacts` (unseen enemies from sounds / beams / damage: `pos`, `sigma`, `t`, `kind`, `id`, `source`),
  `dodge_urgency` (0..1), `mode_guess` (`squad` / `ffa` / `unknown`), `squad_evidence`, `killable` (mech ids we
  can probably finish in ~3 s), `safe_dirs` (16 × `(yaw, score)`, best first: directions that move away from the
  danger), `face_yaw` (where the torso should point to keep the front arc on the danger), `n_can_hit`,
  `incoming_damage`, `rear_threat`, `shorted_until`.
- `EnemyX` (in `threats.enemies`): `aim`, `cubes`, `radius`, `height`, `flip_rate` (direction reversals/s),
  `since_flip`, `flip_min_gap`, `agility`, `jumpy`, `airborne`, `rear_exposed` (its back faces us: our hits ×1.5),
  `age`, `charge_t`, `holds_mortar`, `hp_frac`, `bearing`, `model_dps`.
- `CombatOutX`: `weapon` (primary this decision), `p_hit`, `laser_charging` (movement is halved while true),
  `laser_charge`, `dumping` (heal requested mid-charge: the charge is being fired into the sky), `damaging`
  (a trigger that can deal damage is pulled — regen will reset if it hits), `reason`.

Contract details honoured: `intent.allow_fire=False` → no damaging trigger at all; a charging laser is pitched
to the sky and released there (letting go fires), unless it is a sure kill. NPC drones are shot only when they
are `intent.target_id` or are shooting us. Crates only when `intent.shoot_crate` names them. With no target the
torso faces `threats.face_yaw` (danger), else `intent.face`, else the newest heard contact, else scans ±50°
around the direction of travel (vision is a 120° wedge).

## Physics facts — verified vs assumed

Verified against the public 10 Hz replay (`mechanics-v2-16.jsonl.gz`) and the kit's real observation stream:

| Fact | Evidence |
| --- | --- |
| Torso slew is a per-axis clamp: yaw `turn_rate`, pitch `pitch_rate`; pitch limits −0.7 / 1.3 | max Δyaw per 0.1 s = 0.523 (4 × 1.3 gyros), Δpitch = 0.300; test `test_replay_slew_limits` |
| Projectiles do not inherit shooter velocity | gun speeds 140.00 ± 0.05 m/s regardless of shooter speed; mortar launch speed 72 with shooters at up to 15 m/s |
| Shot origin: `muzzle_height` (gun) / `height + 0.5` (mortar) above the feet, plus `radius + 0.5` m **horizontally** (`3·cos(pitch)`) | mortar fits < 0.1 m over 3.7 s; with a 3-D offset the residual is −3·sin(pitch). Test `test_replay_shells_follow_model`. Reported in `docs/SIM_ISSUES.md` (sim now matches) |
| Timing: a projectile fired in decision tick N is at `origin + v·τ (− g τ²/2)` at time `t_N + τ` | same fit (shell 3.6 m further along than "spawn at fire tick" would give) |
| Mortar gravity 22, speed 72 | second differences = 22.000; launch speeds 70–72.8 (aim-rounding noise) |
| Gun spread is a per-axis Gaussian with σ ≈ `spread_deg` | 152 steady-aim shots: σ 0.58° per axis (incl. 0.01 rad aim rounding) |
| Live balance ≠ replay balance | replay gun 140 m/s; live `hello.config` and the kit stream 252 m/s. Everything is read from `hello.config` / weapon `stats` |
| House bots release lasers at a fixed 0.65 s charge; 11/39 replay laser shots hit | `charge` events all `dur 0.65` |

Assumed (rulebook prose, not observable in the replay):

- Laser: hold to charge (≤ `charge` s), release fires hitscan along the *actual* aim; release before `min_charge`
  fires when `min_charge` is reached; full charge held `hold_s` more auto-fires; damage `min_frac..1` linear in
  charge; a `short` cancels and blocks charging `short_s`. Controller follows the prose, not the wrapper comment.
- Lightning cone: we only fire when the intended victim is within ±13° of the aim and is the *nearest* object
  (mech / NPC / crate) with LOS within ±`cone_deg` — correct under both readings (half-angle 30° or full 30°).
- Which sim tick a held trigger fires on: tick 1 of the decision if `cooldown ≤ 0.05`, else tick 2 (the sim
  accumulates cooldown, so a 0.24 s gun alternates). In the replay every gun fire is on the first tick, which a
  first-tick-only server would also explain; our lead covers both (`combat.fire_tick`).
- Mortar splash falls off linearly from `splash` to `splash_edge × splash` at `splash_radius`.

## Models

**Gun lead.** Solve `|p + v_eff·(t + extra) − o| = speed·t` from the real origin (our position one tick ahead,
horizontal 3 m offset), `extra = (k−1)·0.05` for a shot on tick k. Airborne targets get gravity. Horizontal
velocity is scaled by the telegraph-process factor `f = (1 − e^{−2rτ}) / (2rτ)` (r = observed reversal rate),
the MSE-optimal lead for a target that reverses at Poisson rate r; periodic strafers get full lead right after a
reversal (`effective_flip_rate`). Fire if `p_hit ≥ 0.22` (0.12 under 60 m or killable, 0.3 with ≤ 3 rounds),
where `p_hit` = spread (σ = `spread_deg`) ⊕ target-motion σ = `(0.28 + 0.6·agility)·min(a t²/2, 2 v t)`
(0.08 for stationary targets; fitted in the sim) ⊕ jump σ, evaluated at the torso aim *after the slew to the
firing tick* (`ballistics.slew`).

**Laser state machine.** Start charging when ready (cooldown ≤ 0.1, not shorted, not retreat/heal, urgency < 0.7)
with a mech target in range — or pre-charge behind cover when engaging a mech seen < 2 s ago. While charging, aim
at the hitscan point one tick ahead. Release when charge is full and `p_hit ≥ 0.72`, early when the current
charge already kills (or we are under beam/heavy fire and charge ≥ 0.45) with `p ≥ 0.75`, and always just before
the auto-fire (`auto_in ≤ 0.15 s`). Gun keeps firing with its own lead while the laser charges.

**Lightning.** Fires when the arc's actual victim is acceptable (target, any enemy mech, a hostile NPC); keeps
a 20-energy reserve for jets (6 when finishing / interrupting a laser charger / < 25 m). Charging enemies get a
×1.6 priority (the hit shorts their laser).

**Mortar.** Low arc first, high arc for indirect fire (memory tracking gives the real position for 5 s behind
cover; high arcs need pitch ≤ 1.3, i.e. range ≳ 120 m on flat ground). The arc is checked with ≤ 6
`shot_clear` segments. Self-splash guard twice: the solution must land > `splash_radius + radius + 2.5` m from
where we will be, and the *actual* fire aim is re-simulated against the ground before pulling the trigger.

**Targets.** Score = best weapon's expected DPS at its own solution × priority / (1 + 1.5 × slew time).
Priority: mech `1 + danger/120`, ×2.5 killable, ×1.5 if it is charging a laser at us, ×3 for `intent.target_id`;
rear-exposed targets get ×1.5 damage; ×0.55 if aiming at it would turn our back (> 85°) on the most dangerous
other mech; ×1.3 hysteresis for the current target.

**Threats.** Per enemy: danger ≈ the DPS it can put on us now (weapon table × range hit model × cube multiplier ×
facing × LOS; observed DPS on us over 5 s wins if larger; +150 while it charges a laser at us; 20% latent danger
when it has no LOS but is tracked). Incoming bullets: closest approach of the relative ray to our cylinder; dodge
perpendicular to the bullet's path on the side that grows the miss. Shells: integrated against
`Arena.ground_z` to the impact; dodge away from the blast if it lands within `splash_radius + radius + 2` of where
we will be. Squad / FFA: any death we did not cause before 300 s, beams ending on another mech, or unexplained HP
drops of visible enemies inside the zone → `ffa`; nothing of that by 60 s → `squad`.

## Measured (team simulator, `sim/`, 2026-11-20)

Gun, our shooter standing, target not shooting back, 4 × 10 s per cell (`duel_harness.py hitrate --reps 4`).
"model" = mean predicted `p_hit` of the shots fired (calibration check).

| target \ range | 40 m | 100 m | 150 m | 190 m |
| --- | --- | --- | --- | --- |
| standing | 1.00 (model 1.00) | 0.99 (0.99) | 0.92 (0.91) | 0.84 (0.81) |
| walking (turns every 6 s) | 1.00 (0.99) | 0.85 (0.83) | 0.55 (0.46) | 0.47 (0.36) |
| strafing (reverses every 1.2–2.5 s) | 1.00 (1.00) | 0.80 (0.77) | 0.51 (0.44) | 0.30 (0.35) |
| juking (reverses every 0.3–1 s) | 1.00 (1.00) | 0.50 (0.68) | 0.28 (0.42) | 0.20 (0.45) |
| juking + jumping | 1.00 (1.00) | 0.83 (0.81) | 0.46 (0.60) | 0.34 (0.50) |

Other weapons (same harness, 3 × 10–12 s per cell):

| weapon | result |
| --- | --- |
| laser (with gun) | 15/15 at 40 and 100 m vs standing / strafing / juking / jumping targets; 15/15 at 190 m vs strafing and juking; one shot per 2.4 s (full cycle) |
| lightning (with gun) | 99–100% at 20 and 40 m vs every pattern (~300 DPS combined with the gun) |
| mortar | 150 DPS vs standing at 40 m, 120 at 100 m, 90 at 180 m; vs moving targets 30–100 DPS at 40 m, 10–40 DPS at 100–180 m |

Duels, 1v1 vs the sim's built-in `expert` tier (aim σ 0.45°, full lead, strafes, retreats at 35% HP), our legs
strafing (holding 28 m with lightning), 10 seeds each:

| ours | expert | range | W–L–D |
| --- | --- | --- | --- |
| gun | gun | 100 m | 10–0–0 |
| gun + laser | gun + laser | 150 m | 10–0–0 |
| gun + lightning | gun + laser | 40 m | 10–0–0 |
| gun + lightning | gun + lightning | 30 m | 10–0–0 |
| gun + mortar | gun + lightning | 80 m | 9–0–1 |
| gun | gun | 40 m | 9–1–0 |
| gun | gun | 180 m | 9–0–1 |
| gun + laser | gun + laser | 60 m | 10–0–0 |
| gun + laser | gun + lightning | 40 m | 10–0–0 |
| gun + laser | `sniper` gun + laser | 180 m | 10–0–0 |
| gun | gun + laser | 100 m | 1–9–0 (get a second weapon) |
| gun | `brawler` gun + lightning | 40 m | 0–10–0 (never brawl a lightning holder with the gun alone) |

Full squad-mode matches (whole bot, 12 seeds): gun 555/728 = 76%, laser 40/42 = 95%, mortar 3/5, lightning ~100%
(hit counts include chain hits). Mean score 1.9 (the house squad focuses the entrant; survival is brain/nav).

Value of the module: FFA, 12 seeds, 2 copies each of HEAD vs HEAD with the original placeholder combat/threats
(same brain/nav), `bot*2,bot2*2,expert*3,hard*4,brawler*3,sniper*2`: mean score 11.04 vs 7.92, kills/match 1.62
vs 0.71; paired difference +3.1 (95% CI −1.1 … +7.3). FFA, 8 seeds, 2 copies vs built-ins only: 11.5.

Evasion (what nav should do; `duel_harness.py evade`, expert gun, dmg/s taken): stand 107/93/72 at 60/120/180 m,
strafe 1.2–2.5 s 109/77/61, strafe+dodge 89/61/47, juke 0.3–1.0 s 95/56/27. Juking beats reactive bullet dodging.

Timing (threats.assess + combat.step, real `Arena`, one core, unloaded): over a recorded 865-decision sim match
thread-CPU p50 0.07 ms, p99 1.3 ms, max 2.1 ms; recorded FFA match (9 visible mechs, shells): p50 0.28, p99 0.6,
max 0.7 ms (`tests/combat/replay_smoke.py <obs.jsonl.gz>`, prints wall and CPU). Shell impacts are cached per
projectile id. Wall-clock numbers on the shared build box (load 60 on 16 cores) are scheduler noise. Under 3–4 parallel sim jobs the per-module p99 rises to ~3 ms (CPU contention).

## Known gaps

- Juking targets at ≥ 150 m: the model is ~0.15 optimistic, so the gun still fires at p ≈ 0.2–0.3 there
  (cheap: misses do not reset regen, but they cost reload time and make noise).
- No explicit "shot clear" check for chain lightning hops or for the lightning arc beyond the first victim.
- Mortar splash occlusion by walls is ignored when estimating damage on the target (it is not ignored for our
  own safety: the arc and the impact point are checked).
- House-bot behaviour in the real practice squad is unknown; duel numbers are against the sim's reconstruction.
- `weapon_value` / `duel_estimate` use modelled hit rates (table in `combat.our_hit_rate`), not online estimates.
