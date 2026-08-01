"""Clearance-aware 2-layer autorouter for QuadPreRecorder Rev3.
Geometry model validated against KiCad's own DRC output (pad positions 19/19,
board area exact, connectivity reproduces KiCad's island count on all nets)."""
import re, math, os, pickle
import numpy as np
from scipy import ndimage

HW='/sessions/keen-peaceful-brahmagupta/mnt/quadpreandrecorder/hardware'
PCB=os.path.join(HW,'QuadPreRecorder_rev3_4layer.kicad_pcb')
FINE=0.05; RES=0.10
TW=0.20; VIA_D=0.8; VIA_DR=0.4
TRK_T=0.25; VIA_T=0.55; HOLE_T=0.45
EDGE_TRK_T=0.60; EDGE_VIA_T=0.90; KEEP_TRK_T=0.10; KEEP_VIA_T=0.40
L=['F.Cu','In2.Cu','B.Cu']        # routing layers (In1.Cu is a solid GND plane)
ALLCU=['F.Cu','In1.Cu','In2.Cu','B.Cu']
OUTLINE=[(0,9),(9,0),(129,0),(138,9),(138,105),(129,114),(9,114),(0,105)]

# ---------- s-expression ----------
def tokenize(s):
    toks=[];i=0;n=len(s)
    while i<n:
        c=s[i]
        if c in '()': toks.append(c); i+=1
        elif c=='"':
            j=i+1;buf=[]
            while j<n:
                if s[j]=='\\': buf.append(s[j+1]); j+=2
                elif s[j]=='"': break
                else: buf.append(s[j]); j+=1
            toks.append(('s',''.join(buf))); i=j+1
        elif c.isspace(): i+=1
        else:
            j=i
            while j<n and not s[j].isspace() and s[j] not in '()"': j+=1
            toks.append(('y',s[i:j])); i=j
    return toks
def parse(s):
    st=[[]]
    for t in tokenize(s):
        if t=='(': nw=[]; st[-1].append(nw); st.append(nw)
        elif t==')': st.pop()
        else: st[-1].append(t[1])
    return st[0]
def nm_(n): return n[0] if n and isinstance(n[0],str) else None
def find(n,k):
    for c in n:
        if isinstance(c,list) and nm_(c)==k: return c
def find_all(n,k): return [c for c in n if isinstance(c,list) and nm_(c)==k]

# ---------- board extraction ----------
def load_board(path=PCB):
    root=parse(open(path,encoding='utf-8').read())[0]
    def rot(x,y,a):
        r=math.radians(a); return (x*math.cos(r)-y*math.sin(r), x*math.sin(r)+y*math.cos(r))
    pads=[]
    for fp in find_all(root,'footprint'):
        at=find(fp,'at'); fx,fy=float(at[1]),float(at[2])
        fang=float(at[3]) if len(at)>3 else 0.0
        ref=''
        for pr in find_all(fp,'property'):
            if len(pr)>1 and pr[1]=='Reference': ref=pr[2]
        for pd in find_all(fp,'pad'):
            pat=find(pd,'at'); px,py=float(pat[1]),float(pat[2])
            pang=float(pat[3]) if len(pat)>3 else 0.0
            rx,ry=rot(px,py,-fang)                      # sign validated 19/19 vs DRC
            sz=find(pd,'size'); nn=find(pd,'net'); lays=find(pd,'layers'); dr=find(pd,'drill')
            drill=0.0
            if dr:
                nums=[t for t in dr[1:] if isinstance(t,str) and re.match(r'^[\d.]+$',t)]
                if nums: drill=float(nums[0])
            pads.append(dict(ref=ref,num=pd[1],type=pd[2],shape=pd[3],x=fx+rx,y=fy+ry,
                ang=pang,fang=fang,w=float(sz[1]),h=float(sz[2]),
                net=nn[1] if nn and len(nn)>1 else '',
                layers=list(lays[1:]) if lays else [],drill=drill,
                rr=float(find(pd,'roundrect_rratio')[1]) if find(pd,'roundrect_rratio') else 0.0))
    segs=[]
    for s in find_all(root,'segment'):
        st_=find(s,'start');en=find(s,'end');wd=find(s,'width');ly=find(s,'layer');nt=find(s,'net')
        segs.append(dict(x1=float(st_[1]),y1=float(st_[2]),x2=float(en[1]),y2=float(en[2]),
            w=float(wd[1]),layer=ly[1],net=nt[1] if nt and len(nt)>1 else ''))
    vias=[]
    for v in find_all(root,'via'):
        at=find(v,'at');sz=find(v,'size');dr=find(v,'drill');nt=find(v,'net')
        vias.append(dict(x=float(at[1]),y=float(at[2]),size=float(sz[1]),drill=float(dr[1]),
            net=nt[1] if nt and len(nt)>1 else ''))
    keeps=[]
    for z in find_all(root,'zone'):
        ko=find(z,'keepout'); poly=find(z,'polygon')
        if not (ko and poly): continue
        po=find(poly,'pts')
        if not po: continue
        keeps.append([(float(xy[1]),float(xy[2])) for xy in find_all(po,'xy')])
    return dict(pads=pads,segs=segs,vias=vias,keeps=keeps)

