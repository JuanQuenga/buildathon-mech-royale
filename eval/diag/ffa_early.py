"""FFA: our deaths, time, attackers, our loadout at death, label mix in the last 10 s. python3 ffa_early.py TRACE_DIR"""
import gzip, json, os, sys, collections
for fn in sorted(os.listdir(sys.argv[1])):
    if not fn.endswith(".gz"): continue
    recs=[json.loads(l) for l in gzip.open(os.path.join(sys.argv[1],fn),'rt')]
    hdr=recs[0]; res=recs[-1]; hz=hdr["tick_hz"]
    names={m["id"]:m["name"] for m in hdr["mechs"]}
    R={m["id"]:m for m in res["mechs"]}
    mine=[i for i,n in names.items() if not n.startswith(("builtin","house","cmd")) and R[i].get("place")]
    for me in mine:
        dt=R[me]["death_t"]
        if dt is None: print(fn, me, "survived place", R[me]["place"]); continue
        att=collections.Counter(); labs=collections.Counter(); w=None; hp0=None
        for fr in recs:
            if "m" not in fr: continue
            t=fr["t"]/hz
            if t>dt: break
            for ev in fr.get("ev",[]):
                if ev["e"]=="hit" and ev["dst"]==me and t>dt-10: att[names.get(ev["src"],ev["src"])]+=ev["amt"]
            if t>dt-10:
                d=fr.get("dbg",{}).get(str(me))
                if d: labs[d.get("label","").split(" ")[0]]+=1
                for m in fr["m"]:
                    if m[0]==me: w=(m[11],m[12])
        print(f"{fn} me{me} death {dt:.0f} place {R[me]['place']} by {R[me]['killed_with']} w{w} att {dict((k,round(v)) for k,v in att.items())} modes {dict(labs)}")
