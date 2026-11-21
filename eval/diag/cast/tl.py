"""Timeline of one mech in a cast capture: tl.py capture.jsonl name [seed]"""
import json, sys, math
path, name = sys.argv[1], sys.argv[2]; seed = int(sys.argv[3]) if len(sys.argv) > 3 else None
hdr = None; me = None
for l in open(path):
    try: d = json.loads(l)
    except Exception: continue
    if d.get('type') == 'header':
        hdr = d; ids = {m['id']: m.get('name') for m in d['mechs']}
        me = next((m['id'] for m in d['mechs'] if m.get('name') == name), None)
        if seed and d.get('seed') != seed: me = None
        if me is not None: print('=== seed', d.get('seed'), 'me', me)
        continue
    if me is None or 'm' not in d: continue
    t = d['t']; M = {m[0]: m for m in d['m']}
    ev = d.get('ev') or []
    for e in ev:
        if e.get('e') == 'hit' and (e.get('dst') == me or e.get('src') == me):
            print(f"   t={e['t']/20:6.2f} hit {ids.get(e['src'])} -> {ids.get(e.get('dst'), e.get('dst'))} {e.get('amt')} {e.get('w')} {'REAR' if e.get('rear') else ''}")
        elif e.get('e') not in ('fire', 'impact', 'hit') and (e.get('id') == me or e.get('by') == me):
            print(f"   t={e['t']/20:6.2f} {e}")
    if t % 10 == 0 and me in M:
        m = M[me]
        if m[6] <= 0: continue
        near = []
        for j, o in M.items():
            if j == me or o[6] <= 0: continue
            dd = math.hypot(o[1]-m[1], o[2]-m[2])
            if dd < 200:
                b = math.atan2(o[2]-m[2], o[1]-m[1]); rel = (b - m[4] + math.pi) % (2*math.pi) - math.pi
                face = (math.atan2(m[2]-o[2], m[1]-o[1]) - o[4] + math.pi) % (2*math.pi) - math.pi
                near.append(f"{ids.get(j)[:10]}@{dd:.0f}m rel{math.degrees(rel):+.0f} aimsAtMe{abs(math.degrees(face))<15}")
        print(f"t={t/20:6.1f} pos=({m[1]:.0f},{m[2]:.0f},{m[3]:.0f}) hp={m[6]} en={m[7]} fl={m[8]} slots={m[11]},{m[12]} | " + '; '.join(near))
