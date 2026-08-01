"""Insert routed geometry into the .kicad_pcb by pure text insertion.
No re-serialisation of the existing file: cut segments are deleted by exact
match and new segments/vias are inserted before the first zone block."""
import sys, os, re, uuid, pickle, shutil
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import arlib, ripup

SRC=arlib.PCB
def seg_sexp(s):
    return ('\t(segment\n\t\t(start %s %s)\n\t\t(end %s %s)\n\t\t(width %s)\n'
            '\t\t(layer "%s")\n\t\t(net "%s")\n\t\t(uuid "%s")\n\t)\n'%(
            f"{s['x1']:.4f}".rstrip('0').rstrip('.'), f"{s['y1']:.4f}".rstrip('0').rstrip('.'),
            f"{s['x2']:.4f}".rstrip('0').rstrip('.'), f"{s['y2']:.4f}".rstrip('0').rstrip('.'),
            s['w'], s['layer'], s['net'], uuid.uuid4()))
def via_sexp(x,y,net):
    return ('\t(via\n\t\t(at %s %s)\n\t\t(size %s)\n\t\t(drill %s)\n'
            '\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "%s")\n\t\t(uuid "%s")\n\t)\n'%(
            f"{x:.4f}".rstrip('0').rstrip('.'), f"{y:.4f}".rstrip('0').rstrip('.'),
            arlib.VIA_D, arlib.VIA_DR, net, uuid.uuid4()))

def find_block(s,start):
    depth=0; k=start
    while k<len(s):
        if s[k]=='(': depth+=1
        elif s[k]==')':
            depth-=1
            if depth==0: return k+1
        k+=1
    return -1

def run(state_path,out_path):
    st=pickle.load(open(state_path,'rb'))
    s=open(SRC,encoding='utf-8').read()
    # 1. delete the ripped segments by exact coordinate match
    ndel=0
    for (net,layer,a,b) in ripup.RIPUP+ripup.RIPUP2:
        pat=re.compile(r'\t\(segment\n\t\t\(start ([-\d.]+) ([-\d.]+)\)\n\t\t\(end ([-\d.]+) ([-\d.]+)\)\n'
                       r'\t\t\(width [\d.]+\)\n\t\t\(layer "([^"]+)"\)\n\t\t\(net "([^"]*)"\)\n\t\t\(uuid "[^"]*"\)\n\t\)\n')
        def keep(mo):
            nonlocal ndel
            x1,y1,x2,y2,lay,nt=float(mo.group(1)),float(mo.group(2)),float(mo.group(3)),float(mo.group(4)),mo.group(5),mo.group(6)
            t=lambda u,v: abs(u[0]-v[0])<1e-3 and abs(u[1]-v[1])<1e-3
            if nt==net and lay==layer and ((t((x1,y1),a) and t((x2,y2),b)) or (t((x1,y1),b) and t((x2,y2),a))):
                ndel+=1; return ''
            return mo.group(0)
        s=pat.sub(keep,s)
    # 2. build insertion text
    add=[]
    for n,rec in sorted(st['added'].items()):
        for sg in rec['segs']: add.append(seg_sexp(sg))
        for (x,y,nt) in rec['vias']: add.append(via_sexp(x,y,nt))
    ins=''.join(add)
    i=s.find('\n\t(zone\n')
    assert i>0,'no zone block found'
    s=s[:i+1]+ins+s[i+1:]
    open(out_path,'w',encoding='utf-8',newline='').write(s)
    nseg=sum(len(r['segs']) for r in st['added'].values())
    nvia=sum(len(r['vias']) for r in st['added'].values())
    print('deleted %d ripped segments; inserted %d segments + %d vias for %d nets'%(ndel,nseg,nvia,len(st['added'])))
    return ndel,nseg,nvia

if __name__=='__main__':
    out=sys.argv[2] if len(sys.argv)>2 else SRC
    shutil.copy(SRC,SRC+'.prewrite.bak')
    run(sys.argv[1],out)
