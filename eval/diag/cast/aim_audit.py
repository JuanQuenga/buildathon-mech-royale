#!/usr/bin/env python3
"""Aim audit on real cast captures. For every gun shot of the named bot (or all bots): reconstruct the bullet from the
shooter's recorded torso aim at the fire tick (frames every 2 ticks, linear interpolation), fly it at 252 m/s from the
muzzle (feet + 7 m x size, 3 m out along the aim) against every mech's recorded track, and record the closest approach
to the intended target (the mech nearest the aim line at fire time). Outcome = a real gun 'hit' event by this shooter on
that target within the flight window. Miss vector at closest approach is split into: along the target's horizontal
velocity (+ = shot passed AHEAD of it, - = behind), vertical (+ = high), and the remaining horizontal lateral part.
    python3 aim_audit.py NAME capture.jsonl [...]      (NAME = poteto, or ALL)"""
import json, math, sys, collections, statistics as S
NAME = sys.argv[1]; files = sys.argv[2:]
SPEED, MUZ, OFF, R0, H0 = 252.0, 7.0, 3.0, 2.5, 9.0
rows = []; seen = set()
for f in files:
    hdr = None; frames = []
    def flush():
        if hdr is None or not frames or hdr['seed'] in seen: return
        seen.add(hdr['seed']); analyse(hdr, frames)
    def analyse(hdr, frames):
        names = {m['id']: m.get('name') for m in hdr['mechs']}
        show = all((b or '').startswith('docker') for b in hdr.get('bots', []))
        if not show: return
        T = [fr['t'] for fr in frames]
        byt = {fr['t']: fr for fr in frames}
        def state(i, t):            # interpolated mech row fields at tick t
            k = max(0, min(len(T) - 2, next((j for j in range(len(T) - 1) if T[j] <= t <= T[j + 1]), len(T) - 2)))
            a, b = byt[T[k]], byt[T[k + 1]]
            ma = next((m for m in a['m'] if m[0] == i), None); mb = next((m for m in b['m'] if m[0] == i), None)
            if ma is None or mb is None: return None
            w = 0.0 if T[k + 1] == T[k] else (t - T[k]) / (T[k + 1] - T[k]); w = max(0.0, min(1.0, w))
            def lerp(x, y): return x + (y - x) * w
            dyaw = (mb[4] - ma[4] + math.pi) % (2 * math.pi) - math.pi
            return dict(x=lerp(ma[1], mb[1]), y=lerp(ma[2], mb[2]), z=lerp(ma[3], mb[3]), yaw=ma[4] + dyaw * w,
                        pitch=lerp(ma[5], mb[5]), hp=ma[6], cubes=ma[9], flags=int(ma[8]))
        def vel(i, t, dt=2):
            a, b = state(i, t - dt), state(i, t + dt)
            if a is None or b is None: return (0.0, 0.0, 0.0)
            s = (2 * dt) / 20.0
            return ((b['x'] - a['x']) / s, (b['y'] - a['y']) / s, (b['z'] - a['z']) / s)
        hits = collections.defaultdict(list)
        fires = []
        for fr in frames:
            for e in fr.get('ev') or []:
                if e.get('e') == 'hit' and e.get('w') == 'gun' and e.get('dst', 9999) < 1000: hits[(e['src'], e['dst'])].append(e['t'])
                if e.get('e') == 'fire' and e.get('w') == 'gun': fires.append((e['t'], e['id']))
        ids = [m['id'] for m in hdr['mechs']]
        for t0, sid in fires:
            if NAME != 'ALL' and names.get(sid) != NAME: continue
            me = state(sid, t0)
            if me is None or me['hp'] <= 0: continue
            sc = 1 + 0.05 * (me['cubes'] or 0)
            dx, dy, dz = math.cos(me['pitch']) * math.cos(me['yaw']), math.cos(me['pitch']) * math.sin(me['yaw']), math.sin(me['pitch'])
            ox, oy, oz = me['x'] + OFF * dx, me['y'] + OFF * dy, me['z'] + MUZ * sc + OFF * dz
            best = None
            for j in ids:
                if j == sid: continue
                tg = state(j, t0)
                if tg is None or tg['hp'] <= 0: continue
                rx, ry = tg['x'] - me['x'], tg['y'] - me['y']; d = math.hypot(rx, ry)
                if d < 5 or d > 235: continue
                off = abs((math.atan2(ry, rx) - me['yaw'] + math.pi) % (2 * math.pi) - math.pi)
                if off < math.radians(8) and (best is None or off < best[0]): best = (off, j, d)
            if best is None: continue
            _, j, d0 = best
            # fly the bullet: closest approach over the flight, in 1-tick steps (refined linearly)
            bestm = None
            for k in range(0, 21):
                tt = t0 + k
                tg = state(j, tt)
                if tg is None: break
                tau = k / 20.0
                bx, by, bz = ox + dx * SPEED * tau, oy + dy * SPEED * tau, oz + dz * SPEED * tau
                tsc = 1 + 0.05 * (tg['cubes'] or 0)
                cz = tg['z'] + 0.5 * H0 * tsc
                h = math.hypot(bx - tg['x'], by - tg['y'])
                if bestm is None or h < bestm[0]: bestm = (h, k, bx - tg['x'], by - tg['y'], bz - cz, tg, tsc)
            if bestm is None: continue
            h, k, mx, my, mz, tg, tsc = bestm
            hit = any(t0 <= ht <= t0 + 22 for ht in hits.get((sid, j), []))
            v = vel(j, t0 + k); vh = math.hypot(v[0], v[1])
            along = (mx * v[0] + my * v[1]) / vh if vh > 1 else 0.0
            lat = math.sqrt(max(0.0, mx * mx + my * my - along * along)) if vh > 1 else math.hypot(mx, my)
            mv = vel(sid, t0); myspd = math.hypot(mv[0], mv[1])
            a1, a2 = vel(j, t0 - 4), vel(j, t0)
            turned = (a1[0] * a2[0] + a1[1] * a2[1]) < 0 and math.hypot(*a1[:2]) > 3 and math.hypot(*a2[:2]) > 3
            # crossing speed: target velocity perpendicular to our line of sight
            lx, ly = (tg['x'] - me['x']) / max(1e-6, d0), (tg['y'] - me['y']) / max(1e-6, d0)
            cross = abs(-ly * v[0] + lx * v[1])
            air = not (tg['flags'] & 1)
            rows.append(dict(shooter=names.get(sid), d=d0, hit=hit, geo_hit=(h <= R0 * tsc + 0.6 and abs(mz) <= 0.5 * H0 * tsc + 0.6),
                             along=along, lat=lat, vert=mz, horiz=h, vh=vh, cross=cross, myspd=myspd, turned=turned, air=air))
    for l in open(f):
        try: d = json.loads(l)
        except Exception: continue
        if d.get('type') == 'header':
            flush(); hdr = d; frames = []
        elif 'm' in d and hdr is not None:
            frames.append(d)
    flush()

