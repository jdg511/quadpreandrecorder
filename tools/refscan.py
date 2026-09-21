import re
from pathlib import Path

src = Path("tools/generate_schematic.py").read_text(encoding="utf-8")
for prefix in ("R", "C", "SW", "D", "J", "U", "Q", "L", "K", "TP"):
    nums = set(int(m) for m in re.findall(r'"%s(\d+)"' % prefix, src)
               if len(m) <= 3)
    if not nums:
        continue
    hi = max(nums)
    missing = [n for n in range(1, hi + 1) if n not in nums]
    print("%-3s count=%-4d max=%-4d free below max: %s"
          % (prefix, len(nums), hi, missing[:15]))
