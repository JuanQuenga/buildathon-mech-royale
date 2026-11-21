#!/usr/bin/env python3
"""Conditional effect of the peek cycle (sim traces with MECH_DEBUG=1 labels): damage taken/dealt per second while the
peek cycle runs vs strafing engagements with a laser held, stratified by attackers (distinct mechs hitting us in 3 s).
    python3 eval/diag/peek_cond.py TRACE_DIR"""
import collections, glob, gzip, json, os, sys
cells = collections.defaultdict(lambda: [0.0, 0.0, 0.0])   # (cat, natt) -> [seconds, taken, dealt]
for fn in sorted(glob.glob(os.path.join(sys.argv[1], "*.gz"))):
    recs = [json.loads(l) for l in gzip.open(fn, "rt")]
    hdr = recs[0]
    wk = hdr.get("weapon_kinds") or []
    me = next((m["id"] for m in hdr["mechs"] if m["name"] in ("entrant", "bot")), 0)
    hz = hdr.get("tick_hz", 20); fe = hdr.get("frame_every", 2)
    recent = []
    for fr in recs:
        if "m" not in fr:
            continue
        t = fr["t"] / hz
        lab = ((fr.get("dbg") or {}).get(str(me)) or {}).get("label") or ""
        mine = next((m for m in fr["m"] if m[0] == me), None)
        if mine is None or mine[6] <= 0:
            continue
        slots = [wk[i] if 0 <= i < len(wk) else None for i in (mine[11], mine[12])]
        taken = dealt = 0.0
        for e in fr.get("ev") or []:
            if e.get("e") != "hit":
                continue
            if e.get("dst") == me:
                taken += e.get("amt", 0); recent.append((t, e.get("src")))
            elif e.get("src") == me and e.get("dst", 9999) < 1000:
                dealt += e.get("amt", 0)
        recent = [(a, s) for a, s in recent if t - a <= 3.0]
        natt = len({s for a, s in recent if s is not None})
        if "peek:" in lab:
            cat = "peek cycle"
        elif lab.startswith("engage") and "laser" in slots:
            cat = "strafe, laser held"
        else:
            continue
        c = cells[(cat, min(natt, 2))]
        c[0] += fe / hz; c[1] += taken; c[2] += dealt
print("| state | attackers (3 s) | seconds | taken/s | dealt/s |")
print("| --- | --- | --- | --- | --- |")
for (cat, n), (sec, tk, dl) in sorted(cells.items()):
    print(f"| {cat} | {'2+' if n == 2 else n} | {sec:.0f} | {tk / max(1e-9, sec):.1f} | {dl / max(1e-9, sec):.1f} |")
