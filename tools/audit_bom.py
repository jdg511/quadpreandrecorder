"""Audit the current BOM for parts a fab house cannot actually source."""
import csv, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUR = ROOT / "review_outputs" / "BOM-current.csv"
OLD = ROOT / "hardware" / "manufacturing" / "QuadPreRecorder-BOM.csv"

PLACEHOLDER = re.compile(r"\bseries\b|\bgeneric\b|^\s*$|\bTBD\b|\bassorted\b", re.I)


def load(path, mpn_keys, ref_keys):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            k = {kk.strip().lower(): (vv or "").strip() for kk, vv in r.items() if kk}
            mpn = next((k[x] for x in mpn_keys if x in k and k[x]), "")
            ref = next((k[x] for x in ref_keys if x in k and k[x]), "")
            qty = next((k[x] for x in ("qty", "quantity") if x in k and k[x]), "")
            rows.append({"ref": ref, "mpn": mpn, "qty": qty,
                         "value": k.get("value", k.get("comment", "")),
                         "mfr": k.get("manufacturer", "")})
    return rows


def expand(ref_field):
    out = []
    for part in ref_field.replace(" ", "").split(","):
        m = re.match(r"^([A-Za-z]+)(\d+)-([A-Za-z]*)(\d+)$", part)
        if m:
            out += [f"{m.group(1)}{i}" for i in range(int(m.group(2)), int(m.group(4)) + 1)]
        elif part:
            out.append(part)
    return out


cur = load(CUR, ("mpn", "manufacturer part number"), ("reference", "references", "designator"))
old = load(OLD, ("manufacturer part number", "mpn"), ("designator", "reference"))

cur_refs = {r for row in cur for r in expand(row["ref"])}
old_refs = {r for row in old for r in expand(row["ref"])}

print("=" * 78)
print("CURRENT SCHEMATIC: %d BOM lines, %d placements" % (len(cur), len(cur_refs)))
print("BOM ON DISK      : %d BOM lines, %d placements" % (len(old), len(old_refs)))
new = sorted(cur_refs - old_refs, key=lambda s: (re.sub(r"\d", "", s), int(re.sub(r"\D", "", s) or 0)))
gone = sorted(old_refs - cur_refs)
print()
print("PARTS MISSING FROM THE BOM ON DISK (%d): %s" % (len(new), ", ".join(new) or "none"))
print("IN THE OLD BOM BUT NOT THE SCHEMATIC (%d): %s" % (len(gone), ", ".join(gone) or "none"))

blank, placeholder, ok = [], [], []
for row in cur:
    refs = expand(row["ref"])
    if not row["mpn"]:
        blank.append((row["ref"], row["value"], len(refs)))
    elif PLACEHOLDER.search(row["mpn"]):
        placeholder.append((row["ref"], row["value"], row["mfr"], row["mpn"], len(refs)))
    else:
        ok.append((row["ref"], row["mpn"], len(refs)))

n_ph = sum(x[4] for x in placeholder)
n_bl = sum(x[2] for x in blank)
n_ok = sum(x[2] for x in ok)
print()
print("=" * 78)
print("ORDERABLE MPN         : %3d lines / %3d placements" % (len(ok), n_ok))
print("PLACEHOLDER, NOT REAL : %3d lines / %3d placements" % (len(placeholder), n_ph))
print("BLANK MPN             : %3d lines / %3d placements" % (len(blank), n_bl))
print()
print("--- PLACEHOLDER MPNs (a fab house cannot buy these) ---")
for ref, val, mfr, mpn, n in placeholder:
    print("  %-28s %-22s %-14s %s" % (ref[:28], val[:22], mfr[:14], mpn[:34]))
print()
print("--- BLANK MPNs ---")
for ref, val, n in blank:
    print("  %-28s %s" % (ref[:28], val[:34]))
