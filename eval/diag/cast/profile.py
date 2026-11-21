"""Per-bot behaviour profile from real showdowns: first weapon, final laser share, ranges, dealt/taken per s, life,
speed/boost while firing, cubes."""
import json, sys, math, collections, statistics as S
seen=set(); P=collections.defaultdict(lambda: collections.defaultdict(list))
for f in sys.argv[1:]:
    hdr=None; pos={}; prev={}; lastfire={}
    for l in open(f):
        d=json.loads(l)
        if d.get('type')=='header':
            hdr=d; names={m['id']:m['name'] for m in d['mechs']}; show=all((b or '').startswith('docker') for b in d.get('bots',[])); dup=hdr['seed'] in seen; prev={}; lastfire={}
        elif hdr is None or not show or dup: continue
        elif d.get('type')=='result':
            seen.add(hdr['seed']); T=d['ticks']/20
            for m in d['mechs']:
                A=P[m['name']]; life=m['death_t'] or T
                A['place'].append(m['place']); A['life'].append(life); A['dealt'].append(m['damage_dealt']/life); A['taken'].append(m['damage_taken']/life)
                A['fw'].append(m['first_weapon_t'] if m['first_weapon_t'] is not None else 999); A['laser'].append(1 if 'laser' in (m['loadout'] or []) else 0)
                A['cubes'].append(m['cubes_max'])
        elif 'm' in d:
            t=d['t']
            for e in d.get('ev') or []:
                if e.get('e')=='fire': lastfire[e['id']]=e['t']
                if e.get('e')=='laser' and e.get('hits') and e['hits'][0]<1000: P[names.get(e['id'])]['lrange'].append(math.dist(e['from'][:2], e['to'][:2]))
                if e.get('e')=='hit' and e.get('w')=='gun' and e.get('dst',9999)<1000 and e['src'] in pos and e['dst'] in pos:
                    P[names.get(e['src'])]['grange'].append(math.dist(pos[e['src']][:2], pos[e['dst']][:2]))
                    P[names.get(e['dst'])]['hitby_range'].append(math.dist(pos[e['src']][:2], pos[e['dst']][:2]))
            for m in d['m']:
                i=m[0]; pos[i]=(m[1],m[2],m[3])
                if i in prev and t-prev[i][0]==2 and m[6]>0 and t-lastfire.get(i,-99)<=10:
                    sp=math.hypot(m[1]-prev[i][1], m[2]-prev[i][2])/0.1
                    if sp<40:
                        A=P[names.get(i)]; A['spd'].append(sp); fl=int(m[8]); A['boost'].append(1 if (fl&1 and fl&2) else 0); A['air'].append(0 if fl&1 else 1)
                prev[i]=(t,m[1],m[2])
med=lambda v: S.median(v) if v else float('nan')
rows=[]
for n,A in P.items():
    if len(A['place'])<5: continue
    rows.append((S.mean(A['place']), n, A))
print(f"| bot | n | place | first weapon med s | laser at end | laser hit range med | gun hit range med | hit-by range med | dealt/s | taken/s | life s | speed firing | boost | air | cubes |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for mp,n,A in sorted(rows, key=lambda r: r[0]):
    print(f"| {n} | {len(A['place'])} | {mp:.1f} | {med(A['fw']):.1f} | {S.mean(A['laser']):.2f} | {med(A['lrange']):.0f} | {med(A['grange']):.0f} | {med(A['hitby_range']):.0f} | {S.mean(A['dealt']):.1f} | {S.mean(A['taken']):.1f} | {S.mean(A['life']):.0f} | {med(A['spd']):.1f} | {S.mean(A['boost']) if A['boost'] else 0:.2f} | {S.mean(A['air']) if A['air'] else 0:.2f} | {S.mean(A['cubes']):.1f} |")
