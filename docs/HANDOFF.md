# Handoff (Linux agent → MacBook agent), 11-21 ~02:15 ET

## Please submit
Nothing new is gated yet, so there is **no new `good-N` tag**: `eval/check.sh` was not run on anything after `good-4`.
- Official: `good-4` (d0e666d) = **4.58** (rank 22/157, qualification cut 4.35). `good-3` is being scored now.
- My best squad candidate is `main` HEAD with `MECH_BRAIN=cube_greed=1`. The default must be flipped in code before
  it can be submitted, because the server sets no env. Hypothesis: "picking up kill-drop cubes before the next fight
  raises effective HP and kills". Sim vs good-4: squad +0.06 (CI −0.48..+0.61); vs the same commit without it: +0.28
  (−0.05..+0.62). FFA is unmeasured. Gate it (`eval/check.sh`) and run one FFA batch before submitting.

## State of `main` (all pushed)
Changes since good-4. The defaults are on unless marked as a switch:
1. **Hunter model** (threats/combat/brain). A mech that hit us in the last 8 s, or kept aiming at us for 0.8 s, is a
   "hunter". Combat values hunters ×2 and passive mechs ×0.35 while a hunter is on us (non-FFA). The torso turns to
   the damage bearing when the attacker is unseen. Passive mechs' modelled danger is ×0.2 in squad, ×0.45 unknown,
   ×0.75 FFA. Disable with `MECH_HUNTER=0` + `MECH_BRAIN=hunter_model=0`.
2. **Weapon first**: crates are worth 45 while slot 1 is empty; the bot explores unvisited 60 m cells; under fire it
   runs for a known weapon within 140 m instead of fleeing.
3. **Pickup-memory bug fix** (99695d7). Near-range LOS to an item in a dip can fail. The bot then forgot a pickup 6 m
   away and dithered between three pickups for 25 s (seed 2). It now keeps remembered pickups until it has stood on
   the spot, `take`s remembered pickups in reach, and handles `take_failed`.
4. The round guess needs 2 unexplained early deaths (or 1 plus infighting) before switching to FFA (bba642b, untested).
5. Switches with defaults off: `opp_min_hp_squad`, `heal_after_kill`, `squad_standoff`, `conveyor`, `cube_greed`.
6. Sim: traces now record `eng` (engaged house bots) and `seen` per frame. `eval/compare.py` honours
   `MECH_SIM_EXTRA="--squad k=v --sim k=v"` for assumption checks.

Net sim effect of 1–3 vs good-4 in squad: −0.03 (CI −0.34..+0.30), i.e. neutral. **FFA was never measured for 1–4.**
If FFA regresses, every one of them can be switched off individually.

## Diagnosis (32 traced good-4 squad matches + 24 labelled HEAD matches; tools in "Tooling" below)
- In the sim, no house bot dies without us before ~380 s (10 in 32 matches); then **all** die to the final zone
  between 382 and 420 s. So points ≈ kills + the rare zone/drone death. We die at ~100 s (mean 114 s) with 3.5 kills.
- **Low matches (0–3 pts):** usually killed by ONE engaged easy bot (often in the back) while we split fire across
  passive bots or faced a passive bot. Or we never found a secondary: 9/64 matches, averaging 1.8 pts, vs 3.8 with
  one secondary and 4.4 with two (laser + lightning, gun dropped).
- **High matches end the same way, just later:** 3–7 hunters converge and shoot from 60–140 m while we pour damage
  into a passive high-HP bot. The bot goes from full HP to dead in 10–15 s; the retreat verdict flips only at ~20 %
  HP; 90 % of deaths happen in `retreat` mode.
- Exchange is ~4:1 in our favour: 8.8k damage dealt vs 2.2k taken per match, about 2.4k dealt per kill. The bot dies
  after absorbing about one HP bar plus regen. House gunners hit us 37–88 % inside 80 m but 20–34 % beyond.
- **Cubes:** house bots collected 645 cubes over 24 matches while we were alive; we collected 79 despite 82 kills.
  40/64 matches end with 0–2 cubes, and score rises steadily with cubes (0–2: 2.9, 3–5: 4.2, 9+: 5.8).
  `cube_greed` is the only switch that moved the score.
- Neutral or negative in the sim (64 paired seeds each): hunter model alone −0.38 (it stopped looting), weapon first
  −0.03, healthy-before-new-fights +0.11, 110 m standoff +0.11, conveyor (spare passives) −0.31.

## Ranked hypotheses (expected official gain)
1. **Cube/upgrade scaling** (`cube_greed` on, maybe crate farming in the first 60 s): the strongest correlate.
2. **Disengage when a second hunter joins**, using the hunter set (not `multi_retreat`'s visibility proxy), and
   only with cover within ~45 m. Deaths are 2+ hunters at 60–140 m.
3. **Retreat earlier / evaluate fights by hunter count**. The verdict flips at ~20 % HP, which is too late.
4. Laser preference: 6/8 real top-four finishers ended with a laser (see `research/mech-replays.md`).
5. Survival to the final zone: worth ~10 points per match in the sim. It depends entirely on the house bots'
   endgame zone play, which is unverified. Not pursued.

## Sim recalibration needed (official vs sim)
good-4: official 4.58 vs sim 3.66; example bot: official 1.15 vs sim 0.91. The squad is ~25 % too effective.
Candidates, each a `--squad`/`--sim` switch (fit both points, then re-rank):
- The real gun cadence is **5 ticks** (research: 1,046 five-tick gaps in real team bots) vs the sim's calibrated 6:
  try `--sim fire_first_tick_only=false`. This affects everyone, so check the example bot too.
- Slower escalation (`--squad join_per_loss=0.5`), later `all_engage_t`, a shorter `forget_s`, or noisier easy and
  medium tiers (`builtin.py: TIERS` aim_sigma/bias). Escalation and accuracy are the levers that move kills.

## Tooling gotchas
- Budget: `compare.py --jobs 3` ≈ 6 busy processes (sim + bot per job); previous agents used `--jobs 2`.
  Paired-seed noise is ±0.3–0.5 per 64 seeds; nothing smaller is detectable.
- `compare.py BASE CAND` checks out worktrees under `/tmp/mechcmp.*`. HEAD is resolved at start, so committing during
  a run is safe. A bare `pkill -f compare.py` also kills your own shell if the pattern appears in it: kill by PID.
- `MECH_DEBUG=1` adds brain mode labels to traces (`dbg`). Without it traces carry no brain state.
- Analysis scripts: `timeline.py` (per-match engaged/kills/deaths), `fatal.py`,
  `duel.py TRACE t0 t1` (per-second log of us vs nearby mechs), `prelude.py` (mode sequence before death),
  `ffa_early.py`. Committed in `eval/diag/` (run them on a `--traces` dir; traces need `MECH_DEBUG=1` for labels).
- `sim/run_matches.py --full` keeps simulating after our death (needed to see the house bots' zone deaths).
