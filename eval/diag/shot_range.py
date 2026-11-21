#!/usr/bin/env python3
"""Our gun shots in sim traces: range to the mech nearest our aim line and our own speed at the shot, vs whether a gun
hit on a mech by us lands within 1.2 s (bullet 252 m/s). python3 eval/diag/shot_range.py TRACE_DIR"""
import collections, glob, gzip, json, math, os, sys
rng = collections.defaultdict(lambda: [0, 0]); spd = collections.defaultdict(lambda: [0, 0]); laser_r = []
for fn in sorted(glob.glob(os.path.join(sys.argv[1], "*.gz"))):
    recs = [json.loads(l) for l in gzip.open(fn, "rt")]
    hdr = recs[0]; hz = hdr.get("tick_hz", 20)
    me = next((m["id"] for m in hdr["mechs"] if m["name"] in ("entrant", "bot")), 0)
    prev = None; pending = []
    for fr in recs:
        if "m" not in fr:
            continue
        t = fr["t"] / hz
        M = {m[0]: m for m in fr["m"]}
        mine = M.get(me)
        if mine is None or mine[6] <= 0:
            break
        v = math.hypot(mine[1] - prev[1], mine[2] - prev[2]) / ((fr["t"] - prev[0]) / hz) if prev and fr["t"] > prev[0] else 0.0
        prev = (fr["t"], mine[1], mine[2])
        for e in fr.get("ev") or []:
            if e.get("e") == "fire" and e.get("id") == me and e.get("w") == "gun":
                best = None
                for j, o in M.items():
                    if j == me or o[6] <= 0 or j >= 1000:
                        continue
                    d = math.hypot(o[1] - mine[1], o[2] - mine[2])
                    off = abs((math.atan2(o[2] - mine[2], o[1] - mine[1]) - mine[4] + math.pi) % (2 * math.pi) - math.pi)
                    if off < math.radians(8) and d < 240 and (best is None or d < best):
                        best = d
                if best is not None:
                    pending.append([t, best, v, False])
            elif e.get("e") == "hit" and e.get("src") == me and e.get("w") == "gun" and e.get("dst", 9999) < 1000:
                for p in pending:
                    if not p[3] and t - p[0] <= 1.2:
                        p[3] = True
                        break
            elif e.get("e") == "laser" and e.get("id") == me and e.get("hits"):
                laser_r.append(math.dist(e["from"][:2], e["to"][:2]))
    for t0, d, v, h in pending:
        b = rng[min(int(d // 30) * 30, 210)]; b[0] += 1; b[1] += h
        s = spd["standing (<2 m/s)" if v < 2 else ("slow (2-8)" if v < 8 else "strafe (8+)")]; s[0] += 1; s[1] += h
print("| our gun range (m) | shots | hit rate |\n| --- | --- | --- |")
tot = sum(b[0] for b in rng.values())
for k in sorted(rng):
    print(f"| {k}-{k + 30} | {rng[k][0]} ({rng[k][0] / tot:.0%}) | {rng[k][1] / max(1, rng[k][0]):.2f} |")
print("\n| our speed at the shot | shots | hit rate |\n| --- | --- | --- |")
for k, b in spd.items():
    print(f"| {k} | {b[0]} | {b[1] / max(1, b[0]):.2f} |")
if laser_r:
    laser_r.sort(); print(f"\nlaser hits on mechs: n={len(laser_r)} median range {laser_r[len(laser_r) // 2]:.0f} m")
