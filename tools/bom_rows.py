import csv
from pathlib import Path

WANT = {"J1", "J2", "J3", "J4", "J5", "J9", "SW2", "SW3", "SW4",
        "D4", "D5", "U8", "RV1", "SW1"}
p = Path("review_outputs/BOM-current.csv")
with p.open(newline="", encoding="utf-8-sig") as fh:
    rows = list(csv.reader(fh))
hdr = rows[0]
print(" | ".join(hdr))
print("-" * 100)
for r in rows[1:]:
    refs = [x.strip() for x in r[0].split(",")]
    if any(x in WANT for x in refs):
        print(" | ".join(r))
