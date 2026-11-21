"""Do shooters lead? For each gun projectile: fit its line from the first two frames, find the mech whose path passes
closest to it, and compare the miss vs (a) the target's actual path (lead) and (b) the target frozen at fire time (no lead)."""
import json, sys, math, collections
def matches(path):
    hdr=None; frames=[]
    for l in open(path):
        try: d=json.loads(l)
        except Exception: continue
        if d.get('type')=='header':
            if hdr and frames: yield hdr, frames
            hdr=d; frames=[]
        elif 't' in d and 'm' in d and hdr is not None:
            frames.append(d)
    if hdr and frames: yield hdr, frames
res=collections.defaultdict(list)
for hdr, frames in matches(sys.argv[1]):
    bots=hdr.get('bots') or []; names={m['id']:m.get('name') for m in hdr.get('mechs',[])}
    by_t={}
    for f in frames: by_t[f['t']]=f
    ts=sorted(by_t)
    # projectile tracks
    ptr=collections.defaultdict(list)
    for t in ts:
        for p in by_t[t].get('p') or []:
            if p[1]==0: ptr[p[0]].append((t,p[2],p[3],p[4]))
    fires=[]
    for t in ts:
        for e in by_t[t].get('ev') or []:
            if e.get('e')=='fire' and e.get('w')=='gun': fires.append((e['t'],e['id']))
    for pid,tr in ptr.items():
        if len(tr)<3: continue
        (t0,x0,y0,z0),(t1,x1,y1,z1)=tr[0],tr[1]
        dt=(t1-t0)/20.0
        if dt<=0: continue
        vx,vy,vz=(x1-x0)/dt,(y1-y0)/dt,(z1-z0)/dt
        sp=math.sqrt(vx*vx+vy*vy+vz*vz)
        if sp<100: continue
        # shooter: nearest mech at t0 to the back-projected origin
        f0=by_t.get(t0); 
        if not f0: continue
        best=None
        for m in f0['m']:
            d=math.hypot(m[1]-x0,m[2]-y0)
            if best is None or d<best[0]: best=(d,m[0])
        if best[0]>40: continue
        sh=best[1]
        # candidate targets: mechs (not shooter); compute min distance of line to target actual pos and frozen pos over flight
        cands=[]
        for m in f0['m']:
            if m[0]==sh: continue
            tx,ty,tz=m[1],m[2],m[3]+4.5
            # time when projectile closest to frozen target
            rx,ry,rz=tx-x0,ty-y0,tz-z0
            s=(rx*vx+ry*vy+rz*vz)/(sp*sp)
            if s<0 or s*sp>240: continue
            px,py,pz=x0+vx*s,y0+vy*s,z0+vz*s
            frozen=math.sqrt((px-tx)**2+(py-ty)**2+(pz-tz)**2)
            # actual target position at time t0+s
            ta=t0+round(s*20)
            ta=min(by_t, key=lambda u: abs(u-ta)) if ta not in by_t else ta
            am=[q for q in by_t[ta]['m'] if q[0]==m[0]]
            if not am: continue
            ax,ay,az=am[0][1],am[0][2],am[0][3]+4.5
            sa=((ax-x0)*vx+(ay-y0)*vy+(az-z0)*vz)/(sp*sp)
            qx,qy,qz=x0+vx*sa,y0+vy*sa,z0+vz*sa
            actual=math.hypot(qx-ax,qy-ay)
            disp=math.hypot(ax-tx,ay-ty)
            frozen_h=math.hypot(px-tx,py-ty)
            cands.append((min(actual,frozen_h),actual,frozen_h,disp,s*sp,m[0]))
        if not cands: continue
        c=min(cands)
        if c[0]>6 or c[3]<2.0: continue   # unclear target, or target barely moved (no information)
        res[bots[sh] if sh<len(bots) else sh].append(c)
for k,v in sorted(res.items(), key=lambda kv: -len(kv[1])):
    lead=sum(1 for c in v if c[1]<c[2]); n=len(v)
    ma=sorted(c[1] for c in v)[n//2]; mf=sorted(c[2] for c in v)[n//2]
    print(f"{str(k):34s} n={n:4d} closer-to-actual={lead/n:.2f}  median miss vs actual {ma:5.2f} m  vs frozen {mf:5.2f} m  median disp {sorted(c[3] for c in v)[n//2]:.1f} m  range {sorted(c[4] for c in v)[n//2]:.0f}")