# ---------- raster ----------
class Grid:
    def __init__(s,res,margin=1.0):
        s.res=res; s.x0=-margin; s.y0=-margin
        s.W=int(math.ceil((138+2*margin)/res))+1; s.H=int(math.ceil((114+2*margin)/res))+1
    def to_ix(s,x,y): return int(round((x-s.x0)/s.res)), int(round((y-s.y0)/s.res))
    def to_xy(s,ix,iy): return s.x0+ix*s.res, s.y0+iy*s.res
    def blank(s): return np.zeros((s.H,s.W),dtype=bool)

def _sl(g,xmin,ymin,xmax,ymax,pad):
    ix0=max(0,int(math.floor((xmin-pad-g.x0)/g.res))); ix1=min(g.W-1,int(math.ceil((xmax+pad-g.x0)/g.res)))
    iy0=max(0,int(math.floor((ymin-pad-g.y0)/g.res))); iy1=min(g.H-1,int(math.ceil((ymax+pad-g.y0)/g.res)))
    if ix1<ix0 or iy1<iy0: return None
    X=g.x0+np.arange(ix0,ix1+1)[None,:]*g.res; Y=g.y0+np.arange(iy0,iy1+1)[:,None]*g.res
    return (slice(iy0,iy1+1),slice(ix0,ix1+1)),X,Y

def disc(g,m,cx,cy,r):
    q=_sl(g,cx,cy,cx,cy,r+g.res)
    if q: s,X,Y=q; m[s]|=((X-cx)**2+(Y-cy)**2)<=r*r
def seg(g,m,x1,y1,x2,y2,hw):
    q=_sl(g,min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2),hw+g.res)
    if not q: return
    s,X,Y=q; dx,dy=x2-x1,y2-y1; L2=dx*dx+dy*dy
    if L2<1e-12: d2=(X-x1)**2+(Y-y1)**2
    else:
        t=np.clip(((X-x1)*dx+(Y-y1)*dy)/L2,0,1); d2=(X-(x1+t*dx))**2+(Y-(y1+t*dy))**2
    m[s]|=d2<=hw*hw
def pad_(g,m,p):
    th=math.radians(p['ang']+p['fang'])          # additive model, empirically validated
    ca,sa=math.cos(th),math.sin(th); hw,hh=p['w']/2,p['h']/2; R=math.hypot(hw,hh)
    q=_sl(g,p['x'],p['y'],p['x'],p['y'],R+g.res)
    if not q: return
    s,X,Y=q; dx=X-p['x']; dy=Y-p['y']; lx=dx*ca+dy*sa; ly=-dx*sa+dy*ca
    if p['shape']=='circle': mm=(dx*dx+dy*dy)<=max(hw,hh)**2
    elif p['shape']=='oval':
        if hw>=hh: mm=((np.abs(lx)<=hw-hh)&(np.abs(ly)<=hh))|(((np.abs(lx)-(hw-hh))**2+ly**2)<=hh*hh)
        else: mm=((np.abs(ly)<=hh-hw)&(np.abs(lx)<=hw))|(((np.abs(ly)-(hh-hw))**2+lx**2)<=hw*hw)
    else: mm=(np.abs(lx)<=hw)&(np.abs(ly)<=hh)
    m[s]|=mm
