# Rev C2 sourcing and control-height report

2026-09-08. Sources: LCSC/JLCPCB parametric DB, Mouser API, DigiKey API, manufacturer
datasheets. Prices USD, qty 1 unless noted.

---

## 0. STATUS 2026-09-09: both blocking footprint errors are FIXED

Verified after the change: **ERC 0 violations, DRC 0 violations, 0 schematic
parity issues.** Board otherwise unchanged.

**D1, D10, D12, D14** — was `SS34-E3/57T`, which is SMC/DO-214AB on an SMA
footprint. Now **Diodes Inc B340A-13-F**, a genuine 40 V 3 A Schottky in
DO-214AC/SMA. Active, 28,006 in stock at Mouser, $0.51 qty1 / $0.241 qty10.
Alternate: LangJie SS34 in SMA (LCSC C7450457, 16k stock, $0.029).
Note: I also checked ROHM RB050L-60TE25 as a candidate and rejected it — it is
NRND with zero stock.

**D15-D19** — was `BAT54W-7-F`, a 3-lead SC-70/SOT-323 part on a 2-lead SOD-123
footprint, and down to ~65 pieces in stock worldwide against 5 per board.
Now **1N4148W-7-F**. This is not merely a package fix; silicon is the better
part for this circuit, for three reasons:

1. **Leakage.** D18/D19 block VBAT (3.7 V) from an unpowered Teensy pin through
   a 1 M pull-up, and D15-D17 feed BOOST_EN through the 1 M pull-down R88. A
   Schottky leaks about 1 uA, which across 1 M is roughly a volt of error and
   can hold the soft-power latch on. Silicon leaks about 25 nA, some 40x
   better, so the unit actually powers off.
2. **Isolation margin.** An unpowered Teensy clamps its pins to ~0.5 V. A
   Schottky's 0.3 V drop can begin conducting at that clamp voltage. Silicon's
   higher drop cannot.
3. **Forward drop is irrelevant here.** These carry microamps into a
   high-impedance enable pin. Even at 0.45 V of drop, BOOST_EN still reaches
   ~2.85 V against a ~1.3 V threshold.

It also consolidates with D13, which was already a 1N4148W. Alternate:
ST(Semtech) 1N4148W (LCSC C81598, Basic library, 3.5 M stock).

---

## 1. HISTORICAL: the two footprint mismatches (now fixed, see section 0)

These are wrong in the schematic today. Parts ordered against them will not fit the board.

### 1.1 D1, D10, D12, D14 (4 placements) - SS34 in the wrong package

- BOM says `SS34-E3/57T` (Vishay). That part is **SMC / DO-214AB**.
- Board footprint is `Diode_SMD:D_SMA` (**DO-214AC**).
- Confirmed against both DigiKey and LCSC (C13354, "SMC(DO-214AB)").
- Fix: change the MPN to an SMA-package SS34, or change the footprint. An SMA SS34
  is abundant, e.g. LCSC C8678 (MDD, SMA/DO-214AC, $0.035, 5.2M stock, JLC Basic).

### 1.2 D15, D16, D17, D18, D19 (5 placements) - BAT54W wrong package AND wrong pin count

- BOM says `BAT54W-7-F`. That part is **SC-70 / SOT-323, 3 leads**.
- Board footprint is `Diode_SMD:D_SOD-123`, **2 leads**.
- This is a lead-count mismatch, not just a size difference.
- Also genuinely scarce: 65 at Mouser, 0 at DigiKey (3,000 min order), 92 at LCSC,
  and the design needs 5 per board.
- Fix: re-select the part outright. A 2-lead SOD-123 Schottky is the obvious swap.

These five diodes are the soft-power latch isolation diodes, which are exactly the
part the whole two-button power-on scheme depends on. Worth getting right.

---

## 2. Parts that are obsolete, restricted, or unbuyable

