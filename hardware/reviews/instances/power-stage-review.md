# QuadPreRecorder Rev A — Power Stage Pin-Level Review

Scope: U1 TPS62160DGK buck, U2 TPS7A2033PDBV LDO, U3 TLE2426ID rail splitter, and the
input power path (J1, F1, D1, D2, D3, L1, input/output caps).
Facts source: `/home/claude/review/pinmap.json` (authoritative, PCB-cross-validated, 0 mismatches).
Datasheets: plain-text extracts under `/home/claude/review/datasheets/text/`
(tps62160_542446e606.txt = SLVSAM2E, tps7a20_28ebbbb298.txt = SBVS338H,
tle2426_79d7817df7.txt = SLOS098D). Prior claims in
`/mnt/user-data/uploads/quadpreandrecorder/hardware/reviews/` were re-verified, not trusted.

Verdict legend: **pass** / **fail** / **warning** / **manual_review**.

---

## U1 — TPS62160DGK (9 V → 5 V buck, VSSOP-8 "DGK")

### Pin table

Datasheet "Pin Functions" (SLVSAM2E p.4): PGND=1, VIN=2, EN=3, AGND=4, FB=5, VOS=6, SW=7, PG=8;
"The exposed thermal pad is available with the DSG package only, not with DGK package."

| Pin | Name | Net | Expected (datasheet) | Verdict |
|---|---|---|---|---|
| 1 | PGND | /GND | Power ground | pass |
| 2 | VIN | /+9V | Supply, 3–17 V rec (abs max 20 V) | pass |
| 3 | EN | /+9V | High = enabled; abs max VIN+0.3 | pass (always-on, tied to VIN) |
| 4 | AGND | /GND | Analog ground | pass |
| 5 | FB | /BUCK_FB | Adjustable version: resistive divider; regulated to 800 mV | pass |
| 6 | VOS | /+5V | "Output voltage sense pin and connection for the control loop" — must connect to VOUT | pass |
| 7 | SW | /BUCK_SW | "Connect inductor between SW and output capacitor" — L1 pin 1 | pass |
| 8 | PG | /BUCK_PG | Open drain, "requires pull-up resistor" | pass (R3 100 kΩ to /+5V) |

No unused pins; DGK has no thermal pad, so the pad-to-AGND rule does not apply.

### FB divider math (datasheet Equation 6 context, section 9.2.2.2)

- Datasheet: "The voltage at the FB pin is regulated to 800 mV" (also Electrical
  Characteristics: "VREF Internal reference voltage 0.8 V").
- R1 = 680 kΩ (/+5V → /BUCK_FB), R2 = 130 kΩ (/BUCK_FB → /GND).
- VOUT = 0.8 V × (1 + 680/130) = 0.8 × 6.2308 = **4.985 V** (−0.31 % vs 5.00 V target). **pass**
- Constraint "the value of R2 should not exceed 400 kΩ" (divider current ≥ 2 µA):
  130 kΩ → I(div) = 0.8 V/130 k = 6.15 µA ≥ 2 µA. **pass**
- Feed-forward: C4 = 22 pF C0G across R1 (/+5V ↔ /BUCK_FB). Datasheet 9.2.2.6: internal
  25 pF VOS–FB cap exists; "An external feed-forward capacitor can also be added" and the
  device "is stable without the pole and zero being in a particular location". **pass**
- FB-open failure mode noted in datasheet (VOS clamps ≈7.4 V) — not a schematic issue.

### External parts

