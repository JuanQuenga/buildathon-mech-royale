"""What happened in the 30 s before each death: mode sequence, HP, kills, hunters, cube looting. python3 prelude.py DIR"""
import gzip,json,os,sys,collections,math
for fn in sorted(os.listdir(sys.argv[1]), key=lambda f:int(f.split('seed')[1].split('.')[0])):
    recs=[json.loads(l) for l in gzip.open(os.path.join(sys.argv[1],fn),'rt')]
    h=recs[0]; res=recs[-1]; hz=h['tick_hz']; names={m['id']:m['name'].split(':')[-1][:2] for m in h['mechs']}
    me=[i for i,m in enumerate(h['mechs']) if not m['name'].startswith('house')][0]
    R={m['id']:m for m in res['mechs']}; dt=R[me]['death_t']
    if dt is None: continue
    seq=[]; last=None; kills=[]; hp=None
    for fr in recs:
        if 'm' not in fr: continue
        t=fr['t']/hz
        for ev in fr.get('ev',[]):
            if ev['e']=='death' and ev.get('by')==me and ev['id'] in names: kills.append(round(t))
        if t<dt-30: continue
        lab=fr.get('dbg',{}).get(str(me),{}).get('label','?')
        M={m[0]:m for m in fr['m']}
        if me not in M: break
        mode=lab.split(' ')[0]+(' '+lab.split(' ')[1] if lab.split(' ')[0] in ('loot','retreat','engage') else '')
        if mode!=last:
            seq.append(f"{t-dt:+.0f}:{mode}@{M[me][6]}"); last=mode
    print(f"s{h['seed']} pts {16-R[me]['place']} death {dt:.0f} kills {kills} | "+" ".join(seq[-14:]))