| Ref | Part | Status |
|---|---|---|
| SW4 | Alps SKQUCAA010 | **OBSOLETE.** Zero stock, no price, not in the JLCPCB library. Must be replaced. |
| D6-D9 | Nexperia PESD12VL1BA,115 | **"The factory is currently not accepting orders for this product."** Restricted availability, zero stock. SOD-323 second sources exist on LCSC (UMW C2687119, $0.033, 58k stock) but verify clamping/capacitance, these sit on the mic inputs. |
| U12 | TI TPS7A4701RGWR | Zero stock at Mouser, not in the JLCPCB library at all. Single-sourced. This is the ultra-low-noise analog LDO, so substitution is not casual. |
| Q1, Q2 | Nexperia 2N7002,215 | Zero stock at Mouser for that orderable code. Trivially second-sourced (JLC C8545 Basic, 2.1M stock). |
| J6, J7 | "2x13 0.1in pin header", mfr "Generic" | That is a description, not a part number. Nothing can be ordered against it. |
| D3 | SS14-13-F | Could not verify on any distributor through these tools. Well-formed Diodes Inc code, so likely a coverage gap rather than a bad MPN, but unconfirmed. |
| F2 | 1206L200/12WR | Could not verify. Note 2 A hold in a 1206 body is at the top of the 1206L family range, so confirm the code exists. |

Low-stock-at-Mouser but fine at LCSC: U2 (0 vs 53k), U11 (58 vs 7.9k), U9 (69 vs 9.4k),
U1 (163 vs 980). Buy those three from LCSC.

---

## 3. The control height problem, solved

### The geometry

Board top sits 19.5-20 mm above the enclosure floor. Inside height is 35.25 mm.

- Board top to lid **underside**: **15.5 mm**
- Board top to lid **outer face**: **17.5 mm** (lid is 2.0 mm)

### The documentation was wrong

`enclosure-1590XX-desk-study.md` states SW2 (Omron B3F-5150) has a "plunger 17.5 mm
above" the board and is therefore flush with the outer lid face. **It is 7.3 mm.**
Confirmed on Mouser and on the Omron B3F datasheet. The real B3F-5150 falls 8.2 mm
short of even touching the lid underside. Correct that document.

### The root finding

**No tactile switch and no 5-way switch on the market puts its actuator 15.5 mm above
a PCB.** Surveyed the entire LCSC tactile catalogue (12,685 parts): the tallest is
8.5 mm. Omron's tallest 12x12 (B3F-4055) is 7.3 mm, same as the current part.

The ONLY board-mounted control that natively spans this gap is a **long-shaft rotary
encoder**. Everything else needs a cap, a knob, or a lid-mounted carrier.

That reframes the question. The three controls cannot all be solved by picking taller
switches, because taller switches do not exist. They are solved by deciding how to
bridge 15.5 mm.

### Recommended set

**SW3 + SW4 collapse into ONE part.**

| | Part | Detail |
|---|---|---|
| **SW3+SW4** | **Alps RKJXT1F42001** | 4-direction stick + centre push + **rotary encoder**, all in one. 17.0 x 17.0 x 10.5 mm. 30 detents / 15 pulses. Centre push travel 0.3 mm. 9 deg stick throw. THT. **$9.05 qty1, $8.60 qty10, 1,280 in stock at Mouser, Active.** LCSC C160841, 4,832 in stock, $5.21. |

This is literally the "5-way encoder/controller" originally asked for. It replaces the
obsolete SW4 and the $4.91 EC11E15244G1 with a single active, well-stocked part at
roughly the same combined cost, frees board area, and removes one panel hole.

It stands 10.5 mm tall, so it needs a knob about 9-11 mm tall to reach and pass the
lid. Alps designs this family expecting a customer knob, which is how it works in car
head units. 3D printed is fine for a prototype.

**Alternative if you want the encoder and the nav kept separate:**

