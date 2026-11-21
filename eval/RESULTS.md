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
| **good-3** | **f8db786** | check.sh PASS; 64 sim matches, 0 missed replies, 0 tracebacks | nav + combat + brain + process guard. Sim 0fb1d99: squad **3.38** (example 0.91), FFA **10.91** (example 7.34) |

## Conformance and timing (eval/check.sh)

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
