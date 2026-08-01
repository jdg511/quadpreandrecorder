"""Exact analytic clearance validation of emitted geometry against real copper.
Independent of the routing grid - this is the check that must pass before writing."""
import math, sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import arlib
CLR=0.15; HOLE=0.25

def seg_seg(p1,p2,p3,p4):
    def d_ps(p,a,b):
        ax,ay=a; bx,by=b; dx,dy=bx-ax,by-ay; L2=dx*dx+dy*dy
        t=0.0 if L2<1e-15 else max(0.0,min(1.0,((p[0]-ax)*dx+(p[1]-ay)*dy)/L2))
        return math.hypot(p[0]-(ax+t*dx),p[1]-(ay+t*dy))
    def ccw(a,b,c): return (c[1]-a[1])*(b[0]-a[0])-(b[1]-a[1])*(c[0]-a[0])
    if (ccw(p1,p3,p4)*ccw(p2,p3,p4)<0) and (ccw(p3,p1,p2)*ccw(p4,p1,p2)<0): return 0.0
    return min(d_ps(p1,p3,p4),d_ps(p2,p3,p4),d_ps(p3,p1,p2),d_ps(p4,p1,p2))

def pad_rect(p,shrink=0.0):
    th=math.radians(p['ang']+p['fang']); ca,sa=math.cos(th),math.sin(th)
    hw=max(1e-6,p['w']/2-shrink); hh=max(1e-6,p['h']/2-shrink)
    return [(p['x']+dx*ca-dy*sa, p['y']+dx*sa+dy*ca) for dx,dy in ((-hw,-hh),(hw,-hh),(hw,hh),(-hw,hh))]

def seg_pad(a,b,p):
    """exact distance from segment ab to the true pad shape (0 if touching/inside)"""
    sh=p['shape']; w,h=p['w'],p['h']
    if sh=='circle':
        r=max(w,h)/2
        return max(0.0, seg_seg(a,b,(p['x'],p['y']),(p['x'],p['y']))-r)
    if sh=='oval':
        th=math.radians(p['ang']+p['fang']); ca,sa=math.cos(th),math.sin(th)
        if w>=h:
            r=h/2; d=(w-h)/2; e1=(-d,0.0); e2=(d,0.0)
        else:
            r=w/2; d=(h-w)/2; e1=(0.0,-d); e2=(0.0,d)
        q1=(p['x']+e1[0]*ca-e1[1]*sa, p['y']+e1[0]*sa+e1[1]*ca)
        q2=(p['x']+e2[0]*ca-e2[1]*sa, p['y']+e2[0]*sa+e2[1]*ca)
        return max(0.0, seg_seg(a,b,q1,q2)-r)
    if sh=='roundrect' and p.get('rr',0.0)>0:
        r=p['rr']*min(w,h)
        return max(0.0, seg_poly(a,b,pad_rect(p,shrink=r))-r)
    return seg_poly(a,b,pad_rect(p))

def seg_poly(a,b,poly):
    d=min(seg_seg(a,b,poly[i],poly[(i+1)%len(poly)]) for i in range(len(poly)))
    def inside(pt):
        c=False; n=len(poly)
        for i in range(n):
            x1,y1=poly[i]; x2,y2=poly[(i+1)%n]
            if (y1>pt[1])!=(y2>pt[1]):
                if pt[0]<(x2-x1)*(pt[1]-y1)/(y2-y1+1e-300)+x1: c=not c
        return c
    return 0.0 if (inside(a) or inside(b)) else d

def check(B,new_segs,new_vias,verbose=True):
    """B must already contain the new geometry removed (i.e. original + previously written)."""
    bad=[]
    for ns in new_segs:
        net=ns['net']; a=(ns['x1'],ns['y1']); b=(ns['x2'],ns['y2']); hw=ns['w']/2
        for s in B['segs']:
            if s['net']==net or s['layer']!=ns['layer']: continue
            d=seg_seg(a,b,(s['x1'],s['y1']),(s['x2'],s['y2']))-hw-s['w']/2
            if d<CLR-1e-6: bad.append(('trk-trk',net,s['net'],round(d,4),a,b))
        for p in B['pads']:
            if p['net']==net or p['type']=='np_thru_hole': continue
            if ns['layer'] not in arlib.pad_layers(p): continue
            if abs(p['x']-(a[0]+b[0])/2)>60 and abs(p['y']-(a[1]+b[1])/2)>60: continue
            d=seg_pad(a,b,p)-hw
            if d<CLR-1e-6: bad.append(('trk-pad',net,'%s.%s/%s'%(p['ref'],p['num'],p['net']),round(d,4),a,b))
        for v in B['vias']:
            if v['net']==net: continue
            def dps(pt,x,y):
                dx,dy=b[0]-a[0],b[1]-a[1]; L2=dx*dx+dy*dy
                t=0.0 if L2<1e-15 else max(0.0,min(1.0,((x-a[0])*dx+(y-a[1])*dy)/L2))
                return math.hypot(x-(a[0]+t*dx),y-(a[1]+t*dy))
            d=dps(None,v['x'],v['y'])-hw-v['size']/2
            if d<CLR-1e-6: bad.append(('trk-via',net,v['net'],round(d,4),a,b))
    for (vx,vy,vnet) in new_vias:
        for s in B['segs']:
            if s['net']==vnet: continue
            dx,dy=s['x2']-s['x1'],s['y2']-s['y1']; L2=dx*dx+dy*dy
            t=0.0 if L2<1e-15 else max(0.0,min(1.0,((vx-s['x1'])*dx+(vy-s['y1'])*dy)/L2))
            d=math.hypot(vx-(s['x1']+t*dx),vy-(s['y1']+t*dy))-arlib.VIA_D/2-s['w']/2
            if d<CLR-1e-6: bad.append(('via-trk',vnet,s['net'],round(d,4),(vx,vy),None))
        for p in B['pads']:
            if p['net']==vnet: continue
            if p['type']!='np_thru_hole':
                d=seg_pad((vx,vy),(vx,vy),p)-arlib.VIA_D/2
                if d<CLR-1e-6: bad.append(('via-pad',vnet,'%s.%s/%s'%(p['ref'],p['num'],p['net']),round(d,4),(vx,vy),None))
            if p['drill']>0:
                d=math.hypot(vx-p['x'],vy-p['y'])-arlib.VIA_DR/2-p['drill']/2
                if d<HOLE-1e-6: bad.append(('hole-hole',vnet,'%s.%s'%(p['ref'],p['num']),round(d,4),(vx,vy),None))
        for v in B['vias']:
            d=math.hypot(vx-v['x'],vy-v['y'])-arlib.VIA_DR/2-v['drill']/2
            if d<HOLE-1e-6 and math.hypot(vx-v['x'],vy-v['y'])>1e-6:
                bad.append(('hole-hole',vnet,v['net'],round(d,4),(vx,vy),None))
    if verbose:
        print('exact validation: %d violations'%len(bad))
        for x in bad[:25]: print('   ',x)
    return bad
