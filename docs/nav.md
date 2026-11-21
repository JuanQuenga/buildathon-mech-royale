# Navigation and geometry (`bot/arena.py`, `bot/navigate.py`)

Owner: nav. Offline tools in `tools/nav/`, tests in `tests/nav/` (`python -m unittest discover -s tests/nav`).

## Data

| What | Where | Size | Built |
| --- | --- | --- | --- |
| Prisms (rings, holes, base/top) | `world.json` (`hello.map.dir`) | 259 prisms, 9,786 ring vertices | parsed at `Arena.load` |
| Terrain | `terrain.i16` | 1070 × 724, 1 m | read at load (float32 + `array('f')`) |
| Trees | `world.json` | 1,560 | parsed at load |
| Nav bake | `bot/navbake.npz` (committed) | 1.0 MB | `tools/nav/bake.py arena/v2 bot/navbake.npz` (numpy + scipy + matplotlib, 4 s) |

`Arena.load` takes ~140 ms on this machine (geometry 70 ms, bake 70 ms). If the bake is missing or broken,
LOS/shot tests still work and every nav query degrades to straight lines (`ok_nav = False`). The bake records the
SHA-1 of `world.json`; a mismatch is logged and the bake is still used (the map is fixed).

### Solids and segment tests

* Every ring/hole edge goes into a **16 m uniform grid** (`cell_edges`, numpy index arrays) with per-cell max top
  and min base. A query walks the cells the 2D segment crosses (Amanatides–Woo DDA), drops cells entirely above
  or below the segment's z-range, and runs **one vectorised 2D segment/edge intersection**. A crossing whose
  height is inside `[base, top]` of that prism is a wall hit. This is exact for side faces, including
  sub-metre "sliver" walls that raster methods miss.
* Exact extras (Python, rare): a segment that **passes through a slab** between two side crossings without
  touching a face inside its height range (steep shots through a bridge deck), and **endpoints inside a solid**.
* Terrain: bilinear samples every 1 m, only when the segment dips below the per-cell terrain maximum; the first
  and last 0.6 m are ignored so feet-level endpoints don't self-occlude.
* Trees (vision only, §8): trunks = cylinders `trunkR` from `z` to `z + crownBase`; crowns = ellipsoids centred at
  `(crownX, crownY, z + (crownBase + height)/2)` with radii `(crownR, crownR, (height − crownBase)/2)`. Sight is
  blocked when `exp(−canopyDensity · chord) < canopyBlockT` (0.35 / 0.25 → about 4 m of crown).
  **Unverified**: the server's crown shape and attenuation formula are not published.
* `shot_clear` / `los` results are cached per tick (0.1 m-rounded endpoints).

### Nav bake (1 m vertex grid, `[j, i]` = `(minY + j, minX + i)`)

* `g` — standing surface of the ground column: terrain raised to the top of any prism whose base is less than
  9 m above the current surface (buildings → roof, river decks → deck). Prisms leaving ≥ 9 m headroom are
  **ceilings** (`ceil`): elevated bridges, walk-under.
* `dwall` / clearance — horizontal distance to the nearest prism edge that is a wall *for a mech standing on
  that vertex's surface* (top > g + 1.2 and base < g + 9·scale), from per-prism EDTs on a 0.5 m sub-grid with
  densely sampled edges (error ≤ 0.36 m). A river-bed walker is blocked by the deck's side; a deck walker isn't.
* Walkable for size class k (`scale` 1.0 / 1.25 / 1.5 = 0 / 5 / 10 cubes): clearance ≥ `2.5·scale + 0.4`,
  headroom ≥ `9·scale`, inside bounds. Connectivity: |rise| ≤ 1.2 m between neighbours, 1.6 m/m on
  terrain-to-terrain edges (see *verified*), never uphill into terrain steeper than 50° (σ = 1 m smoothed).
  `walk` bit k = main ground component; bit k+3 = any component ≥ 20 cells (roofs, stadium bowl and stands).
