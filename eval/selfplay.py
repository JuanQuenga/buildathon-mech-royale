#!/usr/bin/env python3
"""Per-variant FFA self-play table from run_matches --out jsonl files (var:<profile> entries carry their name).
    python3 eval/selfplay.py out1.jsonl [out2.jsonl ...]
Prints mean (16 - place) ± 95% CI per name, kills, alive time, survival share, deaths by cause, and the detector's
mode guess timing (first 'ffa' time; share of matches that ever guessed 'squad')."""
import collections, json, statistics as S, sys
rows = []
for f in sys.argv[1:]:
    for l in open(f):
        r = json.loads(l)
        if "error" not in r:
            rows.append(r)
by = collections.defaultdict(list)
for r in rows:
    by[r.get("name") or r.get("label")].append(r)
print(f"| Variant | n | mean (16 − place) | kills | alive s | survived | ffa detected (median s) | ever 'squad' | tracebacks |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for name, R in sorted(by.items(), key=lambda kv: -S.mean(x["score"] for x in kv[1])):
    sc = [x["score"] for x in R]
    ci = 1.96 * S.stdev(sc) / len(sc) ** 0.5 if len(sc) > 1 else 0
    mf = [((x.get("bot_stats") or {}).get("brain") or {}).get("mode_first") or {} for x in R]
    ffa_t = sorted(m["ffa"] for m in mf if "ffa" in m)
    sq = sum(1 for m in mf if "squad" in m)
    surv = sum(1 for x in R if x["death_cause"] == "survived")
    alive = S.mean((x["death_t"] or x["sim_t"]) for x in R)
    tb = sum(x.get("bot_stderr_tracebacks") or 0 for x in R)
    det = f"{ffa_t[len(ffa_t)//2]:.0f} ({len(ffa_t)}/{len(R)})" if ffa_t and mf[0] != {} else "-"
    print(f"| {name} | {len(R)} | {S.mean(sc):.2f} ± {ci:.2f} | {S.mean(x['kills'] for x in R):.2f} | {alive:.0f} | {surv}/{len(R)} | {det} | {sq if mf[0] != {} else '-'} | {tb} |")