| Item | Fitted | Datasheet requirement | Verdict |
|---|---|---|---|
| Input cap | C3 10 µF 25 V + C2 100 nF (on /+9V), C1 100 µF 16 V bulk | 9.2.2.5.2: "For most applications, 10 µF is sufficient and is recommended" | pass |
| Output cap | C5 + C6 = 2 × 22 µF 10 V (on /+5V) | 9.2.2.5.1: "recommended value for the output capacitor is 22 µF"; Table 2 LC matrix: 2.2 µH checked with 22 µF and 47 µF | pass (44 µF nominal; with ~50 % DC-bias derating at 5 V still lands inside the checked 22–47 µF band) |
| Inductor | L1 2.2 µH "1.5 A" ASPIAIG-F4020-2R2M | Table 2: 2.2 µH is the standard/recommended value; Table 3 lists 2.2 µH parts rated 1.3–1.9 A | pass (see sat math below) |
| Soft start | none external | Internal soft start ("the device starts switching after a delay… smooth" — Enable/soft-start section); no SS pin exists | pass |
| PG pull-up | R3 100 kΩ to /+5V | Table 4 reference design uses "R3 100 kΩ"; PG abs max 7 V (5 V OK), sink ≤10 mA (50 µA actual) | pass |

### Ratings math

- Duty ≈ 5/9 = 0.556; t_on ≈ 0.556/2.25 MHz = 247 ns >> 80 ns minimum on-time. pass
- Inductor ripple (Eq. 7/8): ΔIL = VOUT×(1−VOUT/VIN)/(L×fSW) = 5×0.444/(2.2 µH×2.25 MHz)
  = **0.449 A** p-p. Peak at worst-case 0.8 A load: IL(max) = 0.8 + 0.449/2 = **1.02 A**.
  With the datasheet's "+20 % margin" → 1.23 A required saturation ≤ 1.5 A schematic
  rating (Abracon F4020-2R2M molded parts are typically rated far higher; vendor sheet not
  provided). pass. Peak 1.02 A is also below ILIMF(min) 1.45 A — no current-limit hits.
- Load budget on /+5V: Teensy 4.1 via D3 (≈100–500 mA) + TFT/backlight (≈100–150 mA)
  + TPA6132A2 (tens of mA) + U2 LDO (≈35 mA) ≈ 0.75–0.85 A worst case < 1 A rated. pass,
  thin margin at absolute worst case.
- **Thermal (warning):** DGK RθJA = **184.3 °C/W** (Thermal Information table; DSG is
  61.8 °C/W). At 0.8 A/5 V from 9 V, η ≈ 90 % → ≈0.44 W total loss, ≈0.35–0.4 W in the IC
  → **ΔTJ ≈ 65–74 °C**. TJ ≈ 100 °C at 25 °C ambient, approaching the 125 °C recommended
  limit inside a warm enclosure on a 2-layer board. Fine at typical ~0.5 A
  (ΔT ≈ 40–45 °C).
- Abs-max cross-check: VIN abs max 20 V vs SMBJ12A max clamp 19.9 V (600 W pulse) —
  0.1 V margin, transient-only, acceptable for a regulated 9 V source (see power path).

### U1 findings

| # | Severity | Confidence | Finding | Evidence |
|---|---|---|---|---|
| U1-1 | medium | high | DGK (no thermal pad, RθJA 184.3 °C/W) runs ≈65–75 °C junction rise at the 0.8 A worst-case load; DSG package or generous copper/via stitching would restore margin | SLVSAM2E §7.4 Thermal Information ("DGK (VSSOP) … 184.3 °C/W"); load budget above |
| U1-2 | low | medium | VIN abs max 20 V vs TVS max clamp 19.9 V leaves 0.1 V margin during a full-rated surge (transient only, regulated supply expected) | SLVSAM2E §7.1 Abs Max ("VIN –0.3 20 V"); Littelfuse SMBJ12A VC(max) 19.9 V (rating not in provided text set — industry standard value) |

Everything else on U1: **pass**. Computed output = 4.985 V.

---

## U2 — TPS7A2033PDBV (5 V → 3.3 V analog LDO, SOT-23-5 "DBV")

### Pin table

Datasheet "Pin Functions: X2SON, SOT-23" (SBVS338H p.4): SOT-23: IN=1, GND=2, EN=3, N/C=4, OUT=5.

