import re
from pathlib import Path

src = Path(__file__).with_name("generate_schematic.py").read_text(encoding="utf-8")
i = src.find("class Part")
print("=== class Part ===")
print(src[i:i + 1600])
print()
print("=== where properties get emitted ===")
for m in re.finditer(r'\(property "(\w+)"', src):
    pass
names = sorted(set(re.findall(r'\(property "(\w+)"', src)))
print("property names written by the generator:", names)
