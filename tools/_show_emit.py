from pathlib import Path

src = Path(__file__).with_name("generate_schematic.py").read_text(encoding="utf-8")
lines = src.splitlines()
for n, line in enumerate(lines, 1):
    if "Manufacturer" in line or "part.mpn" in line or "item.mpn" in line:
        lo = max(0, n - 12)
        hi = min(len(lines), n + 14)
        print(f"--- hit at line {n} ---")
        for k in range(lo, hi):
            print(f"{k+1:5}  {lines[k]}")
        print()
        break
