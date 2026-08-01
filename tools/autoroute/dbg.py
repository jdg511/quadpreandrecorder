import sys, os, resource
resource.setrlimit(resource.RLIMIT_AS,(1400*1024*1024,1400*1024*1024))
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import arlib, ripup, pickle, validate as VAL
B=arlib.load_board(); ripup.apply(B)
if os.path.exists('/tmp/ar_state.pkl'):
    st=pickle.load(open('/tmp/ar_state.pkl','rb'))
    for n,rec in st['added'].items():
        B['segs'].extend(rec['segs'])
        for (x,y,nn) in rec['vias']: B['vias'].append(dict(x=x,y=y,size=arlib.VIA_D,drill=arlib.VIA_DR,net=nn))
    print('state: %d nets already routed'%len(st['added']))
E=arlib.Env(B)
for net in sys.argv[1:]:
    print('=== %s'%net)
    for res,extra,marg in ((0.10,0.00,30.0),(0.10,0.03,30.0),(0.05,0.00,18.0),(0.05,0.00,40.0)):
        m,t,v,f=arlib.build_env(E,net,res=res,extra=extra)
        isl=arlib.island_masks(E,net,t,res=res)
        A,Bm=isl
        if A['F.Cu'].sum()+A['B.Cu'].sum()>Bm['F.Cu'].sum()+Bm['B.Cu'].sum(): A,Bm=Bm,A
        rc=arlib.reachable(t,v,A,Bm)
        r=None
        if rc:
            try: r=arlib.astar(E,t,v,A,Bm,via_cost=4.0,wt=1.10,maxpush=3000000,margin_mm=marg)
            except MemoryError: r='MEM'
        print('  res=%.2f x=%.2f marg=%.0f reach=%-5s astar=%s'%(res,extra,marg,rc,
              ('None' if r is None else ('MEM' if r=='MEM' else '%d pts'%len(r)))))
        if rc and isinstance(r,list): break