* **4 m lattice** per class: one node per block, snapped to the best-clearance standable vertex (main ground
  preferred). Directed **walk/drop edges** to the 8 neighbours (32 samples: never rise > 1.2 m; unstandable
  samples are allowed only while airborne after a drop). **Jet edges** to the 16 blocks at distance 1–2 that are
  not walkable: climb = highest surface on the line − start surface (≤ 40 m), no ceiling over the line.
  Class 0: 47k nodes, 354k walk/drop edges, 52k jet edges.

### Planning

* `plan_nodes` is a **reverse weighted A\*** (w = 1.4) from the goal node toward the start node, kept in a small
  LRU (10 searches keyed by goal node, size class, jet cap). Each call runs for at most `budget_ms`; an unfinished
  search is resumed by the next call (any nearby start: the heuristic re-targets). `plan()` returns `[goal]`
  while pending, `[]` when the goal is unreachable.
* Edge costs: length + up to 3 m clearance penalty near walls; jets add 25 m + 1.5 m per metre climbed (so the
  planner prefers walking unless a hop saves a lot) and are limited by `jet_cap` (energy is waited for at the hop
  base, see below).
* `plan_full` string-pulls walk runs (binary-searched walk-line checks, 1 ms deadline; the rest stays raw and is
  shortcut on the fly) and returns `(x, y, z, 'walk'|'jet', climb)` waypoints.
* Start/goal snapping prefers nodes on the same level as the given z (roof vs street).

### Steering (`navigate.step`)

1. Replan when the goal moves > 4 m, every 4 s, when the path empties or a jet hop failed.
2. Pop reached/passed waypoints; look 1–2 waypoints ahead when straight-walkable (corner cutting).
3. Engage mode: hold `desired_range` with alternating strafes (1.2–2.5 s, tick-seeded jitter).
4. Blend `threats.dodge`; push away from `intent.avoid` when retreating/healing.
5. Probe the direction with a 5 m walk-line and fan out ±20°, ±40°… to the closest walkable direction (wall
   sliding without touching walls).
6. Boost: urgency ≥ 0.7 with energy > 12, retreat with energy > 35, urgency ≥ 0.4 with energy > 80, never with
   `max_speed`. `max_speed` caps the move length (silent walking).
7. **Stall detection**: commanded movement for 1.2 s but < 20 % of the expected displacement → recovery:
   back-off + sidestep (0.6 s), then jump + jet toward the target (1.4 s, if energy allows, never more than 7 m
   above the start), and replan. `blocked=True` while recovering. A stall within 3.5 m of the goal counts as
   arrival (pickup reach) instead. In the air, `boost` (= jet) is only ever on during a planned hop or a jet
   recovery: walking off a roof with boost held would otherwise rocket the mech onto the next roof.
8. **Jet hops**: wait at the base until energy ≥ `2·(climb − 2) + 6` (or ≥ 60 % of it when urgency ≥ 0.8), then
   jump + boost toward the landing node, boost until feet are 1 m above the climb top, keep moving in; done
   when grounded within 2.5 m of the landing level, otherwise replan.
9. Off the main component with no plan (noise island, pit): head for the nearest main node; stalls trigger jumps.
10. Goals that cannot be stood on (items against walls, on roof edges) are replaced by `Arena.reach_spot` (nearest
    standable spot within 3.2 m horizontal / 3.8 m vertical, same level preferred).
11. Bad input (NaN position or goal) → zero move / goal ignored; any exception → straight-line fallback, logged
    (rate-limited) to stderr.

Zone helpers: `navigate.eta(state, goal)` (path seconds at walk speed + 0.5 s; inf if unreachable),
`navigate.safe_route(state)` → `point` (inside the next circle with a margin, walkable), `eta`, `leave_by`
(`min(edge reaches us, shrink_end) − eta − 3 s`), `inside_now`, `t_edge`; `navigate.edge_time(zone, p, t)`.