def rate(R): return f"{sum(r['hit'] for r in R) / max(1, len(R)):.2f} (n={len(R)})"
print(f"shots attributed to a mech target: {len(rows)}   hit rate {rate(rows)}")
agree = sum(1 for r in rows if r['hit'] == r['geo_hit']) / max(1, len(rows))
print(f"reconstruction agrees with the real outcome on {agree:.0%} of shots (geo-hit rate {sum(r['geo_hit'] for r in rows)/max(1,len(rows)):.2f})")
def bucket(title, key, edges):
    print(f"\n| {title} | hit rate |\n| --- | --- |")
    for lo, hi in zip(edges, edges[1:]):
        R = [r for r in rows if lo <= key(r) < hi]
        if R: print(f"| {lo}-{hi} | {rate(R)} |")
bucket("range m", lambda r: r['d'], [0, 30, 60, 90, 120, 150, 180, 240])
bucket("target crossing speed m/s", lambda r: r['cross'], [0, 2, 5, 8, 11, 15, 40])
bucket("our speed m/s", lambda r: r['myspd'], [0, 2, 6, 10, 13, 40])
print(f"\n| target state | hit rate |\n| --- | --- |\n| airborne | {rate([r for r in rows if r['air']])} |\n| grounded | {rate([r for r in rows if not r['air']])} |\n| reversed in last 0.2 s | {rate([r for r in rows if r['turned']])} |")
M = [r for r in rows if not r['hit'] and r['vh'] > 3]
if M:
    print(f"\nmisses on moving targets (n={len(M)}): along-velocity error median {S.median(r['along'] for r in M):+.2f} m "
          f"(share behind {sum(r['along'] < 0 for r in M)/len(M):.0%}), |lateral| median {S.median(r['lat'] for r in M):.2f} m, "
          f"vertical median {S.median(r['vert'] for r in M):+.2f} m (share high {sum(r['vert'] > 0 for r in M)/len(M):.0%})")
    # latency fit: along error / target speed = time error
    te = [r['along'] / r['vh'] for r in M if r['vh'] > 5]
    if te: print(f"along error / target speed (time-equivalent lead error): median {S.median(te):+.3f} s  (negative = we lag behind)")
H = [r for r in rows if r['hit'] and r['vh'] > 3]
if H: print(f"hits on moving targets (n={len(H)}): along median {S.median(r['along'] for r in H):+.2f} m, vertical median {S.median(r['vert'] for r in H):+.2f} m")
