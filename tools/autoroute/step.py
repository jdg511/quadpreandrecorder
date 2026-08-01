import sys, os, pickle, math, json, time
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import resource
resource.setrlimit(resource.RLIMIT_AS,(1900*1024*1024,1900*1024*1024))
import arlib, ripup
STATE='/tmp/ar_state.pkl'
net=sys.argv[1]; wt=float(sys.argv[2]); vc=float(sys.argv[3]); mp=int(sys.argv[4])
B=arlib.load_board(); ripup.apply(B)
st={'added':{}} if not os.path.exists(STATE) else pickle.load(open(STATE,'rb'))
for n,rec in st['added'].items():
    B['segs'].extend(rec['segs'])
    for (x,y,nn) in rec['vias']: B['vias'].append(dict(x=x,y=y,size=arlib.VIA_D,drill=arlib.VIA_DR,net=nn))
E=arlib.Env(B); t=time.time()
import validate as VAL
# U7's west pin escape is a ~1mm corridor that fits two parallel tracks.
# Routing greedily puts the first net down the middle and strands the second,
# so +3V3_A (pad 8) is pushed to the outer lane, leaving the inner lane for
# ADC_LDO (pad 11).
AVOID={
  # U7 pin 8 (+3V3_A) runs north-south past pin 11 (ADC_LDO), which must escape
  # west -- the two traces have to cross. Block +3V3_A from F.Cu across ADC_LDO's
  # escape line so it dives to In2.Cu and crosses underneath instead.
  # (avoid regions cleared)
}
AV=AVOID.get(net,())
LADDER=((0.10,0.00,30.0),(0.10,0.03,30.0),(0.05,0.00,18.0),(0.05,0.03,18.0),(0.10,0.07,34.0))
best=None; lastbad=None
for res,extra,marg in LADDER:
    m,trkok,viaok,fineD=arlib.build_env(E,net,res=res,extra=extra,avoid=AV)
    isl=arlib.island_masks(E,net,trkok,res=res)
    if len(isl)!=2: print('SKIP %s islands=%d'%(net,len(isl))); sys.exit(3)
    A,Bm=isl
    if A['F.Cu'].sum()+A['B.Cu'].sum()>Bm['F.Cu'].sum()+Bm['B.Cu'].sum(): A,Bm=Bm,A
    if not arlib.reachable(trkok,viaok,A,Bm): continue
    try:
        pts=arlib.astar(E,trkok,viaok,A,Bm,via_cost=vc,wt=wt,maxpush=mp,margin_mm=marg)
    except MemoryError:
        pts=None
    if pts is None: continue
    segs,vias=arlib.to_geom(E,net,pts,fineD,m,extra=extra,avoid=AV)
    bad=VAL.check(B,segs,vias,verbose=False)
    if not bad: best=(segs,vias,res,extra); break
    lastbad=bad
if best is None:
    if lastbad: print('REJECT %-12s worst=%.3f  %s'%(net,min(b[3] for b in lastbad),lastbad[0][:3]))
    else: print('FAIL %-14s'%net)
    sys.exit(1)
segs,vias,used,extra=best
Ln=sum(math.hypot(s['x2']-s['x1'],s['y2']-s['y1']) for s in segs)
st['added'][net]=dict(segs=segs,vias=vias,length=Ln)
pickle.dump(st,open(STATE,'wb'))
print('OK   %-14s len=%6.1fmm vias=%2d segs=%3d res=%.2f x=%.2f (%.0fs)'%(net,Ln,len(vias),len(segs),used,extra,time.time()-t))
