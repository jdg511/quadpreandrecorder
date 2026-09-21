from pathlib import Path

d = Path("hardware/review_outputs/QuadPreRecorder-unrouted.dsn")
t = d.read_text(encoding="utf-8", errors="replace")
print("size            :", len(t))
print("has (wiring     :", "(wiring" in t)
print("(via  count     :", t.count("(via "))
print("(wire  count    :", t.count("(wire "))
i = t.find("(wiring")
if i >= 0:
    print("\nfirst 600 chars of the wiring section:")
    print(t[i:i + 600])