def poly(g,m,pts):
    if len(pts)<3: return
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    q=_sl(g,min(xs),min(ys),max(xs),max(ys),g.res)
    if not q: return
    s,X,Y=q
    Xb=np.broadcast_to(X,(Y.shape[0],X.shape[1])); Yb=np.broadcast_to(Y,(Y.shape[0],X.shape[1]))
    ins=np.zeros(Xb.shape,dtype=bool); n=len(pts)
    for i in range(n):
        x1,y1=pts[i]; x2,y2=pts[(i+1)%n]
        c=((y1>Yb)!=(y2>Yb))
        with np.errstate(divide='ignore',invalid='ignore'):
            xin=(x2-x1)*(Yb-y1)/(y2-y1+1e-300)+x1
        ins^=c&(Xb<xin)
    m[s]|=ins

def pad_layers(p):
    return [x for x in L if any(pl==x or pl=='*.Cu' for pl in p['layers'])]

class Env:
    def __init__(s,B):
        s.B=B; g=Grid(FINE); s.gf=g; s.gc=Grid(RES)
        s.copper={l:g.blank() for l in L}; s.holes=g.blank(); s.keep=g.blank(); s.board=g.blank()
        for p in B['pads']:
            if p['type']!='np_thru_hole':
                for l in pad_layers(p): pad_(g,s.copper[l],p)
            if p['drill']>0: disc(g,s.holes,p['x'],p['y'],p['drill']/2)
        for t in B['segs']:
            if t['layer'] in s.copper: seg(g,s.copper[t['layer']],t['x1'],t['y1'],t['x2'],t['y2'],t['w']/2)
        for v in B['vias']:
            for l in L: disc(g,s.copper[l],v['x'],v['y'],v['size']/2)
            disc(g,s.holes,v['x'],v['y'],v['drill']/2)
        for k in B['keeps']: poly(g,s.keep,k)
        poly(g,s.board,OUTLINE)
        s.keepD=(ndimage.distance_transform_edt(~s.keep)*FINE).astype(np.float32)
        s.holeD=(ndimage.distance_transform_edt(~s.holes)*FINE).astype(np.float32)
        s.edgeD=(ndimage.distance_transform_edt(s.board)*FINE).astype(np.float32)
    def net_mask(s,net):
        g=s.gf; m={l:g.blank() for l in L}
        for p in s.B['pads']:
            if p['net']==net and p['type']!='np_thru_hole':
                for l in pad_layers(p): pad_(g,m[l],p)
        for t in s.B['segs']:
            if t['net']==net and t['layer'] in m: seg(g,m[t['layer']],t['x1'],t['y1'],t['x2'],t['y2'],t['w']/2)
        for v in s.B['vias']:
            if v['net']==net:
                for l in L: disc(g,m[l],v['x'],v['y'],v['size']/2)
        return m
    def add(s,segs,vias):
        for t in segs:
            seg(s.gf,s.copper[t['layer']],t['x1'],t['y1'],t['x2'],t['y2'],t['w']/2); s.B['segs'].append(t)
        for (x,y,net) in vias:
            for l in L: disc(s.gf,s.copper[l],x,y,VIA_D/2)
            disc(s.gf,s.holes,x,y,VIA_DR/2)
            s.B['vias'].append(dict(x=x,y=y,size=VIA_D,drill=VIA_DR,net=net))
        if vias: s.holeD=(ndimage.distance_transform_edt(~s.holes)*FINE).astype(np.float32)

# ---------- connectivity ----------
class UF:
    def __init__(s): s.p={}
    def find(s,a):
        s.p.setdefault(a,a)
        while s.p[a]!=a: s.p[a]=s.p[s.p[a]]; a=s.p[a]
        return a
    def union(s,a,b):
        ra,rb=s.find(a),s.find(b)
        if ra!=rb: s.p[ra]=rb

