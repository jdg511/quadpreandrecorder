"""Mark the pre-placed GND fanout in the DSN as protected wiring.

KiCad exports existing tracks as `(type route)`, which tells Freerouting it
may rip them up and re-route them. Since In1.Cu is handed over as a power
plane, Freerouting considers GND already connected and would simply delete
the fanout - putting us right back where we started. `(type protect)` means
"keep this exactly as it is".
"""
import re
import sys
from pathlib import Path

src = Path(sys.argv[1] if len(sys.argv) > 1
           else "hardware/review_outputs/QuadPreRecorder-unrouted.dsn")
t = src.read_text(encoding="utf-8", errors="replace")

i = t.find("(wiring")
if i < 0:
    raise SystemExit("no wiring section - nothing was pre-placed")

head, tail = t[:i], t[i:]
before = tail.count("(type route)")
tail = tail.replace("(type route)", "(type protect)")
after = tail.count("(type protect)")

src.write_text(head + tail, encoding="utf-8")
print("wiring entries protected: %d (was %d routable)" % (after, before))

# show one via line so the syntax is on the record
m = re.search(r"\(via [^\n]*", tail)
print("sample via:", m.group(0) if m else "none found")
print(src)
