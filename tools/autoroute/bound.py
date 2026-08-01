import sys,os,resource; resource.setrlimit(resource.RLIMIT_AS,(1900*1024*1024,)*2)
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import arlib, ripup, numpy as np, math
from scipy import ndimage
from collections import Counter
ST=np.ones((3,3),bool)

def reach_set(t,v,seed):
    """full multi-layer reachable set from seed masks"""
    L=arlib.L
    labs={}; uf=arlib.UF()
    for l in L: labs[l],_=ndimage.label(t[l],structure=ST)
    ys,xs=np.nonzero(v)
    for l in L[1:]:
        a=labs[L[0]][ys,xs]; b=labs[l][ys,xs]
        for i in range(len(a)):
            if a[i]>0 and b[i]>0: uf.union((L[0],int(a[i])),(l,int(b[i])))
    roots=set()
    for l in L:
        for i in np.unique(labs[l][seed[l]]):
            if i>0: roots.add(uf.find((l,int(i))))
    out={}
    for l in L:
        ids=[i for i in range(1,int(labs[l].max())+1) if uf.find((l,i)) in roots]
        out[l]=np.isin(labs[l],ids) if ids else np.zeros_like(t[l])
    return out

def bounding_nets(B,E,R,net,topn=12):
    """which nets' copper forms the boundary of reachable set R"""
    hits=Counter()
    for lay in ('F.Cu','B.Cu'):
        edge=ndimage.binary_dilation(R[lay],structure=ST,iterations=3)&~R[lay]
        ys,xs=np.nonzero(edge)
        if len(ys)==0: continue
        step=max(1,len(ys)//600)
        for k in range(0,len(ys),step):
            x,y=E.gr.to_xy(int(xs[k]),int(ys[k]))
            best=None; bd=1e9
            for s in B['segs']:
                if s['layer']!=lay or s['net']==net: continue
                dx,dy=s['x2']-s['x1'],s['y2']-s['y1']; L2=dx*dx+dy*dy
                tt=0 if L2<1e-12 else max(0,min(1,((x-s['x1'])*dx+(y-s['y1'])*dy)/L2))
                d=math.hypot(s['x1']+tt*dx-x,s['y1']+tt*dy-y)-s['w']/2
                if d<bd: bd=d; best=('SEG',s['net'],lay)
            for vv in B['vias']:
                if vv['net']==net: continue
                d=math.hypot(vv['x']-x,vv['y']-y)-vv['size']/2
                if d<bd: bd=d; best=('VIA',vv['net'],'both')
            for p in B['pads']:
                if p['net']==net or p['type']=='np_thru_hole' or lay not in arlib.pad_layers(p): continue
                d=math.hypot(p['x']-x,p['y']-y)-max(p['w'],p['h'])/2
                if d<bd: bd=d; best=('PAD',p['net'] or p['ref'],lay)
            if best and bd<0.45: hits[best]+=1
    return hits

if __name__=='__main__':
    net=sys.argv[1]
    B=arlib.load_board(); ripup.apply(B); E=arlib.Env(B)
    m,t,v,f=arlib.build_env(E,net,res=0.10)
    isl=arlib.island_masks(E,net,t,res=0.10); A,Bm=isl
    if A['F.Cu'].sum()+A['B.Cu'].sum()>Bm['F.Cu'].sum()+Bm['B.Cu'].sum(): A,Bm=Bm,A
    for nmm,seed in (('U7-side',A),('target-side',Bm)):
        R=reach_set(t,v,seed)
        tot=int(R['F.Cu'].sum()+R['B.Cu'].sum())
        ys,xs=np.nonzero(R['F.Cu']|R['B.Cu'])
        print('%s reachable set: %d cells  bbox x %.1f..%.1f y %.1f..%.1f'%(nmm,tot,
            E.gr.to_xy(xs.min(),0)[0],E.gr.to_xy(xs.max(),0)[0],E.gr.to_xy(0,ys.min())[1],E.gr.to_xy(0,ys.max())[1]))
        h=bounding_nets(B,E,R,net)
        print('   bounded by:',h.most_common(8))
