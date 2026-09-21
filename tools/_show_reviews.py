import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import passive_catalog

print("=== entries that needed an engineering compromise ===")
for line in passive_catalog.review_notes():
    print(" -", line)
print()
print("catalog sizes: %d resistor 1%%, %d resistor 0.1%%, %d ceramic, %d electrolytic"
      % (len(passive_catalog.RESISTOR_1PCT), len(passive_catalog.RESISTOR_01PCT),
         len(passive_catalog.CERAMIC), len(passive_catalog.ELECTROLYTIC)))
