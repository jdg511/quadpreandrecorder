"""Send the review packets to LM Studio (local OpenAI-compatible server) one by one; write each answer to a file."""
import json, urllib.request, time, sys, os
BASE = "http://localhost:1234/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
packets = json.load(open(os.path.join(HERE, "packets.json"), encoding="utf-8"))
model = sys.argv[1] if len(sys.argv) > 1 else ""
SYSTEM = ("You are a senior mixed-signal hardware reviewer doing an independent triple-check of a KiCad design before it goes to fabrication. "
          "You are given extracts of a machine-generated review dossier (values, nets and pin tables read directly from the schematic and PCB). "
          "Find real errors: wrong values, wrong pins, wrong rails, unsafe conditions, datasheet violations, layout risks. "
          "Rules: be concrete and cite the exact row, part, pin or net; do not restate the design; no generic advice; if something is fine say so in one line; "
          "rank findings BLOCKER / SHOULD FIX / NOTE; check every piece of arithmetic yourself. Plain text, no markdown tables. Do not use the em dash character. Do not try to recall IC pinouts from memory: the pin-by-pin tables you are given were already checked against the manufacturer datasheets, so only flag a pin if the packet itself contains a contradiction (for example a pin function that does not fit the net it lands on, or two rows that disagree). Focus on values, rails, polarities, missing parts, arithmetic and layout.")
log = open(os.path.join(HERE, "run.log"), "a", buffering=1)
for name, text in packets.items():
    out = os.path.join(HERE, "out", name + ".txt")
    if os.path.exists(out):
        continue
    body = {"messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "Packet %s. Review it and write the findings directly, ranked, at most 8 items, each 1-3 lines with the part or net it concerns. If you rely on a datasheet limit you are not certain of, write VERIFY next to it.\n\n%s" % (name, text)},
                         {"role": "assistant", "content": "<think>\n\n</think>\n\n"}],
            "temperature": 0.2, "max_tokens": 1800}
    if model: body["model"] = model
    t0 = time.time()
    req = urllib.request.Request(BASE + "/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + os.environ.get("LM_API_TOKEN", "")})
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            d = json.load(r)
        msg = d["choices"][0]["message"]
        content = msg.get("content") or ""
        if not content.strip() and msg.get("reasoning_content"):
            content = "[reasoning only, truncated]\n" + msg["reasoning_content"][-6000:]
        with open(out, "w", encoding="utf-8") as f:
            f.write(content)
        log.write("%s done in %.0fs, %d chars, model %s\n" % (name, time.time() - t0, len(content), d.get("model")))
    except Exception as e:
        log.write("%s FAILED: %r\n" % (name, e))
log.write("ALL DONE\n")