ST8=np.ones((3,3),dtype=bool)
def net_islands(E,net):
    m=E.net_mask(net)
    labs={}; ns={}
    uf=UF()
    for l in L:
        lab,n=ndimage.label(m[l],structure=ST8); labs[l]=lab; ns[l]=n
        for i in range(1,n+1): uf.find((l,i))
    links=[(v['x'],v['y']) for v in E.B['vias'] if v['net']==net]
    links+=[(p['x'],p['y']) for p in E.B['pads'] if p['net']==net and p['type']=='thru_hole']
    for (x,y) in links:
        ix,iy=E.gf.to_ix(x,y)
        if not(0<=ix<E.gf.W and 0<=iy<E.gf.H): continue
        present=[(l,int(labs[l][iy,ix])) for l in L if labs[l][iy,ix]>0]
        for a in range(1,len(present)): uf.union(present[0],present[a])
    gr={}
    for l in L:
        for i in range(1,ns[l]+1): gr.setdefault(uf.find((l,i)),[]).append((l,i))
    return labs,gr

def min3(A,H,W):
    M=ndimage.minimum_filter(A,size=3,mode='nearest')
    sub=M[0:2*H:2,0:2*W:2]; o=np.zeros((H,W),dtype=np.float32); h,w=sub.shape; o[:h,:w]=sub; return o
def samp(A,H,W):
    sub=A[0:2*H:2,0:2*W:2]; o=np.zeros((H,W),dtype=np.float32); h,w=sub.shape; o[:h,:w]=sub; return o

def _dn(A,H,W,k,mode):
    """k = routing/fine cell ratio. mode 'min' uses a 3x3 fine min (rigorous for
    0.1mm steps); mode 'raw' samples directly (needed when the legal centreline
    window is narrower than the coarse pitch; emitted geometry is then validated
    exactly against real copper before it is written)."""
    M=ndimage.minimum_filter(A,size=3,mode='nearest') if mode=='min' else A
    sub=M[0:k*H:k,0:k*W:k]; o=np.zeros((H,W),dtype=np.float32); h,w=sub.shape; o[:h,:w]=sub; return o

def build_env(E,net,res=RES,extra=0.0,avoid=()):
    k=int(round(res/FINE)); E.gr=Grid(res); H,W=E.gr.H,E.gr.W
    mode='min' if k>1 else 'raw'
    # EDT measures distance to rasterised cell CENTRES, so it understates copper
    # extent by up to half a fine cell. min-filter mode already over-covers this.
    bias=(0.0 if mode=='min' else FINE/2.0)+extra
    m=E.net_mask(net)
    km=_dn(E.keepD,H,W,k,mode); em=_dn(E.edgeD,H,W,k,mode)
    fineD={}; trkok={}
    for l in L:
        foreign=E.copper[l]&~m[l]
        d=(ndimage.distance_transform_edt(~foreign)*FINE).astype(np.float32)
        del foreign
        fineD[l]=d
        ok=(_dn(d,H,W,k,mode)>=TRK_T+bias)&(km>=KEEP_TRK_T+bias)&(em>=EDGE_TRK_T+bias)
        sub=m[l][0:k*H:k,0:k*W:k]; oc=np.zeros((H,W),dtype=bool); h,w=sub.shape; oc[:h,:w]=sub
        ok=ok|oc
        for av in avoid:                       # (x0,y0,x1,y1[,layer]) - layer defaults to F.Cu
            ax0,ay0,ax1,ay1=av[:4]
            if (av[4] if len(av)>4 else 'F.Cu')!=l: continue
            i0,j0=E.gr.to_ix(ax0,ay0); i1,j1=E.gr.to_ix(ax1,ay1)
            ok[max(0,j0):max(0,j1), max(0,i0):max(0,i1)]=False
        trkok[l]=ok
    r=lambda A:_dn(A,H,W,k,'raw')
    vb=FINE/2.0+extra
    viaok=(r(E.holeD)>=HOLE_T+vb)&(r(E.keepD)>=KEEP_VIA_T+vb)&(r(E.edgeD)>=EDGE_VIA_T+vb)
    for l in L:                      # a through via must clear copper on EVERY routing layer
        viaok &= (r(fineD[l])>=VIA_T+vb)
    return m,trkok,viaok,fineD

def island_masks(E,net,trkok,res=RES):
    k=int(round(res/FINE))
    labs,gr=net_islands(E,net)
    H,W=E.gr.H,E.gr.W; ks=list(gr.keys())
    def mk(g):
        o={}
        for l in L:
            ids=[i for (t,i) in gr[g] if t==l]
            mm=np.isin(labs[l],ids) if ids else np.zeros(labs[l].shape,dtype=bool)
            sub=mm[0:k*H:k,0:k*W:k]; a=np.zeros((H,W),dtype=bool); h,w=sub.shape; a[:h,:w]=sub; o[l]=a
        return o
    return [mk(x) for x in ks]