| Pin | Name | Net | Expected (datasheet) | Verdict |
|---|---|---|---|---|
| 1 | IN | /+5V | Supply 1.6–6.0 V rec, 6.5 V abs max — fed from buck 5 V (NOT 9 V; 9 V would violate abs max) | pass |
| 2 | GND | /GND | Common ground | pass |
| 3 | EN | /+5V | High = enabled; VEN 0–6.0 V; internal 500 kΩ pulldown | pass (always-on) |
| 4 | N/C | unconnected | "No internal electrical connection" | pass (open OK) |
| 5 | OUT | /+3V3_A | Regulated output; low-ESR cap required | pass |

### External parts and ratings

- CIN: C7 1 µF 10 V on /+5V. Rec. Operating Conditions: CIN 1 µF nominal
  ("effective value of 0.47 µF minimum is recommended"). **pass**
- COUT: C8 4.7 µF at OUT plus downstream on /+3V3_A: C42 10 µF, C55 10 µF, C41/C54/C64
  100 nF → ≈25 µF total. Requirement: "Effective output capacitance of 0.47 µF minimum and
  200 µF maximum is required for stability", ESR ≤ 100 mΩ (ceramics). **pass**
- Load: PCM1864 AVDD (U7-8) + PCM5102A AVDD/CPVDD (U9-8/1) ≈ 30–40 mA << 300 mA rated. **pass**
- Dropout: VDO = **145 mV max at 300 mA** for 2.5 V ≤ VOUT ≤ 5.5 V, DBV package
  (Electrical Characteristics table). Headroom = 5.0 − 3.3 = 1.7 V >> 145 mV; even the
  4.985 V computed rail leaves 1.685 V. **pass**
- Note: U2 IN is on /+5V (buck output), confirmed from pinmap — it does not see 9 V.
  Sequencing: output tracks buck rise via internal soft start; EN=IN needs no sequencing.

### U2 findings

None. All checks **pass**.

---

## U3 — TLE2426ID (9 V → 4.5 V VREF rail splitter, SOIC-8 "D")

### Pin table

Datasheet "D, JG, OR P PACKAGE (TOP VIEW)" (SLOS098D p.3): OUT=1, COMMON=2, IN=3, NC=4,
NC=5, NC=6, NC=7, NOISE REDUCTION=8; "NC − No internal connection".

| Pin | Name | Net | Expected (datasheet) | Verdict |
|---|---|---|---|---|
| 1 | OUT | /VREF | VO = VI/2 = 4.5 V | pass |
| 2 | COMMON | /GND | Reference/return terminal | pass |
| 3 | IN | /+9V | 4–40 V input range ("full input range of 4 V to 40 V") | pass |
| 4–7 | NC | unconnected | No internal connection | pass |
| 8 | NOISE REDUCTION | /VREF_NR | Optional CNR; noise spec "CNR = 1 µF → 30 µV rms" | pass |

### External parts and loading

- CNR: C9 = 1 µF (/VREF_NR → /GND = COMMON). Matches the characterized condition
  ("Output noise voltage, rms f = 10 Hz to 10 kHz, CNR = 1 µF, 30 µV"; noise-reduction
  impedance 110 kΩ). Correct return node (COMMON = GND). **pass**
- Output load capacitance: **C10 47 µF + C11 100 nF directly on /VREF** → **manual_review**
  (finding U3-1 below).
- DC loading on /VREF: R14–R17 1 MΩ bias, R19/R21/R23/R25 33 kΩ 0.1 %, R26–R29 10 kΩ 0.1 %
  (preamp/pad reference networks), J6 debug pin 4. Bias-network currents are µA-to-sub-mA
  and largely signal-symmetric; well inside sink/source capability (short-circuit currents
  26 mA sink / 47 mA source at VO = 5 V table conditions). **pass**
- Supply current ≤ 400 µA, no thermal concern. **pass**

### U3 findings

