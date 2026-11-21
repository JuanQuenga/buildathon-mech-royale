#!/usr/bin/env python3
"""Print what a tracked mech was doing while outside the zone, from a sim trace (mechreplay/1 JSONL.gz).

    python3 eval/zone_trace.py trace.jsonl.gz [mech_id]     (default: the mech named bot/entrant)

For every second spent outside the circle: position, distance outside the edge, hp, energy, grounded/boosting,
and how far it moved since the previous second (stuck = ~0 m/s).
"""
import gzip
import json
import math
import sys


def main():
    path = sys.argv[1]
    want = int(sys.argv[2]) if len(sys.argv) > 2 else None
    with gzip.open(path, "rt") as f:
        lines = [json.loads(l) for l in f if l.strip()]
    hdr = lines[0]
    if want is None:
        for m in hdr["mechs"]:
            if m["name"] in ("bot", "entrant"):
                want = m["id"]
                break
    frames = [l for l in lines[1:] if "m" in l]
    last_print = -1e9
    prev = None
    out_s = 0.0
    dt = None
    for fr in frames:
        t = fr["t"]
        me = next((m for m in fr["m"] if m[0] == want), None)
        z = fr.get("z")
        if me is None or z is None:
            continue
        x, y, zz, hp, en, flags = me[1], me[2], me[3], me[6], me[7], me[8]
        cx, cy, r = z[0], z[1], z[2]
        d = math.hypot(x - cx, y - cy) - r
        if prev is not None:
            dt = t - prev[0]
        if d > 0 and dt:
            out_s += dt
        if d > 0 and t - last_print >= 1.0:
            mv = math.hypot(x - prev[1], y - prev[2]) / max(1e-6, t - prev[0]) if prev else 0.0
            print(f"t={t:6.1f} pos=({x:7.1f},{y:7.1f},{zz:5.1f}) outside_by={d:6.1f} m zone=({cx:.0f},{cy:.0f}) r={r:.0f} "
                  f"hp={hp:5.0f} en={en:4.0f} {'G' if flags & 1 else 'air'}{' B' if flags & 2 else ''} speed={mv:4.1f}")
            last_print = t
        prev = (t, x, y)
    print(f"total outside: {out_s:.1f} s")


if __name__ == "__main__":
    main()
