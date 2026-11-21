"""Per bot, while it fired in the last 0.5 s: horizontal speed, grounded-boost share, airborne share, lateral reversal rate."""
import json, sys, math, collections
sys.path.insert(0, __file__.rsplit('/',1)[0])
from lead import matches
agg=collections.defaultdict(lambda: collections.defaultdict(list))
for path in sys.argv[1:]:
  for hdr, frames in matches(path):
    names={m['id']:m.get('name') for m in hdr.get('mechs',[])}
    bots=hdr.get('bots') or []
    lastfire={}
    prev={}
    vprev={}
    for f in frames:
        t=f['t']
        for e in f.get('ev') or []:
            if e.get('e')=='fire': lastfire[e['id']]=e['t']
        for m in f['m']:
            i=m[0]
            if m[6]<=0: continue
            if i in prev and t-prev[i][0]==2:
                vx=(m[1]-prev[i][1])/0.1; vy=(m[2]-prev[i][2])/0.1
                sp=math.hypot(vx,vy)
                key=names.get(i) or str(i)
                if bots and i<len(bots) and bots[i].startswith('house'): key=bots[i]
                if t-lastfire.get(i,-99)<=10 and sp<40:
                    A=agg[key]
                    A['sp'].append(sp); fl=int(m[8])
                    A['air'].append(0 if fl&1 else 1); A['gboost'].append(1 if (fl&1 and fl&2) else 0)
                    A['charge'].append(1 if fl&4 else 0)
                    if i in vprev and sp>3 and vprev[i][2]>3:
                        dot=(vx*vprev[i][0]+vy*vprev[i][1])/(sp*vprev[i][2])
                        A['rev'].append(1 if dot<-0.3 else 0)
                vprev[i]=(vx,vy,sp)
            prev[i]=(t,m[1],m[2])
rows=[]
for k,A in agg.items():
    n=len(A['sp'])
    if n<100: continue
    sp=sorted(A['sp'])
    rv=sum(A['rev'])/max(1,len(A['rev']))*10   # reversals per second (0.1 s frames)
    rows.append((k,n,sp[n//2],sum(1 for s in sp if s>14)/n,sum(A['gboost'])/n,sum(A['air'])/n,sum(A['charge'])/n,rv))
for r in sorted(rows,key=lambda r:-r[1]):
    print(f"{r[0][:28]:28s} n={r[1]:5d} med_speed={r[2]:5.1f} fast(>14)={r[3]:.2f} gboost={r[4]:.2f} air={r[5]:.2f} charging={r[6]:.2f} rev/s={r[7]:.2f}")