| | Part | Detail |
|---|---|---|
| SW3 | **Bourns PEC11R-4220F-S0024** | 20 mm flatted 6 mm shaft, with push switch. Body 10 mm above PCB. **$2.29 qty1, $1.85 qty10, 11,274 in stock, Active.** Mouser 652-PEC11R-4220F-S24. Half the price of the Alps EC11E and 10x the stock. Shaft clears the lid with room for a standard knob. Family offers 12.5 / 15 / 17.5 / 20 / 25 mm shafts, so the height can be tuned exactly. |
| SW4 | Alps SKRHACE010 | 4-direction + centre push, 7.5 x 7.5 mm SMD, 1M cycles, $3.44 qty1, 1,287 Mouser / 1,176 LCSC. Short, so still needs a knob or a lid carrier. |

**SW2 (record button)** needs a bridge either way:
- Omron **B3F-4055**, 12 x 12 mm, 7.3 mm, **1,000,000 cycles** (vs 100k on most),
  $0.50 Mouser / $0.129 LCSC, 163k stock. Then a ~10 mm cap.
- Or a lid-mounted panel momentary, wired to the board. More robust, looks right on
  audio gear, no custom cap needed.

### The option worth considering instead

Put all three controls on a **small carrier PCB mounted to the lid underside**, ribbon
to the main board. Every height problem disappears at once, because each switch then
only has to clear 2 mm of lid instead of 15.5 mm. It also lets you use cheap, short,
in-stock parts for everything. Costs one extra small PCB (about $5 for five at PCBWay)
plus a ribbon cable. This is how commercial gear solves exactly this gap.

---

## 4. RESOLVED 2026-09-08: every passive now has an exact MPN plus an alternate

**Before: 54 lines / 184 placements unorderable (77% of the board). Now: 0.**

95 of 97 BOM lines carry a real primary MPN, a second-source AltMPN from a
different manufacturer, and an LCSC code. The only two blanks are TP1/TP2,
which are bare copper test pads, not purchasable parts.

How it was done, so it stays fixed: the placeholders came from three generic
helper functions in `tools/generate_schematic.py`, not from per-part data, so
editing the `.kicad_sch` would have been wiped on the next regeneration. The
fix is a new **`tools/passive_catalog.py`** holding 45 entries (19 resistor 1%,
4 resistor 0.1%, 20 ceramic, 2 electrolytic), each with primary, alternate and
LCSC code. The helpers now look up that table and **raise on an unknown value**
rather than falling back to a placeholder, so a newly added part can never
silently reintroduce an unorderable line.

`Part` gained `alt_mpn` and `lcsc` fields, emitted as AltMPN and LCSC schematic
properties. Hand-off file: `hardware/manufacturing/QuadPreRecorder-BOM-with-alternates.csv`.

Verified after the change: ERC 0 violations, DRC 0 violations, 0 schematic
parity issues, board unchanged.

### Four entries needed an engineering judgement call. Please confirm each.

1. **C12, "1nF 1kV C0G" 0805 — no manufacturer makes this.** Primary keeps the
   1 kV rating and accepts X7R (Yageo CC0805KRX7RCBB102). If C0G matters more
   than 1 kV, use CC0805JKNPOBBN102 (500 V NP0). Genuine 1 kV C0G exists only
   in 1206, which needs a footprint change.
2. **C5/C6, "22uF 10V" 1206 — now the 16 V part** (Taiyo Yuden EMK316BB7226ML-T).
   X7R 22 µF in 1206 tops out at 10 V from Murata, and 10 V is not enough
   headroom if these sit near the boost or battery node.
3. **C10, "47uF 10V" 1206 is X5R, not X7R.** No X7R 47 µF exists in 1206 from
   anyone. Tolerance is also +/-20%.
4. **R30-R33, 90.9k 0.1% — buy from Mouser/DigiKey, not LCSC.** Thinnest line
   on the board. Do NOT accept 91k as a substitute, it is a different value.

Also fixed: **J6/J7** had manufacturer "Generic" and MPN "2x13 0.1in pin
header", which is a description. Now CONNFLY DS1021-2x13SF11-B (LCSC C7430409)
with HCTL PZ254-2-13-Z-8.5 as the alternate.