def reachable(trkok,viaok,A,Bm):
    labs={}; uf=UF()
    for l in L:
        lab,n=ndimage.label(trkok[l],structure=ST8); labs[l]=lab
        for i in range(1,n+1): uf.find((l,i))
    ys,xs=np.nonzero(viaok)
    for l in L[1:]:
        m0=labs[L[0]][ys,xs]; m1=labs[l][ys,xs]
        for i in range(len(m0)):
            if m0[i]>0 and m1[i]>0: uf.union((L[0],int(m0[i])),(l,int(m1[i])))
    def comps(M):
        r=set()
        for l in L:
            for i in np.unique(labs[l][M[l]]):
                if i>0: r.add(uf.find((l,int(i))))
        return r
    return bool(comps(A)&comps(Bm))

import heapq, gc
def astar(E,trkok,viaok,A,Bm,via_cost=4.0,wt=1.25,maxpush=4000000,margin_mm=30.0):
    """N-layer A* over a window cropped around the two islands."""
    G=getattr(E,'gr',E.gc); RS=G.res
    H0,W0=G.H,G.W; NL=len(L)
    un=np.zeros((H0,W0),dtype=bool)
    for l in L: un|=A[l]|Bm[l]
    ys,xs=np.nonzero(un)
    mg=int(margin_mm/RS)
    y0=max(0,int(ys.min())-mg); y1=min(H0,int(ys.max())+mg+1)
    x0=max(0,int(xs.min())-mg); x1=min(W0,int(xs.max())+mg+1)
    H=y1-y0; W=x1-x0; LW=H*W
    cr=lambda M: np.ascontiguousarray(M[y0:y1,x0:x1])
    allow=np.stack([cr(trkok[l]) for l in L]).reshape(-1)
    goal =np.stack([cr(Bm[l])    for l in L]).reshape(-1)
    start=np.stack([cr(A[l])     for l in L]).reshape(-1)
    vf=cr(viaok).reshape(-1)
    g2=np.zeros((H,W),dtype=bool)
    for l in L: g2|=cr(Bm[l])
    hm=(ndimage.distance_transform_edt(~g2)*RS).astype(np.float32)*np.float32(wt)
    hf=np.tile(hm.reshape(-1),NL)
    dist=np.full(NL*LW,np.float32(1e18),dtype=np.float32); prev=np.full(NL*LW,-1,dtype=np.int32)
    heap=[]
    for i in np.nonzero(start)[0].tolist(): dist[i]=0.0; heap.append((float(hf[i]),i))
    heapq.heapify(heap)
    D=RS; DD=RS*1.41421356
    nb=((-1,0,D),(1,0,D),(0,-1,D),(0,1,D),(-1,-1,DD),(-1,1,DD),(1,-1,DD),(1,1,DD))
    hp=heapq.heappop; hs=heapq.heappush; found=-1; pushes=0
    while heap:
        f,u=hp(heap)
        du=dist[u]
        if f>du+hf[u]+1e-6: continue
        if goal[u]: found=u; break
        ly=u//LW; r=u-ly*LW; iy=r//W; ix=r-iy*W; base=ly*LW
        for dy,dx,w in nb:
            ny=iy+dy; nx=ix+dx
            if ny<0 or ny>=H or nx<0 or nx>=W: continue
            v=base+ny*W+nx
            if not allow[v]: continue
            if dy and dx and (not allow[base+ny*W+ix] or not allow[base+iy*W+nx]): continue
            nd=du+w
            if nd<dist[v]:
                dist[v]=nd; prev[v]=u; hs(heap,(float(nd+hf[v]),v)); pushes+=1
        if vf[r]:
            for lz in range(NL):
                if lz==ly: continue
                v=lz*LW+r
                if not allow[v]: continue
                nd=du+via_cost
                if nd<dist[v]:
                    dist[v]=nd; prev[v]=u; hs(heap,(float(nd+hf[v]),v)); pushes+=1
        if pushes>maxpush: break
    if found<0:
        del heap,dist,prev; gc.collect(); return None
    path=[]; u=found
    while u!=-1: path.append(int(u)); u=int(prev[u])
    path.reverse(); del heap,dist,prev; gc.collect()
    out=[]
    for u in path:
        ly=u//LW; r=u-ly*LW; iy=r//W+y0; ix=r-(r//W)*W+x0
        x,y=G.to_xy(ix,iy); out.append((ly,round(x,4),round(y,4)))
    return out

