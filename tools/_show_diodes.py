from pathlib import Path

src = Path(__file__).with_name("generate_schematic.py").read_text(encoding="utf-8")
lines = src.splitlines()
want = ('"D1"', '"D10"', '"D12"', '"D14"', '"D15"', '"D16"', '"D17"', '"D18"', '"D19"', '"SW4"', '"SW3"')
for n, line in enumerate(lines):
    if any(w in line for w in want) and "part(" in line:
        print(f"--- line {n+1} ---")
        for k in range(n, min(len(lines), n + 4)):
            print("   ", lines[k].rstrip())
        print()
