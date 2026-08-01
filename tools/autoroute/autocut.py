import sys,os,resource; resource.setrlimit(resource.RLIMIT_AS,(1900*1024*1024,)*2)
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import arlib, ripup, numpy as np, math, bound
from scipy import ndimage
ST=np.ones((3,3),bool)
PROTECT={'GND'}   # cutting a GND trace is usually free (pours) but keep it last-resort

import pickle
def analyse(cuts,net):
    B=arlib.load_board(); ripup.apply(B)
    if os.path.exists('/tmp/ar_state.pkl') and os.environ.get('USE_STATE'):
        st=pickle.load(open('/tmp/ar_state.pkl','rb'))
        for n,rec in st['added'].items():
            if n==net: continue
            B['segs'].extend(rec['segs'])
            for (x,y,nn) in rec['vias']: B['vias'].append(dict(x=x,y=y,size=arlib.VIA_D,drill=arlib.VIA_DR,net=nn))
    if cuts: B['segs']=[s for s in B['segs'] if not any(ripup.match(s,r) for r in cuts)]
    E=arlib.Env(B)
    m,t,v,f=arlib.build_env(E,net,res=0.10)
    isl=arlib.island_masks(E,net,t,res=0.10)
    if len(isl)!=2: return None,None,None,None,B,E
    A,Bm=isl
    if A['F.Cu'].sum()+A['B.Cu'].sum()>Bm['F.Cu'].sum()+Bm['B.Cu'].sum(): A,Bm=Bm,A
    ok=arlib.reachable(t,v,A,Bm)
    return ok,A,Bm,(m,t,v,f),B,E

def thinnest(B,E,t,v,A,Bm):
    RU=bound.reach_set(t,v,A); RC=bound.reach_set(t,v,Bm)
    best=None
    for lay in ('F.Cu','B.Cu'):
        if RC[lay].sum()==0 or RU[lay].sum()==0: continue
        d=ndimage.distance_transform_edt(~RU[lay])*0.10
        dd=np.where(RC[lay],d,1e9)
        iy,ix=np.unravel_index(np.argmin(dd),dd.shape)
        if best is None or dd[iy,ix]<best[0]:
            best=(float(dd[iy,ix]),lay,E.gr.to_xy(int(ix),int(iy)))
    return best

def culprit(B,lay,x0,y0,net):
    cand=[]
    for s in B['segs']:
        if s['layer']!=lay or s['net']==net: continue
        dx,dy=s['x2']-s['x1'],s['y2']-s['y1']; L2=dx*dx+dy*dy
        tt=0 if L2<1e-12 else max(0,min(1,((x0-s['x1'])*dx+(y0-s['y1'])*dy)/L2))
        d=math.hypot(s['x1']+tt*dx-x0,s['y1']+tt*dy-y0)-s['w']/2
        cand.append((d,s))
    cand.sort(key=lambda z:z[0])
    for d,s in cand[:6]:
        if s['net'] not in PROTECT: return d,s
    return cand[0] if cand else (None,None)

if __name__=='__main__':
    net=sys.argv[1]; budget=int(sys.argv[2]) if len(sys.argv)>2 else 4
    cuts=[]
    for it in range(budget+1):
        ok,A,Bm,env,B,E = analyse(cuts,net)
        if ok is None: print('islands != 2, abort'); break
        print('iter %d: cuts=%d  reachable=%s'%(it,len(cuts),ok))
        if ok:
            print('SOLVED with cuts:')
            for c in cuts: print('   ',c)
            break
        if it==budget: print('budget exhausted'); break
        m,t,v,f=env
        w=thinnest(B,E,t,v,A,Bm)
        if not w: print('no wall found'); break
        gap,lay,(x0,y0)=w
        d,s=culprit(B,lay,x0,y0,net)
        if s is None: print('no culprit'); break
        print('   wall %.2fmm on %s at (%.2f,%.2f) -> cut %s %s (%.3f,%.3f)->(%.3f,%.3f) len=%.2f'%(
            gap,lay,x0,y0,s['net'],s['layer'],s['x1'],s['y1'],s['x2'],s['y2'],
            math.hypot(s['x2']-s['x1'],s['y2']-s['y1'])))
        cuts.append((s['net'],s['layer'],(s['x1'],s['y1']),(s['x2'],s['y2'])))
