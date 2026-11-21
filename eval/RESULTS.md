# Results log

**The sim is a proxy. Official practice scores are the ground truth: whenever they disagree with the sim, trust the
official numbers and say so here in bold.**

## Official results (coordinator pastes real submission scores here)

| Date/time (ET) | Commit | Tag | Official practice mean (48 matches) | Notes |
| --- | --- | --- | --- | --- |
| — | example bot | — | 1.15 | organiser-stated baseline |
| 11-21 00:05 | d0e666d | good-4 | **4.58** (rank 22/157; cut #32 = 4.35; top 5.58) | **sim squad said 3.66: the sim is ~25 % too harsh** (example: sim 0.91 vs official 1.15). good-3 (f8db786) being scored by the coordinator |
| 11-21 ~00:30 | f8db786 | good-3 | **4.88** (rank 20/~157; cut #32 = 4.48; top 5.58) | **same seeds as good-4, +0.30 for the OLDER tag although the sim rated good-4 ≥ good-3**. good-3 is the base to beat |
| 11-21 ~00:45 | f8db786 | good-3 (rerun) | 4.85 | identical commit resubmitted: timing noise ±0.03. Any behaviour change re-rolls every match, so between-tag noise is larger (chaos control tag pending) |
| 11-21 ~01:00 | 5e2b91e | good-6 | **4.96** (rank ~26; cut 4.77) | main + cube_greed (hunter model, weapon-first, pickup fix, 2-death FFA guess). New best |
| 11-21 ~01:35 | 37f5786 | good-5 | 4.46 | good-4 + good-3 brain.py: did NOT recover good-3. Either the regression is outside the brain, or tag-to-tag noise is ~±0.3 |
| 11-21 ~01:40 | 3dd9bcd | good-7 | **5.00** | main + seek profile (sim +0.22 vs greed). New best, but only +0.04 over good-6 |
| 11-21 ~01:55 | 696e4ec | good-8 | 4.79 | main + fresh profile (heal after kill, new fights at 85 %). Sim said +0.20 vs greed; official −0.17 vs good-6 |
| 11-21 ~02:10 | e6718e7 | good-9 | 4.79 | chaos control: good-3 with only the idle torso-scan phase shifted. −0.08 vs good-3 → tag-to-tag noise ≈ ±0.1 |
| 11-21 ~02:32 | 1cd7676 | good-10 | **5.10** | greed + laser first (laser valued 3.6 > lightning 3.0). +0.14 vs good-6 (its base). New best |
| 11-21 ~02:38 | ddbc83a | good-11 | 5.00 | seek + laser first + no mortar: = good-7 (seek). Laser-first gave +0.14 on greed, 0 on seek |
| 11-21 ~02:50 | 2db6e00 | good-14 | **5.17** | good-7 (seek) + good-3's navigate.py: +0.17. good-4's nav changes (jet-hop energy rules) cost score in the real game. New best |
| 11-21 ~03:00 | 7cce2c2 | good-15 | **5.19** | good-10 (laser first on greed) + good-3 navigation. New best by a hair; nav and laser gains do not fully add |
| 11-21 ~03:33 | f8decf1 | good-16 | 4.88 | good-14 + ground-only routes (no jet hops, no roof weapons): **−0.29. Hops/roofs help in the real game** |
| 11-21 ~03:37 | 195a423 | good-17 | 5.06 | good-14 + scale (drops first, crate/drone values up): −0.11, no gain |
| 11-21 ~03:52 | ac81dc0 | good-22 | **5.21** | good-15 + stale jet-hop fix inside nav3. New best |
| 11-21 ~04:00 | 0e4b36f | good-25 | 4.96 | good-22 + combat hops (jump+jet ~10 m every 2–3 s in fights): **−0.25**. Hops on routes help (good-16), hopping in fights hurts |
| 11-21 ~04:33 | 6720a56 | good-27 | **5.25** | good-22 + rage (hunt by memory/sound, engage ratio 1.6, fight from 40 % HP, berserk). New best (+0.04) |
| 11-21 ~04:37 | 4fb7820 | good-26 | 5.04 | good-22 + hide (break LOS from every visible house bot, spare passives): −0.17. The real squad does not lose enough bots without us |
| 11-21 ~04:40 | 23e597b | good-30 | 5.19 | good-22 + juke (0.3–1.0 s reversals beyond 80 m): neutral |
| 11-21 ~05:00 | 1f7fa6f | good-31 | **5.56** | good-22 + steady strafe (reversals every 3–5 s): **+0.35, the first step change**. New best |
| 11-21 ~06:00 | 370d88e | good-35 | 5.31 | good-31 + rage: does not stack (−0.25 vs good-31) |
| 11-21 ~06:10 | 1ca1a5a | good-36 | 5.13 | good-31 with reversals every 6–10 s (−0.43): 3–5 s is a narrow optimum or good-31 drew well; chaos controls good-46/47 queued |
| 11-21 ~06:25 | 0ebc659 / a9a0bd3 | good-37 / good-38 | 5.25 / 5.35 | no sideways / orbit: all four good-31 neighbours 5.13–5.35 (mean 5.26). Sim: behaviour-neutral re-roll SE ≈ 0.27 per 48-match score |
| 11-21 ~06:45 | 8ff6019 / 72710d6 | good-46 / good-39 | 5.29 / 5.27 | re-roll of good-31 (good-31 drew ~+0.27 high) / boost strafe: no gain |
| 11-21 ~07:26 | b0592f6 | good-47 | 5.40 | second re-roll of good-31: policy mean 5.42 over 3 draws (5.56, 5.29, 5.40) |
| 11-21 ~07:48 | 633caaf / 0208ea2 / 6d78ab0 | good-40 / good-48 / good-42 | 5.25 / 5.35 / **4.73** | airborne lead / gun discipline: both within noise of the 5.42 policy mean; break contact at the 2nd hunter clearly worse (dropped) |
| 11-21 ~08:48 | 0b3d535 / a3de7d6 / 3539b7c / a634383 | good-r1 / r2 / r3 / good-50 | 5.25 / 5.29 / 5.48 / 5.35 | re-rolls: base policy mean 5.38, SD 0.12 over 6 draws; opening hold-fire costs nothing in practice |
| 11-21 ~10:48 | 2d14b1f / 964946c / 6301311 / 8f2c4d8 | good-52 / r5 / good-53 / good-44 | 5.17 / 5.27 / 5.31 / 5.33 | jet60 worse; FFA candidate v1 no practice cost; laser hunt neutral |
| 11-21 ~11:43 | ab489ab / b2d0122 / 9ac13f6 | good-54 / good-56 / good-57 | 5.44 / 5.15 / 5.48 | peek mean 5.30 (cycle rarely engages in sim: 19 % of engage decisions); isolate first draw 5.48 |
| 11-21 ~11:50 | 6e21d12 | good-59 | 5.33 | commit (kill conversion): = base mean |
| 11-21 ~12:48 | 5feec86 / fdac016 / 4265b9c / d2a1dcf | good-61 / 62 / 63 / 64 | 5.19 / 5.27 / 5.42 / 5.44 | arm-first mean 5.23 (no); cycle 5.42, arm-first+cycle 5.44 (within noise) |

### Sim calibration vs official (MacBook, sim f683099, good-4, seeds 0-47)

| Squad setting | Sim score | Kills | Alive |
| --- | --- | --- | --- |
| default (early 1, join_per_loss 1, all engage 300 s, 6-tick gun) | 3.69 | 3.58 | 111 s |
| `--sim fire_first_tick_only=false` (5-tick gun, everyone) | 3.29 | 3.17 | 98 s |
| `--squad all_engage_t=360` | 3.38 | 3.33 | 98 s |
| `--squad join_per_loss=0.5` | 4.88 | 4.83 | 124 s |

Official good-4 = 4.58: escalation speed is the lever; the official level sits between join_per_loss 1 and 0.5.

## Known-good tags

A tag is "good" only after `eval/check.sh <sha>` passes (native + Docker with the exact sandbox flags, recorded and
stress streams, zero missed replies, no stderr tracebacks) and, once the sim exists, many sim matches with no
tracebacks / no fallbacks.

| Tag | Commit | Gate | Notes |
| --- | --- | --- | --- |
| good-1 | 634dbe1 | check.sh PASS (no sim yet) | skeleton, example-bot behaviour |
| good-2 | e9ea4c2 | check.sh PASS (no sim yet) | brain v1 on placeholder nav/combat |
| **good-4** | **d0e666d** | check.sh PASS at load 5 (docker p99 3.8 ms / stress p99 12.6 ms, 0 missed); 256 sim matches, 0 missed replies, 0 tracebacks | good-3 + zone fixes (realistic jet energy, stale jet-hop state, heal/retreat goals inside circle), policy auto-restart, juke off. Sim de87b36, 64 seeds vs good-3: squad **3.66** vs 3.59, FFA **11.33** vs 10.88 (both within noise); zone deaths 4→1 |
| good-3 | f8db786 | check.sh PASS; 64 sim matches, 0 missed replies, 0 tracebacks | nav + combat + brain + process guard. Sim 0fb1d99: squad **3.38** (example 0.91), FFA **10.91** (example 7.34) |

## Conformance and timing (eval/check.sh)

| d0e666d (good-4), load 5 | native p99 3.4 / max 6.7 | docker p99 3.8 / max 10.7 | stress big p99 12.6 / max 15.5 | stress late p99 9.4 / max 9.9 | PASS, 0 missed, + slow-policy and crash tests |

Caveat: the build machine is shared and often at load average 50+ on 16 cores; latency numbers and the bot's
fallback counts in sim runs (e.g. 1667 fallbacks over 32 squad matches for f8db786 = ~5% of decisions) are
inflated by that. Unloaded docker --cpus 1 runs of the recorded stream show policy p99 ~8 ms.

| Commit | native p99 / max (ms) | docker p99 / max | stress big p99 / max | stress late p99 / max | Result |
| --- | --- | --- | --- | --- | --- |
| 634dbe1 | 1.7 / 4.9 | 2.2 / 2.4 | 8.5 / 9.2 | 8.6 / 10.7 | PASS (0 missed) |

(checker-measured round-trip incl. 1 ms newest-obs grace and docker stdin proxy; bot-internal p99 2.8–3.8 ms on stress)

## Sim results (paired seeds) — see eval/compare.py

| Date | A (base) | B (cand) | Mode | Matches | mean(16-place) A | B | Δ (95% CI) | Death causes B (zone/outgunned/stuck/fall) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 11-20 ~22:30 | example | 7ff832a (brain v1 + combat v1 + Arena, navigate.py = placeholder) | squad | 24 | 0.08 | 0.92 | +0.83 (+0.42..+1.29) | gun 20, zone 2, laser 1, mortar 1; 0 missed, 0 tracebacks; alive 66s→118s |
| 11-20 ~22:30 | example | 7ff832a | ffa (1 bot + 15 builtin) | 24 | 5.25 | 8.08 | +2.83 (+0.50..+5.29) | gun 14, laser 3, mortar 1, survived 6; alive 58s→171s |
| 11-20 ~23:50 (sim 0458b19) | 7ff832a | fb2966c (nav + combat v1 + process guard) | squad | 24 | 2.62 | 3.67 | +1.04 (+0.25..+1.83) | gun 22, laser 2 (zone 3→0); kills 2.58→3.62; alive 154s→118s |
| 11-20 ~23:50 (sim 0458b19) | 7ff832a | fb2966c | ffa | 24 | 10.17 | 11.08 | +0.92 (−1.00..+2.67) | survived 7→8; kills 1.12→2.04 |

Note: the sim itself changed between 52a06b3 and 0458b19 (house bots' zone pathing, focus vision): absolute numbers
are only comparable within one sim commit (see the "sim" column).
| 11-21 ~00:45 (sim 0fb1d99) | example | f8db786 (good-3) | squad | 32 | 0.91 | 3.38 | +2.47 (+1.97..+3.00) | gun 27, laser 3, mortar 1, zone 1; kills 3.31; alive 159s→103s; round guess squad 6/unknown 23/ffa 3 |
| 11-21 ~00:45 (sim 0fb1d99) | example | f8db786 (good-3) | ffa | 32 | 7.34 | 10.91 | +3.56 (+1.81..+5.38) | gun 17, laser 3, survived 12; kills 1.72; alive 87s→218s |
| 11-21 ~01:10 (sim f8db786) | f8db786 | ef732c2 (juke 0.3–1.0 s beyond 80 m, travel further/roofs for 1st secondary) | squad | 32 | 3.28 | 3.44 | +0.16 (−0.38..+0.69) | 2 weapons at end 78%→88%; 1 zone death (new) |
| 11-21 ~01:10 (sim f8db786) | f8db786 | ef732c2 | ffa | 32 | 11.41 | 11.22 | −0.19 (−1.62..+1.31) | neutral; 1 zone death (new) |
| 11-21 ~01:50 (sim f8db786) | a28e180 | a28e180 + MECH_BRAIN=multi_retreat=0.35 | squad | 32 | 3.25 | 3.47 | +0.22 (−0.16..+0.59) | neutral/slightly positive, not adopted yet |
| 11-21 ~01:50 (sim f8db786) | a28e180 | + heal_below_squad=0.75 | squad | 32 | 3.66 | 3.56 | −0.09 (−0.47..+0.28) | **3 zone deaths** → led to a28fc26 (heal/retreat goals inside the circle) |
| 11-21 ~01:50 (sim f8db786) | a28e180 | + engage_ratio_squad=0.8 | squad | 32 | 3.53 | 3.53 | +0.00 (−0.78..+0.81) | neutral |
| 11-21 ~01:50 (sim f8db786) | a28e180 | + retreat_ratio=1.1 | squad | 32 | 3.66 | 3.44 | −0.22 (−0.84..+0.44) | neutral/negative |

**Noise floor:** the same commit run twice on the same 32 seeds scores 3.25–3.66 in squad (real-process timing
makes matches non-deterministic). Differences under ~0.5 per 32 seeds are not detectable; use ≥ 96 seeds for
small effects.
| 11-21 ~02:30 (sim bf499dc) | good-3 (f8db786) | bf499dc (juke, roof weapons, zone field, detection, inside-circle goals, jet energy rules) | squad | 64 | 3.45 | 3.36 | −0.09 (−0.48..+0.30) | zone 3→2; neutral |
| 11-21 ~02:30 (sim bf499dc) | good-3 (f8db786) | bf499dc | ffa | 64 | 10.92 | 10.06 | **−0.86 (−1.92..+0.16)** | survived 25→17, zone 0→2 (seeds 24, 35). **Likely regression** → found stale jet-hop state bug (e12b612) |
| 11-21 ~02:50 (sim c4fa09a) | 49147f3 | 49147f3 + MECH_BRAIN=retreat_needs_cover=1 | ffa | 64 | 10.05 | 10.17 | +0.12 (−0.70..+1.02) | neutral; not adopted |
| 11-21 ~02:50 (sim c4fa09a) | 49147f3 | 49147f3 + retreat_needs_cover=1 | squad | 64 | 3.36 | 3.42 | +0.06 (−0.36..+0.50) | neutral |
| 11-21 ~03:05 (sim de87b36, load ~8) | good-3 | e12b612 (all fixes incl. stale-jet fix) | ffa | 64 | 10.67 | 10.27 | −0.41 (−1.44..+0.62) | zone 3→1, survived 16→12 |
| 11-21 ~03:05 (sim de87b36, load ~8) | good-3 | e12b612 | squad | 64 | 3.67 | 3.14 | **−0.53 (−0.91..−0.17)** | **regression**; zone 4→0 but kills 3.59→3.05. Bisecting. |
| 11-21 ~03:20 (sim de87b36) | good-3 | a77011d (juke + roof weapons + zone field ETA) | squad | 64 | 3.56 | 3.28 | −0.28 (−0.62..+0.08) | bisect: regression already here; zone 3→0 |
| 11-21 ~03:30 (sim de87b36) | good-3 | a28e180 (+ detection) | squad | 64 | 3.66 | 3.25 | −0.41 (−0.89..+0.06) | bisect |
| 11-21 ~04:00 (sim de87b36) | 0e30c54 | 0e30c54 + MECH_JUKE_RANGE=1e9 (juke off) | squad | 64 | 3.14 | 3.61 | **+0.47 (+0.06..+0.86)** | juke was the regression → off by default |
| 11-21 ~04:10 (sim de87b36) | 0e30c54 | + old loot params (no roof/far weapons) | squad | 64 | 3.30 | 3.11 | −0.19 (−0.53..+0.17) | keep new loot params |
| 11-21 ~04:20 (sim de87b36) | 0e30c54 | + use_zone_field=0 | squad | 64 | 3.28 | 3.25 | −0.03 (−0.33..+0.27) | neutral; keep field (safer zone ETAs) |
| 11-21 ~04:50 (sim de87b36) | good-3 | d0e666d (good-4) | squad | 64 | 3.59 | 3.66 | +0.06 (−0.33..+0.47) | zone 2→0 |
| 11-21 ~04:50 (sim de87b36) | good-3 | d0e666d (good-4) | ffa | 64 | 10.88 | 11.33 | +0.45 (−0.62..+1.58) | survived 21→26, kills 1.78→2.08, zone 0→1 |
| 11-21 ~05:20 (sim 3c9d011) | good-3 (2 copies) | good-4 (2 copies), **same matches** + 12 built-ins | ffa h2h | 24 (48 samples each) | 10.04 | 9.69 | −0.35 (±2.2) | noise, but good-3 better on 16/24 seeds and more kills (1.92 vs 1.23); good-4 0 zone deaths vs 2. Worth an official practice run of both. |

### 11-21 squad step-change search (owner: solo agent) — diagnosis first, see docs/REVIEW.md

Diagnosis (32 traced squad matches at good-4, `--full`, sim traces now record the squad's engaged set):
in the sim **no house bot dies without us before ~380 s** (10 non-us deaths in 32 matches), then all of them die to
the final zone between 382 and 420 s. Points ≈ our kills. Bad matches (0-3 pts): mostly killed by ONE engaged easy
bot while we spread fire over passive bots or faced a passive bot with our back to the attacker (seed 9: 7 s of rear
hits in `hold`), or never found a secondary weapon (9/64: mean 1.8 pts vs 3.8 with one, 4.4 with two). Good matches
end the same way, just later: 3-7 hunters converge from 60-140 m while we hit a passive high-HP bot; we go from
full HP to dead in 10-15 s and the retreat verdict flips at ~20 % HP.

| Date | A (base) | B (cand) | Mode | Matches | A | B | Δ (95% CI) | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 11-21 ~00:00 (sim 3fee0be) | 3fee0be, hunter model off | 3fee0be (hunter model: prioritise mechs that hit us, discount passive mechs, face unseen attackers) | squad | 64 | 3.70 | 3.33 | −0.38 (−0.86..+0.08) | stopped looting: 19/64 ended without a secondary (base 9/64) |
| 11-21 ~00:25 (sim 11d7cb9) | good-4 | 11d7cb9 (hunter model + weapon first: crates while unarmed, explore, run for a known weapon) | squad | 64 | 3.53 | 3.50 | −0.03 (−0.34..+0.30) | 2 weapons at end 84→91 %, kills 3.48→3.44 |
| 11-21 ~00:50 (sim 3e27987) | 3e27987 | + opp_min_hp_squad=0.85, heal_after_kill=1 | squad | 64 | 3.45 | 3.56 | +0.11 (−0.22..+0.44) | neutral |
| 11-21 ~01:05 (sim 3b015a6) | 3b015a6 | + squad_standoff=110 | squad | 64 | 3.53 | 3.64 | +0.11 (−0.19..+0.41) | neutral; laser deaths 10→17 |
| 11-21 ~01:20 (sim 81d2689) | 81d2689 | + conveyor=1 (fight only hunters, spare passive house bots) | squad | 64 | 3.59 | 3.28 | −0.31 (−0.66..+0.03) | passive kills are worth more than the hunter each adds (in this sim) |
| 11-21 ~01:40 (sim 6946cf7) | 6946cf7 | + cube_greed=1 (grab kill-drop cubes before the next fight) | squad | 64 | 3.47 | 3.75 | +0.28 (−0.05..+0.62) | best single switch; cubes are the only lever that moved |
| 11-21 ~02:10 (sim 6946cf7) | good-4 | 6946cf7 + cube_greed=1 | squad | 64 | 3.72 | 3.78 | +0.06 (−0.48..+0.61) | FFA half of this run was stopped (machine handoff): **FFA unmeasured** |

### 11-21 ~01:00 profile screen (MacBook, sim 97fccf5, `--squad join_per_loss=0.6`, seeds 0-95, same seeds)

| Profile (main 833cdf0) | Score | Kills | Alive |
| --- | --- | --- | --- |
| base | 4.77 | 4.73 | 119 s |
| greed (= good-6) | 4.82 | 4.76 | 105 s |
| seek | 5.04 | 5.01 | 116 s |
| hret (break contact at 2 hunters) | 4.85 | 4.83 | 123 s |
| fresh (heal after kill, new fights at 85 %) | 5.02 | 4.95 | 115 s |
| good-3 | 4.94 | 4.85 | 138 s |
| greed + laser_first (laser 3.6 > lightning 3.0) | 5.38 (Δ +0.55 ± 0.42 vs greed) | 5.28 | 116 s |
| picky (unknown-mode fight rules in squad) | 4.93 (+0.10) | 4.90 | 112 s |
| scale (crate 32, drone 60, drops first, eta 70) | 4.90 (+0.07) | 4.82 | 103 s |
| stack (seek + fresh) | 5.14 (+0.31) | 5.07 | 114 s |
| stack2 (seek + fresh + scale) | 5.16 (+0.33) | 5.08 | 103 s |

Loadout at death vs points (sim, greed / laser profiles): gun+laser 5.8 / 6.1, laser+lightning 5.8 / 6.0,
gun+lightning 4.3 / 4.9, gun+mortar 2.6 / 2.9, gun only 2.3 / 1.7.
| farm (seek + explore for crates/drones while armed until 150 s) | 4.97 (+0.15 vs greed, −0.07 vs seek) | 4.92 | 116 s |
| laser2 (greed + laser first + no mortar) | 5.29 (+0.47 vs greed) | 5.20 | 115 s |
| lseek (seek + laser first + no mortar) | 4.76 (**−0.28 vs seek**) | 4.70 | 109 s |

**The sim's paired noise at 96 seeds is about ±0.4.** Laser-first looked +0.55 on greed but −0.28 on seek. Official runs (±0.1) decide.

**Sim repeatability:** the laser profile on the same 96 seeds scored 5.38 one run and 5.09 the next. The sim cannot resolve effects below ~0.4; use it only for crashes and large effects.

## Predictions before scoring (written when queued; official result filled in after)
Base policy (`laser+nav3x+fixx+steadyx`) true mean 5.34, SD 0.13 per draw.

| Tag | Change (one each) | Prediction | Official |
| --- | --- | --- | --- |
| good-65 | slow6: 6 m/s cap while engaging | 5.45 (real leaders fire at ~6 m/s; sim says our accuracy is speed-independent, so +0.1 at most unless the real aim penalty is large) | **4.77** (clearly worse: moving slowly while fighting the squad costs ~0.6; good-66/67/68 withdrawn) |
| good-66 | stand1: stand with ≤ 1 attacker in sight | 5.40 | **4.19** (submitted before the withdrawal; standing to fire is disastrous) |
| good-67 | close60: slow6 + 60 m laser range | 5.35 | withdrawn after good-65 |
| good-68 | slow6 twin (r37x) | same as good-65 | withdrawn after good-65 |
| good-58 | isolate twin (r34x) | 5.42 (isolate 5.48 one draw; sim +0.08 ± 0.12) | **5.44** (isolate mean 5.46 over 2 draws, +0.12 vs base) |
| good-69 | cycle twin (r38x) | 5.40 (cycle 5.42; arm-first+cycle 5.44; sim +0.08 ± 0.12) | **5.21** (cycle mean 5.32 = base) |
| good-70 | isolate + cycle | 5.45 | **5.21** |
| good-55 | FFA candidate (openhold + ffahide3): practice check | 5.34 | withdrawn: practice cost already measured via good-50 (5.35) and good-53 (5.31) |
| good-41 | widex: full sideways weight while closing/opening range | 5.45 (movement dose-response: standing 4.19 < 6 m/s 4.77 < no sideways 5.25 < base 5.34) | **5.23** (more lateral does not help; good-71/72 not queued) |
| good-73 | weave: sideways weave (relative to the nearest attacker, 3–5 s reversals) while retreating | 5.45 (90 % of deaths come in retreat, which is radial motion; sim +0.06 ± 0.26) | **5.38** (= base) |
| good-ri41..62 | re-rolls of the isolate policy (two-draw mean 5.46) | 5.46 each | ri41 **5.17** (isolate mean 5.36 over 3 draws = base level) |
| good-43 | snipe: hold 170 m with a laser | 5.25 | |
| good-75 | cubex: grab cubes when exposure (eta × incoming DPS) < value (~90 HP-eq, +150 at an upgrade threshold) instead of never while hit | 5.45 (outside review: +0.3–0.7 kills; cubes add HP, damage and upgrades) | |
| good-76 | firefixx: re-check the gun shot against the final aim after a laser override | 5.36 (review: +8 % gun damage to mechs in its sim, score +0.02) | |
| good-77 | cubex + drop95x (supply drops first, reach 60 s) | 5.45 | |
| good-78 | keepgunx: gun valued above lightning (no gun-for-lightning swap) | 5.38 | |
| good-79 | coverfixx: retreat cover hidden from the nearest three threats (bug: `_cover_from` used only the first threat) | 5.42 (88 % of deaths happen in retreat) | |