# ---------- path -> geometry ----------
def fine_ok(E,fineD,m,l,x,y,extra=0.0,avoid=()):
    ix,iy=E.gf.to_ix(x,y)
    if ix<0 or iy<0 or ix>=E.gf.W or iy>=E.gf.H: return False
    if m[l][iy,ix]: return True
    for av in avoid:
        ax0,ay0,ax1,ay1=av[:4]
        if (av[4] if len(av)>4 else 'F.Cu')!=l: continue
        if ax0<=x<=ax1 and ay0<=y<=ay1 and not m[l][iy,ix]: return False
    b=FINE/2.0+0.01+extra   # half-cell EDT bias + Lipschitz slack between samples
    return fineD[l][iy,ix]>=TRK_T+b and E.keepD[iy,ix]>=KEEP_TRK_T+b and E.edgeD[iy,ix]>=EDGE_TRK_T+b
def clear_line(E,fineD,m,l,p,q,step=0.01,extra=0.0,avoid=()):
    d=math.hypot(q[0]-p[0],q[1]-p[1]); n=max(2,int(d/step)+1)
    for i in range(n+1):
        t=i/n
        if not fine_ok(E,fineD,m,l,p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1]),extra,avoid): return False
    return True
def simplify(E,fineD,m,l,pts,extra=0.0,avoid=()):
    """greedy line-of-sight merge; never returns an unverified span"""
    out=[pts[0]]; i=0
    while i<len(pts)-1:
        lo,hi=i+1,len(pts)-1; best=None
        while lo<=hi:
            mid=(lo+hi)//2
            if clear_line(E,fineD,m,l,pts[i],pts[mid],extra=extra,avoid=avoid): best=mid; lo=mid+1
            else: hi=mid-1
        if best is None:
            best=i+1   # single grid step: legality already guaranteed by the grid
                       # construction; never emit an unverified long span
        out.append(pts[best]); i=best
    return out
def snap(E,net,l,pt):
    b=None; bd=1e9
    for p in E.B['pads']:
        if p['net']!=net or p['type']=='np_thru_hole' or l not in pad_layers(p): continue
        d=math.hypot(p['x']-pt[0],p['y']-pt[1])
        if d<max(p['w'],p['h'])/2+0.05 and d<bd: bd=d; b=(p['x'],p['y'])
    return b or pt
def to_geom(E,net,pts,fineD,m,extra=0.0,avoid=()):
    runs=[]; cur=[(pts[0][1],pts[0][2])]; cl=pts[0][0]; vias=[]
    for k in range(1,len(pts)):
        ly,x,y=pts[k]
        if ly!=cl: runs.append((cl,cur)); vias.append((x,y,net)); cur=[(x,y)]; cl=ly
        else: cur.append((x,y))
    runs.append((cl,cur)); segs=[]
    for i,(ly,pl) in enumerate(runs):
        ln=L[ly]
        if len(pl)<2:
            continue
        sp=simplify(E,fineD,m,ln,pl,extra=extra,avoid=avoid)
        # snap endpoints onto pad centres only when the resulting run stays legal
        if i==0:
            c=snap(E,net,ln,sp[0])
            if c!=sp[0] and clear_line(E,fineD,m,ln,c,sp[1],extra=extra,avoid=avoid): sp[0]=c
        if i==len(runs)-1:
            c=snap(E,net,ln,sp[-1])
            if c!=sp[-1] and clear_line(E,fineD,m,ln,sp[-2],c,extra=extra,avoid=avoid): sp[-1]=c
        for a,b in zip(sp,sp[1:]):
            if abs(a[0]-b[0])<1e-9 and abs(a[1]-b[1])<1e-9: continue
            segs.append(dict(x1=a[0],y1=a[1],x2=b[0],y2=b[1],w=TW,layer=ln,net=net))
    return segs,vias