| # | Severity | Confidence | Finding | Evidence |
|---|---|---|---|---|
| U3-1 | medium | medium | 47 µF (C10) + 100 nF (C11) hang directly on OUT. The datasheet dedicates Figure 17 "STABILITY RANGE — OUTPUT CURRENT vs LOAD CAPACITANCE (VI = 5 V, TA = 25 °C)" with explicit "Unstable"/"Stable" regions across CL = 10⁻⁶–10² µF — i.e., the TLE2426 is NOT unconditionally stable into capacitive loads, and there is a documented unstable band at low output currents. The Unstable/Stable boundary values are graphical and unreadable in the text extract, so 47 µF cannot be confirmed to sit in the stable large-CL region (and the curve is given for VI = 5 V, not 9 V). If VREF oscillates, it modulates all four preamp/pad/ADC bias chains. Verify against the PDF figure or bench-check; if marginal, add a small series R (e.g., a few Ω) or resize C10, and reconsider whether C11 alone (0.1 µF) would land in the unstable band if C10 is ever DNP'd. | SLOS098D Figure 17 text block (lines ~1128–1140 of tle2426_79d7817df7.txt: "STABILITY RANGE / OUTPUT CURRENT vs LOAD CAPACITANCE … VI = 5 V, TA = 25 °C, Unstable / Stable"); pinmap: C10/C11 pin 1 = /VREF. Prior power-path-review.md asserted this bypassing as simply "fitted" — that claim is unverified. |

---

## Input power path — J1, F1, D1, D2, D3, L1, bulk caps

Topology from pinmap: J1.1 (center pin) → /+9V_IN → F1 (750 mA PTC 1206) → /+9V_FUSED →
D1 SS14 (A on /+9V_FUSED, K on /+9V) → /+9V rail; D2 SMBJ12A across /+9V ↔ /GND;
C1 100 µF 16 V + C3 10 µF 25 V + C2 100 nF on /+9V. J1.2/J1.3 = /GND.