---

## 4b. Original finding (historical): 54 lines, 184 placements, none orderable

Every resistor and capacitor on the board carries a placeholder, not a part number:
"GRM series X7R/C0G", "RC0603FR series, 1%", "TNPW0603 series, 0.1%", "EEE-FK series".
That is 77% of all placements. PCBWay turnkey sources by MPN, so as written they cannot
quote most of the board. Full resolved table is in the session notes; highlights:

**Errors found while resolving:**

- **C1 placeholder family is wrong.** Panasonic EEE-FK has no 100uF/25V in a 6.3 mm
  can at all; the FK part is an 8.0 mm can with an 8.3 x 8.3 mm land and does not fit
  the `CP_Elec_6.3x5.8` footprint. Use **EEE-FT1E101AP** (FT series, genuinely
  6.3 x 5.8 mm, lower ESR).
- **C12 "1nF 1kV C0G 0805" cannot exist.** No manufacturer makes that combination in
  0805. Pick one: keep 1 kV and accept X7R (Yageo CC0805KRX7RCBB102, $0.054, 310k
  stock), keep C0G and drop to 500 V, or move to 1206.
- **C10 "47uF 10V 1206" must be X5R.** No X7R 47uF exists in 1206 from anyone.
- **C5/C6 22uF at exactly 10 V.** If these sit near the boost or battery node, 10 V is
  not enough headroom. 16 V versions exist.
- **C4/C21-C24**: the canonical Murata 22pF part is NRND. Use GCM1885C2A220JA16D.

**Cost concentration:** twelve 1206 10uF caps are $3.75 of the $11.46 passive total
(33%), and the sixteen 0.1% resistors are $2.65 (23%).

**Cost-optimised passive set: $8.13/board instead of $11.46**, with no spec loss:
swap the Vishay TNPW 0.1% set to the Yageo RT0603BRD 0.1% set (better ratio tracking
too, since all four values then come from one family) and the Murata 1206 10uF to
Samsung CL31B106KAHNNNE.

---

## 5. Not on the BOM at all

None of these appear in the BOM, and several are the most expensive items on the build.

| Item | Est. cost | Note |
|---|---|---|
| Teensy 4.1 | ~$31.50 | Largest single line item. PJRC direct, no distributor carries it under that MPN. |
| MSP3526 3.5in capacitive TFT module | ~$20-30 | LCDWiki / import. Still unverified against the design. |
| LiPo pouch, 3500 mAh class, flat, with PCM | ~$16 | Must be a flat pouch. |
| Hammond 1590XX enclosure | ~$25-30 | |
| Knob for the encoder / multi-control | ~$2-8 | Or printed. |
| Cap for the record button | ~$1 | Or printed. |
| 11 mm standoffs + M3 hardware for the TFT | ~$4 | |
| CAT6 cable and plug for the ambisonic mic | ~$5-10 | The mic side of J2. Nothing on the BOM covers it. |
| Stencil | ~$7 | Order with the PCBs. |
| 4-layer PCB, 138 x 114 mm, qty 5 | ~$60-110 | Needs a real PCBWay quote. |

---

## 6. Cost summary

| Group | Per board |
|---|---|
| Priced BOM lines with real MPNs (34 of 41) | $60.22 qty1 / $46.50 qty10 |
| Passives (54 placeholder lines resolved) | $11.46, or $8.13 optimised |
| Teensy 4.1 | ~$31.50 |
| **Board electronics subtotal** | **~$103 qty1, ~$86 qty10** |
| Plus TFT, battery, enclosure, hardware, cable | ~$75-95 |
| **Rough all-in per unit, qty 1** | **~$180-200** |

Not included: the 7 unpriced lines, PCB fabrication, PCBWay assembly labour and their
sourcing markup.

Caveats: LCSC-sourced lines are reel-break prices, not true one-off quotes. The D1/D10/
D12/D14 and D15-D19 costs are against parts that do not fit the current footprints.