### Zone travel-time field

`Arena.zone_field(cx, cy, r)` is a multi-source reverse Dijkstra over the lattice (walk + jet edges) from the
nodes in a 12 m band just inside the circle; interior nodes are 0 and never expanded; capped at 450 m.
`navigate.step` advances the field for the NEXT circle (radius − 5 m) with whatever is left of a 1.5 ms budget,
so it completes ~100–150 decisions after the circle is announced (90–150 slices measured, 160–260 ms total).
`navigate.zone_eta_at(state, x, y[, z])` → seconds to safety from any spot (field when settled, else
1.3 × straight line). Agreement with A* to the nearest circle point: median ratio 0.98–1.00 (lower when the field
finds a closer entry).

### Tactical queries (`Arena`)

* `nearest_cover(pos, threat_pos | [threats], max_dist=60)` — same-level lattice nodes within `max_dist`,
  pre-filtered with **shadow buffers** (per threat: tall-prism edges rasterised into 720 angular depth bins,
  ~0.5 ms, cached per tick), scored by distance with a penalty for moving toward the threats, then the best 8
  verified exactly (muzzle and eye → body centre and top). Shadow filter: never claims hidden when visible
  (5/3834 sampled), misses ~10 % of hidden spots (low walls, terrain).
* `exposure(points, threats)` — how many threats see each point (shadow buffers; cheap exposure map).
* `flank_positions(pos, target, rng=60, other_threats=())` — walkable spots off our bearing with a clear shot.
* `hold_spots(center, radius, threats)` — final-circle spots: low exposure, walls on several sides.
* `can_see(observer, target)` (vision rule: eye → centre or top, trees count), `can_shoot(shooter, target)`
  (muzzle → best clear point on the body; returns the aim point), `shot_clear`, `los`, `inside_solid`,
  `ground_z`, `surface`, `clearance`, `walkable`, `standable`, `walk_line`, `size_class`, `jet_energy`.

## Timings

`taskset -c 0 python tools/nav/bench.py` (Python 3.13, numpy 2.5; this host had load average ~35 on 16 cores
while measuring, so tails are pessimistic). Microseconds unless noted.

| Query | p50 | p99 | max |
| --- | --- | --- | --- |
| `Arena.load` | 143 ms | | |
| `height` | 1.0 | 1.8 | 7.5 |
| `ground_z` | 1.7 | 4.5 | 37 |
| `shot_clear` (< 200 m, uncached) | 40 | 183 | 425 |
| `shot_clear` (cached) | 2.2 | 3.2 | 73 |
| `los` with trees (uncached) | 89 | 304 | (noise spikes) |
| `can_see` | 112 | 313 | 516 |
| `can_shoot` | 18 | 248 | 280 |
| `walk_line` 5 m / < 200 m | 5.1 / 39 | 6.7 / 62 | 19 / 242 |
| A* complete, cold, 100–700 m (unbudgeted) | 4.5 ms | 14.9 ms | 17.6 ms |
| `plan_full` on a finished search | 1.1 ms | 1.3 ms | 1.7 ms |
| `plan(budget_ms=2)` first call | 2.1 ms | 2.6 ms | 3.0 ms |
| `nearest_cover` (60 m, cold) | 1.1 ms | 1.8 ms | 1.9 ms |
| `navigate.step` in closed loop (navsim, 16 routes) | 0.05 ms | 1.8 ms | (noise) |
| `navigate` in the full bot on the kit checker | | 4.4 ms | 7.0 ms |

Same bench inside the match sandbox (`docker run --cpus 1 --memory 512m --read-only --user 65534`, image built
from commit 2768eeb, host load average ~75): `Arena.load` 267 ms, `shot_clear` p50 40 / p99 171 us, `los` p50 88 /
p99 312 us, `walk_line` 5 m p50 6 us, A* cold p50 5.2 / p99 17 ms (unbudgeted), `plan_full` cached p50 1.1 ms,
`plan(budget_ms=2)` max 2.3 ms, `nearest_cover` p50 1.0 / max 2.1 ms. The kit checker on that image: PASS, ready
in 1.7 s, whole-bot answer p50 2.8 / p99 7.5 / max 12.3 ms.

