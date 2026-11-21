# Results log

**The sim is a proxy. Official practice scores are the ground truth: whenever they disagree with the sim, trust the
official numbers and say so here in bold.**

## Official results (coordinator pastes real submission scores here)

| Date/time (ET) | Commit | Tag | Official practice mean (48 matches) | Notes |
| --- | --- | --- | --- | --- |
| — | example bot | — | 1.15 | organiser-stated baseline |

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