| Check | Result | Verdict |
|---|---|---|
| Polarity (center-positive) | J1 pin 1 (center pin, PJ-102AH) → +9V_IN; sleeve/switch pins 2/3 → GND | pass |
| Reverse-input protection | Series Schottky D1: anode on fused input, cathode on +9V — blocks reverse; SS14 Vrrm 40 V >> 9 V reverse | pass (≈0.35–0.45 V drop; buck VIN ≈ 8.6 V still ≥ VOUT+1 V and ≥ 3 V min) |
| D1 current rating | SS14 1 A avg vs ≈0.5 A worst-case input current; ≈0.2 W in SMA | pass (rating from common SS14 spec; vendor sheet not provided) |
| PTC F1 sizing | Worst-case input current: P(5V) ≈ 4 W, η ≈ 0.9 → 0.49 A at 9 V, + ≈15 mA of direct 9 V loads (OPA1654 ≈8 mA, TLE2426 ≤0.4 mA, electret bias ≈2–4 mA, CD4053 ≈0) → ≈**0.51 A** vs 0.75 A hold. 32 % margin at 23 °C; PTC hold current derates with ambient (≈0.6 A at 50 °C for typical 1206L parts) → margin shrinks to ≈15 % in a warm enclosure | pass / warning-low |
| PTC voltage rating | 1206L075 family Vmax typically 13.2 V ≥ 9 V; but no PTC datasheet provided — trip current, Vmax, and derating curve unverified | manual_review |
| TVS standoff | SMBJ12A: 12 V standoff ≥ 9 V regulated input; VBR ≈ 13.3–14.7 V | pass (values are standard Littelfuse specs; SMBJ datasheet not in provided text set) |
| TVS polarity/symbol | D2 drawn as **KiCad `Device:D_TVS` — the non-polarized/bidirectional symbol (pins A1_1, A2_2)** but MPN is unidirectional SMBJ12A (schematic lines 9082–9118). Electrically it lands correctly only via convention: footprint D_SMB pad 1 (cathode band) = /+9V. The schematic itself carries no polarity information | warning (finding PP-1) |
| TVS placement | D2 clamps on /+9V, downstream of F1 **and D1**. Acceptable (F1 limits sustained fault current; D1 blocks negative transients), but positive surge current must transit D1 (SMBJ12A rated Ipp ≈ 30 A vs SS14 IFSM ≈ 40 A 8.3 ms half-sine — survivable for 10/1000 µs, thin for 8/20 µs). Clamping at the jack side (/+9V_FUSED) would relieve D1 | warning-low (finding PP-2) |
| Bulk cap ratings | C1 = 100 µF **16 V** on /+9V: 1.78× derating vs 9 V (fine), but SMBJ12A max clamp 19.9 V exceeds 16 V during a full-rated surge (transient) | warning-low (finding PP-3) |
| Downstream abs-max vs clamp | U1 VIN 20 V, CD4053B 20 V ("Supply Voltage V+ to V− … –0.5 20 V", cd4053b txt line 360), OPA1654 36 V — all ≥ 19.9 V max clamp | pass |
| D3 Teensy feed | SS14 from /+5V to /TEENSY_VIN (K on Teensy side): isolates USB back-feed; Teensy VIN ≈ 5.0 − 0.35 ≈ 4.65 V, inside 3.6–5.5 V; 1 A ≥ 0.5 A load; C46 10 µF local | pass (prior review's USB dual-supply caution still applies — module-internal, not a PCB fix) |
| L1 | 2.2 µH between /BUCK_SW and /+5V, correct topology ("Connect inductor between SW and output capacitor"); sat margin computed under U1 | pass |

### Power path findings

| # | Severity | Confidence | Finding | Evidence |
|---|---|---|---|---|
| PP-1 | low | high | D2 (unidirectional SMBJ12A) is drawn with the non-polarized `Device:D_TVS` symbol (A1/A2 pins) — no schematic-level polarity control; correctness depends on D_SMB pad-1-cathode convention (pad 1 = /+9V, which is the right way). Change to a polarized TVS symbol or specify bidirectional SMBJ12CA to remove the ambiguity | QuadPreRecorder.kicad_sch lines 9082 (`lib_id "Device:D_TVS"`), 9095/9115 (Value/MPN "SMBJ12A"); pinmap D2: A1_1 = /+9V, A2_2 = /GND |
| PP-2 | low | medium | TVS clamps downstream of series diode D1, so surge current passes through the SS14 and the clamp does not protect the fused input node; move to /+9V_FUSED (or accept, given regulated-adapter use) | pinmap: D2 on /+9V; D1 A = /+9V_FUSED, K = /+9V |
| PP-3 | low | medium | C1 100 µF rated 16 V can transiently see up to the SMBJ12A clamp (≈19.9 V worst case) during a max-rated surge; 25 V part removes the concern | pinmap C1 "100uF 16V" on /+9V; SMBJ12A VC(max) standard spec |
| PP-4 | low | medium | F1 750 mA PTC hold margin over the ≈0.51 A worst-case input current thins to ≈15 % at elevated enclosure temperature (PTC derating); no nuisance trips expected at typical load, but verify the specific 1206L075 derating curve | Load math above; PTC datasheet not provided |

---

## Summary

- **fail:** none.
- **Pin-level:** all 21 IC pins of U1/U2/U3 match their datasheet pin functions and
  voltage/abs-max constraints; all unused-pin rules satisfied.
- **Computed:** buck output 4.985 V (0.8 V FB ref × (1+680k/130k)); inductor peak 1.02 A
  worst case (0.449 A p-p ripple); LDO headroom 1.7 V vs 145 mV max dropout; VREF = 9/2 = 4.5 V.
- **Top items to act on:** U3-1 (VREF load-capacitance stability vs Figure 17 — verify
  graphically/bench), U1-1 (DGK thermal margin at sustained ≥0.8 A).

### Not verifiable from provided facts
Vendor specs for F1 (1206L075 hold/trip/Vmax/derating), L1 (ASPIAIG-F4020-2R2M saturation
current/DCR), D1/D3 (SS14), D2 (SMBJ12A VBR/VC), and J1 current rating — no datasheets in
the provided set; standard catalog values were assumed and flagged where they matter.
The TLE2426 Figure 17 stability-region boundary and all graphical curves (dropout plots,
efficiency curves) are images absent from the text extracts. Actual load currents
(Teensy/TFT/DAC) are architecture estimates, not measurements. Ceramic-capacitor DC-bias
derating assumed typical (~50 % at rated-voltage/2).