Memory: the arena adds ~50 MB RSS (numpy grids + edge arrays); policy process peak 73 MB on the checker.

## Movement capabilities: verified vs not

Verified against the public replay (`tools/nav/replay_check.py`, `tests/nav`):

* **Wall collision radius is exactly 2.5 m**: over 14k grounded samples the closest exact distance from a mech
  centre to a blocking prism edge is 2.50 m. No mech body sample (feet+1, +4.5, +8) is ever inside a prism.
* **Grounded mechs stand on the baked surface** (z − g within ±0.2 m at p1/p99; bilinear terrain at the centre).
* **Shots**: all 86 server-traced laser/lightning segments are clear in our geometry up to their end; all 15 beams
  that stopped early stopped at a prism (7) or the terrain (8).
* **Terrain steps**: house bots walk (no boost) over local bilinear slopes up to 1.36 m/m end-to-end and 1.57 m/m
  over 0.5 m, i.e. steeper than the nominal 50° (1.19). The bake therefore allows 1.6 m per 1 m terrain edge and
  judges "steep" on a σ = 1 m smoothed surface.
* **Roof climbing is used by house bots**: 7 of 16 mechs stood on building tops (435 samples). Their hops: a fixed
  ~2 s jet, ~30 energy for ~15 m of rise (2.4 energy/m beyond the free jump); best case 2.37/m. Theory with
  boost held from the jump (vz pinned at 8.9 m/s): 1.7/m. We plan with 2.0/m + 6.
* Max observed rise speed 9.4 m/s (`max_rise_speed` 10), horizontal speed p99 15 m/s (boost 19.5).
* **Stadium bowl**: the field and lower stands are a separate component; the outer rim is a 20–32 m drop. House
  bot 2 spawned inside, hopped around the stands for 200 s and died to the zone. Our planner leaves via a jet
  hop (tested in the sim).

Not verified (assumptions):

* Roof landing details (the rulebook's edge rules) beyond "bots end up on roofs"; jet hops in navsim run on the
  sim's physics, not the server's.
* Canopy model (shape, density formula) — vision only.
* Slopes: the exact server rule (normal vs per-tick rise) is unknown; we use the replay envelope.
* Under-bridge clearance for grown mechs: headroom ≥ 9·scale per class (scale 1.25 / 1.5).
* Elevated bridge decks are separate components reachable only by jets; no edges were tested on them.

### Exposure-aware routing (measured, off by default)

`plan_full(..., avoid=[threat feet])` makes lattice nodes that a threat can see (shadow buffer, 200 m) cost
`EXPO_COST` extra per metre. On 12 random 250 m routes with a threat near the middle : penalty 0.6 → exposed metres 2136 → 2100 (−2 %), planning 21 → 267 ms; penalty 1.5 → 2376 → 1940
(−18 %) for +15 % length, planning 24 → 796 ms. The campus is open; one threat within 200 m sees most routes, so
`navigate.ROUTE_AVOID = False`. Retreat/heal still steer away from `intent.avoid` locally and the brain picks cover
goals with `nearest_cover`.

## Known gaps

* No incremental repair when a mech/crowd blocks a corridor (stall recovery + 4 s replan handle it).
* `los` with trees is ~3× the cost of `shot_clear`; combat should prefer `shot_clear`/`can_shoot`.
* Jet hops wait for energy at the base even under fire (unless urgency ≥ 0.8).
* The zone field takes ~10–15 s of match time to complete after the next circle is announced (it runs in the
  spare part of a 1.5 ms per-step budget); until a spot is settled `zone_eta_at` falls back to 1.3 × straight line.
