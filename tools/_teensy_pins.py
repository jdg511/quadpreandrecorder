from pathlib import Path

src = Path(__file__).with_name("generate_schematic.py").read_text(encoding="utf-8")
lines = src.splitlines()
hits = [n for n, l in enumerate(lines) if "teensy_nets" in l]
print("teensy_nets on lines:", [h + 1 for h in hits])
h = hits[0]
for k in range(max(0, h - 3), min(len(lines), h + 45)):
    print(f"{k+1:5}  {lines[k].rstrip()}")
