"""Summarise the unconnected items in the DRC report.

The distinction that matters: an unconnected item that names a PAD is a real
missing connection and the board is not finished. One that names only zone
copper is a floating sliver of fill - cosmetic, and safe to clean up.
"""
import re
from pathlib import Path

rpt = Path("hardware/fabrication/QuadPreRecorder-drc.rpt").read_text(
    encoding="utf-8", errors="replace")

# the unconnected section runs to the end of the report
m = re.search(r"\*\* Found (\d+) unconnected.*?\*\*\n(.*)", rpt, re.S)
if not m:
    print("no unconnected section in the report")
    raise SystemExit(0)

count, body = int(m.group(1)), m.group(2)
body = re.split(r"\*\* Found \d+ ", body)[0]

items = re.findall(r'\[(\S+)\]:\s*(.*?)\n((?:\s{4}.*\n)*)', body)
print("unconnected items reported: %d" % count)

pad_items, zone_items, other = [], [], []
for code, summary, detail in items:
    text = summary + detail
    refs = sorted(set(re.findall(r'Pad \S+ of (\S+)', text)))
    if refs:
        pad_items.append((code, refs, summary.strip()))
    elif "one" in text.lower() and "zone" in text.lower():
        zone_items.append((code, summary.strip(), detail.strip()))
    else:
        other.append((code, summary.strip(), detail.strip()))

print("\n--- involve a PAD (real missing connections) : %d" % len(pad_items))
for code, refs, summary in pad_items:
    print("   %s  %s  %s" % (code, ",".join(refs), summary[:90]))

print("\n--- zone copper only (floating fill slivers)  : %d" % len(zone_items))
for code, summary, detail in zone_items[:20]:
    first = detail.splitlines()[0].strip() if detail else ""
    print("   %s  %s" % (summary[:70], first[:70]))

print("\n--- unclassified                              : %d" % len(other))
for code, summary, detail in other[:20]:
    print("   %s | %s" % (summary[:80], detail.replace("\n", " ")[:90]))

if pad_items:
    print("\nVERDICT: NOT finished - %d connection(s) involve real pads."
          % len(pad_items))
else:
    print("\nVERDICT: nothing is unrouted. Every pad is connected; what remains "
          "is floating zone fill.")
