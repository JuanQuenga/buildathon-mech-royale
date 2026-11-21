"""Real showdowns: per bot, laser and gun hit distances, and mean place."""
import json, sys, math, collections, statistics as S
seen=set(); lz=collections.defaultdict(list); gz=collections.defaultdict(list); place=collections.defaultdict(list)
for f in sys.argv[1:]:
    hdr=None; pos={}
    for l in open(f):
        d=json.loads(l)
        if d.get('type')=='header':
            hdr=d; names={m['id']:m['name'] for m in d['mechs']}; show=all((b or '').startswith('docker') for b in d.get('bots',[])); dup=hdr['seed'] in seen
        elif hdr is None or not show or dup: continue
        elif d.get('type')=='result':
            seen.add(hdr['seed'])
            for m in d['mechs']: place[m['name']].append(m['place'])
        elif 'm' in d:
            for m in d['m']: pos[m[0]]=(m[1],m[2],m[3])
            for e in d.get('ev') or []:
                if e.get('e')=='laser' and e.get('hits'):
                    tgt=e['hits'][0]
                    if tgt<1000: lz[names.get(e['id'])].append(math.dist(e['from'][:2], e['to'][:2]))
                elif e.get('e')=='hit' and e.get('w')=='gun' and e.get('dst',9999)<1000 and e['src'] in pos and e['dst'] in pos:
                    gz[names.get(e['src'])].append(math.dist(pos[e['src']][:2], pos[e['dst']][:2]))
rows=[(S.mean(place[n]), n) for n in place if len(place[n])>=3]
print('bot                mean_place n  laser_hits med_dist  gun_hits med_dist')
for mp,n in sorted(rows):
    L=lz.get(n,[]); G=gz.get(n,[])
    print(f"{n[:18]:18s} {mp:5.1f} {len(place[n]):3d}   {len(L):4d} {S.median(L) if L else 0:6.0f}     {len(G):5d} {S.median(G) if G else 0:6.0f}")
