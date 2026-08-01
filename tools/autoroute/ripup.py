"""Minimal cuts for the 4-layer board (approved by Jason 2026-08-01).

Two pads are physically stranded: their ONLY escape corridor is occupied by
another net's trace, and the remaining gap (0.165mm / 0.152mm) is far below the
0.5mm a 0.2mm track needs. Adding inner layers does NOT help these two, because
a 0.8mm via cannot fit beside the pad either -- the track must first escape
laterally on the outer layer. Verified by exhaustive reachability analysis.

  U7.11  ADC_LDO  <- blocked by a +3V3_A trace at x=64.135
  U10.11 HP_CPP   <- blocked by an HP_CPN escape at x=114.127

Both cut nets are rerouted by the router and validated by kicad-cli DRC.
"""
RIPUP = [
  ('+3V3_A','F.Cu',(64.135,50.289),(64.135,53.803)),
  ('HP_CPN','F.Cu',(113.438,56.750),(113.867,56.750)),
  ('HP_CPN','F.Cu',(113.867,56.750),(114.127,56.490)),
  ('HP_CPN','F.Cu',(114.127,56.490),(114.127,53.529)),
  ('HP_CPN','F.Cu',(114.127,53.529),(112.707,52.109)),
]
def match(s,r):
    net,layer,a,b=r
    if s['net']!=net or s['layer']!=layer: return False
    p=(s['x1'],s['y1']); q=(s['x2'],s['y2'])
    t=lambda u,v: abs(u[0]-v[0])<1e-3 and abs(u[1]-v[1])<1e-3
    return (t(p,a) and t(q,b)) or (t(p,b) and t(q,a))
# vias to remove (net, x, y). HP_ENABLE's only north corridor out of U10.13 is
# 0.456mm wide where 0.5mm is needed -- pinched by this HPVDD via. Removing it
# (and its two stubs) lets the router re-place it clear of the corridor.
RIPUP_VIAS = []
RIPUP2 = [
  # GND diagonal walling the U7 west escape neck. U7.8 (+3V3_A) and U7.11
  # (ADC_LDO) both need this neck and it fits one track; cutting this frees it.
  # Safe: GND is carried by pours on F.Cu/B.Cu AND the new solid In1.Cu plane,
  # so removing a redundant GND trace costs nothing. DRC re-verifies GND.
  ('GND','F.Cu',(63.574,50.401),(60.305,53.670)),
  ('GND','F.Cu',(63.574,50.297),(63.574,50.401)),
  ('GND','F.Cu',(64.371,49.500),(63.574,50.297)),
  # free U7.8's escape stub so the router picks its own exit direction, and the
  # matching 0.22mm tip on the far island; both were leftovers of the cut wall.
  ('+3V3_A','F.Cu',(65.138,50.000),(64.4242,50.000)),
  ('+3V3_A','F.Cu',(64.4242,50.000),(64.135,50.289)),
  ('+3V3_A','F.Cu',(64.135,53.803),(64.294,53.962)),
]

def apply(B, extra_segs=(), extra_vias=()):
    rs=list(RIPUP)+list(RIPUP2)+list(extra_segs)
    rv=list(RIPUP_VIAS)+list(extra_vias)
    kept=[]; removed=[]
    for s in B['segs']:
        if any(match(s,r) for r in rs): removed.append(s)
        else: kept.append(s)
    B['segs']=kept
    if rv:
        kv=[]
        for v in B['vias']:
            if any(v['net']==n and abs(v['x']-x)<1e-3 and abs(v['y']-y)<1e-3 for (n,x,y) in rv):
                removed.append(v)
            else: kv.append(v)
        B['vias']=kv
    return removed
