"""Like protect_fanout.py, but wires/vias of the listed nets stay (type route) so
Freerouting may rip them up and re-route them.  usage: protect_except.py DSN NET,NET,..."""
import re, sys
from pathlib import Path
src = Path(sys.argv[1]); free = set(sys.argv[2].split(","))
t = src.read_text(encoding="utf-8", errors="replace")
i = t.find("(wiring"); head, tail = t[:i], t[i:]
n_prot = n_free = 0
def fix(m):
    global n_prot, n_free
    block = m.group(0)
    net = re.search(r"\(net ([^\s)]+)\)", block)
    if net and net.group(1).strip('"') in free:
        n_free += 1; return block
    n_prot += 1
    return block.replace("(type route)", "(type protect)")
# a wire or via entry: from "(wire" / "(via" to its "(type route)" token
tail = re.sub(r"\((?:wire|via)\b(?:(?!\(type route\)).)*?\(type route\)", fix, tail, flags=re.S)
src.write_text(head + tail, encoding="utf-8")
print("protected %d entries, left routable %d (nets: %s)" % (n_prot, n_free, ",".join(sorted(free))))
