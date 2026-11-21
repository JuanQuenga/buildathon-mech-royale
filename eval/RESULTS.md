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

## Conformance and timing (eval/check.sh)

| Commit | native p99 / max (ms) | docker p99 / max | stress big p99 / max | stress late p99 / max | Result |
| --- | --- | --- | --- | --- | --- |
| 634dbe1 | 1.7 / 4.9 | 2.2 / 2.4 | 8.5 / 9.2 | 8.6 / 10.7 | PASS (0 missed) |

(checker-measured round-trip incl. 1 ms newest-obs grace and docker stdin proxy; bot-internal p99 2.8–3.8 ms on stress)

## Sim results (paired seeds) — see eval/compare.py

| Date | A (base) | B (cand) | Mode | Matches | mean(16-place) A | B | Δ (95% CI) | Death causes B (zone/outgunned/stuck/fall) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
