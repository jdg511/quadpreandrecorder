# QuadPreRecorder Rev A — Analog Front End Pin-Level Review

Scope: U6 (OPA1654AIPW), U4/U5 (CD4053BPW), input network (J2, R6-R33, D6-D9, C13-C20, C25-C28, R14-R17), SW1/PAD_SELECT.
Facts source: `/home/claude/review/pinmap.json` (cross-validated against routed PCB, 0 mismatches).
Datasheets: `/home/claude/review/datasheets/text/opa1654_f35197b75d.txt` (SBOS477B), `/home/claude/review/datasheets/text/cd4053b_804e4504eb.txt` (SCHS047O).
Docs cross-checked: `architecture.md`, `connector-pinout.md`, `reviews/schematic-review.md`, `reviews/datasheet-summary.md`, `reviews/power-path-review.md` (all under `/mnt/user-data/uploads/quadpreandrecorder/hardware/`).

Rail reality check (from pinmap): `/+9V` is the external barrel input after F1/D1 SS14/D2 SMBJ12A (per power-path review, confirmed by D1/D2 on the net). U6 V+ and U4/U5 VDD are on `/+9V`, not a regulated rail. VREF = TLE2426 (U3) output on `/VREF`. With a Schottky in series, the actual rail is ~8.7 V and VREF ~4.35 V; all margin calculations below still pass.

## U6 — OPA1654AIPW quad op amp (TSSOP-14)

| Pin | Net | Expected | Verdict |
|---|---|---|---|
| 1 | /FLU_PRE | OUT A → R30 (90.9k fb), C21 22pF, C25 4.7uF out-coupling, J6.8 | pass |
| 2 | /FLU_FB | IN A− → R30/R26 junction (10k to VREF), C21 | pass |
| 3 | /FLU_PAD | IN A+ ← U4.14 mux common | pass |
| 4 | /+9V | V+ (supply 4.5–36 V spec, ds line 250) | pass (raw input rail; PSRR 3 µV/V typ so acceptable for the op amp itself) |
| 5 | /FRD_PAD | IN B+ ← U4.15 mux common | pass |
| 6 | /FRD_FB | IN B− → R31/R27, C22 | pass |
| 7 | /FRD_PRE | OUT B → R31, C22, C26, J6.13 | pass |
| 8 | /BLD_PRE | OUT C → R32, C23, C27, J6.18 | pass |
| 9 | /BLD_FB | IN C− → R32/R28, C23 | pass |
| 10 | /BLD_PAD | IN C+ ← U5.14 mux common | pass |
| 11 | /GND | V− (single supply) | pass |
| 12 | /BRU_PAD | IN D+ ← U5.15 mux common | pass |
| 13 | /BRU_FB | IN D− → R33/R29, C24 | pass |
| 14 | /BRU_PRE | OUT D → R33, C24, C28, J6.23 | pass |

Gain math (all four channels identical, verified R26-R29 = 10k 0.1% FB→VREF, R30-R33 = 90.9k 0.1% PRE→FB):
- Non-inverting gain = 1 + 90.9k/10k = 10.09 = **20.08 dB**. Matches architecture.md's "20.1 dB".
- C21-C24 22 pF across 90.9k: closed-loop corner **f-3dB = 79.6 kHz**. Droop: −0.27 dB @ 20 kHz, −0.98 dB @ 40 kHz, −3.9 dB @ 96 kHz (Nyquist of 192 kHz). Acceptable for audio; note if flat >40 kHz response is a goal for the 192 kHz ambisonic capture.
- DC: feedback network references /VREF (R26-R29 bottom to VREF); +input DC-biased at VREF via R14-R17 1M (direct path) or R19/R21/R23/R25 33k (pad path) through the ON mux channel. Output DC = VREF (~4.35–4.5 V). Bias current ±10 pA typ/±100 pA max (ds line 336) through 91.7k worst-case source Z → sub-µV, negligible.
- Common mode: VCM range (V−)+0.5 to (V+)−2 (ds line 338) = 0.5–6.7 V at 8.7 V rail; +input sits at ~4.35 V ± ≤0.4 Vpk. Pass.
- Output swing (V−)+0.8 to (V+)−0.8 at 2k load (ds "VOUT" row); load here is 101k feedback + AC-coupled ADC network. Pass.
- Stability: mux is at the (high-Z) input, not the output, so mux Ron causes no gain error or stability issue. Output capacitive load spec is 100 pF (ds CLOAD row); on-board load is 22 pF fb + series 4.7 µF/100 Ω/10 nF ADC network (resistor-isolated) — pass. J6 (analog debug DB-25) hangs PRE outputs on external pins; a long attached cable exceeds 100 pF — docs already warn "keep attached leads short" (connector-pinout.md J6 note). warning (usage, not schematic).

## U4 — CD4053BPW (FLU = section A, FRD = section B; TSSOP-16)

| Pin | Net | Expected | Verdict |
|---|---|---|---|
| 1 | /FRD_AC | B1 (direct path in) | pass |
| 2 | /FRD_ATT | B0 (padded path in, 68k/33k tap) | pass |
| 3 | unconnected (C1) | unused section C | warning (floating analog terminal, see F6) |
| 4 | unconnected (C common) | unused section C | warning (F6) |
| 5 | unconnected (C0) | unused section C | warning (F6) |
| 6 | /GND | INH low = all channels enabled (ds line 287: "Disables all channels") | pass |
| 7 | /GND | VEE — correct single-supply wiring, VEE=VSS (ds line 883: analog signal may swing VEE to VDD; single-supply range 3–20 V, ds line 8) | pass |
| 8 | /GND | VSS | pass |
| 9 | /GND | S(C) select tied low — digital input defined | pass |
| 10 | /PAD_SELECT | S(B) select | pass |
| 11 | /PAD_SELECT | S(A) select | pass |
| 12 | /FLU_ATT | A0 (padded path in) | pass |
| 13 | /FLU_AC | A1 (direct path in) | pass |
| 14 | /FLU_PAD | A common → U6.3 (+in) | pass |
| 15 | /FRD_PAD | B common → U6.5 (+in) | pass |
| 16 | /+9V | VDD | pass |

## U5 — CD4053BPW (BLD = section A, BRU = section B)

| Pin | Net | Expected | Verdict |
|---|---|---|---|
| 1 | /BRU_AC | B1 | pass |
| 2 | /BRU_ATT | B0 | pass |
| 3 | unconnected (C1) | unused | warning (F6) |
| 4 | unconnected (C common) | unused | warning (F6) |
| 5 | unconnected (C0) | unused | warning (F6) |
| 6 | /GND | INH enabled | pass |
| 7 | /GND | VEE = VSS, correct for single supply | pass |
| 8 | /GND | VSS | pass |
| 9 | /GND | S(C) tied low | pass |
| 10 | /PAD_SELECT | S(B) | pass |
| 11 | /PAD_SELECT | S(A) | pass |
| 12 | /BLD_ATT | A0 | pass |
| 13 | /BLD_AC | A1 | pass |
| 14 | /BLD_PAD | A common → U6.10 | pass |
| 15 | /BRU_PAD | B common → U6.12 | pass |
| 16 | /+9V | VDD | pass |

Select-logic level check (the classic CD4053 3.3 V-vs-VDD fail): **not present here**. PAD_SELECT is driven only by SW1 (pin 1 = /GND, pin 2 = /PAD_SELECT common, pin 3 = /+9V), i.e. full 0 V/9 V rail swing. Datasheet VIH min = 7 V at VDD = 10 V (ds VIH table); 9 V drive satisfies it. The Teensy does **not** drive this net — it senses it through R42 100k → /PAD_SENSE with R43 47k to GND and C33 100nF: 9 V × 47/147 = 2.88 V (2.78 V after the SS14 drop) at U8.32 (D32), safe for 3.3 V logic. During switch break-before-make transit, PAD_SELECT is held low through R42+R43 (147k to GND), so the CMOS input never floats. Pass. Residual items: F4 (J7 exposure) and F7 (shorting-type switch, manual_review).

Logic truth: PAD_SELECT low (SW1 toward GND) selects A0/B0 = ATT nets = **pad engaged when low**; high selects A1/B1 = AC nets = direct. (0 = VSS selects channel "0" per ds line 882 logic convention and Table 7-1.) Confirm silkscreen/panel labeling matches — polarity is a labeling question, not an electrical one: manual_review.

## Input network (per channel, FLU shown; FRD/BLD/BRU verified identical)

| Element | Nets (pinmap) | Expected | Verdict |
|---|---|---|---|
| J2.1 | /FLU_RAW | capsule signal (matches connector-pinout.md) | pass |
| J2.6-9 | /GND | capsule returns | pass |
| J2.5 | /CHASSIS | shield; CHASSIS↔GND via R4 1M ∥ C12 1nF, R5 0R link | pass |
| D6 | /FLU_RAW ↔ /CHASSIS | ESD clamp at connector, dumps to chassis before signal ground | pass |
| R10 100R | /FLU_RAW → /FLU_MIC | RF series | pass |
| R6 4.7k | /+9V → /FLU_MIC | electret bias | **fail — bias taken from raw, unfiltered input rail (F1)** |
| C13 100pF C0G | /FLU_MIC ↔ /CHASSIS | RF bypass (corner ~1 MHz with 4.7k∥Zmic) | pass |
| C17 4.7uF | /FLU_MIC → /FLU_AC | AC coupling; HPF ~0.35 Hz into 91.7k load | pass |
| R14 1M | /FLU_AC → /VREF | DC bias for direct path | pass |
| R18 68k 0.1% | /FLU_AC → /FLU_ATT | pad top | pass |
| R19 33k 0.1% | /FLU_ATT → /VREF | pad bottom (also DC bias for pad path) | pass |
| C25 4.7uF | /FLU_PRE → /FLU_ADC_SRC → R34 100R → /FLU_ADC (U7.3) | output coupling to ADC | pass (ADC side out of scope; R38 100k bleed to GND noted at boundary) |

ESD sanity: PESD12VL1BA is bidirectional, VRWM = 12 V. Worst-case steady DC on RAW = full bias rail ≈ 8.7 V (mic unplugged, R6 pulls MIC high; R10 carries no current) plus small audio swing → ≥3 V margin below VRWM, no clamp leakage into the signal. Connection to CHASSIS (not GND) is deliberate and consistent with the grounding strategy in architecture.md; the strike return relies on the DE-9 shell/enclosure bond and R5 0R. Pass.

Pad math (computed from pinmap values):
- Tap ratio R19/(R18+R19) = 33/101 = 0.3267 → **−9.72 dB**, and because ATT is a tap on the same AC node, the pad-relative attenuation is exactly −9.72 dB **independent of source impedance** (verified for Rs = 0, 4.8k, 1.6k). Nominal target "−10 dB": −9.72 dB nominal is a 0.28 dB shortfall — consistent with prior schematic-review.md, treat as accepted design value. warning (cosmetic).
- Absolute insertion loss of the network in direct mode: −0.15 to −0.44 dB depending on capsule output impedance (AC node loaded by 1M ∥ 101k = 91.7k).
- Channel matching: 0.1% resistors → pad match ~±0.017 dB; mux ΔRon (≤10 Ω between channels at 10 V, ds ΔRON row) into the op amp's TΩ input is irrelevant. Pass.
- Mux Ron at 9 V ≈ 200 Ω typ/≈400–500 Ω max (interpolating ds rON 5 V/10 V rows): in series with +input, zero gain error; adds ~1.8 nV/√Hz — negligible vs the 4.7k bias resistor's 8.8 nV/√Hz. Pass.
- Mux channel leakage (ds OFF/ON leakage table: ±0.3 nA typ 25°C, ±100 nA max 25°C, ±300–1000 nA max 85–125°C) through the 91.7k direct-path DC source impedance: worst-case +input shift 9 mV (25°C max) to 28 mV (85°C max) → 93–280 mV output DC offset. Output is AC-coupled to the ADC (C25), so this only trims headroom (~3.7 V available). Typical parts: negligible. warning (low).
- Switching transient: break-before-make float of the +input during pad toggling will click; SW1 is a manual, occasional control. Info.
- CD4053 "Special Considerations" (ds line ~1520, signals applied without VDD): signals derive from the same /+9V rail as VDD, so no power-off signal-injection condition exists. Pass.

## Findings

| # | Severity | Confidence | Item |
|---|---|---|---|
| F1 | high | medium | **Electret bias resistors R6-R9 (pin 1) connect directly to /+9V — the raw, post-fuse/post-Schottky external barrel-jack rail — with no RC/LC bias filter.** The same node is the TPS62160 (U1.2 VIN) buck input, which draws pulsed input current. Rail hum/noise reaches each capsule attenuated only by Zmic/(4.7k+Zmic) ≈ −10 dB (Zmic ≈ 2.2k) to −3 dB (Zmic ≈ 10k), then gets +20.1 dB in U6: net rail-noise gain up to roughly +10 to +17 dB to the preamp output in the audio band. C13-C16 (100 pF, corner ~1 MHz) and C1/C2 bulk do not help in-band. Electret bias has essentially zero PSRR by construction — a dedicated filter (e.g. 100–470 Ω + ≥100 µF per rail, or one shared filtered bias node) is standard. The task brief and architecture describe the bias as coming from "+9V (filtered)"; the pinmap shows no such filter exists. Confidence is medium only because a very quiet external 9 V supply would mask it; with a generic SMPS wall adapter this will be audible. Evidence: pinmap R6-R9 pin1 = /+9V; /+9V membership list (U1 VIN, D1 SS14, D2 SMBJ12A, C1/C2); power-path-review.md "Rail noise ... require bench measurements". |
| F2 | low | high | Pad is −9.72 dB nominal, not −10 dB (33k/(68k+33k)); constant vs source impedance. Matches prior review's stated value; if exactly −10 dB is wanted, e.g. 68k→69.8k or 33k→31.6k (E96, 0.1%) gives −10.06/−9.99 dB. Evidence: R18-R25 values in pinmap; math above. |
| F3 | low | high | U6 closed-loop bandwidth is 79.6 kHz (22 pF ∥ 90.9k): −0.98 dB @ 40 kHz, −3.9 dB @ 96 kHz. Fine for audio, but the 192 kHz capture chain is not flat in its top octave; halve C21-C24 to 10 pF (159 kHz) if ultrasonic flatness matters. Evidence: C21-C24 = 22pF C0G across R30-R33 in pinmap. |
| F4 | medium | high | /PAD_SELECT (0/9 V logic) is exposed on J7.21, the DIGITAL debug DB-25, surrounded by 3.3 V nets and documented as "pad select logic". Probing/driving it with 3.3 V tooling: 9 V can damage the external device, and an external driver forced against SW1 (which connects the net directly to a rail with no series resistance) is a hard short. 3.3 V drive also cannot meet VIH(min) = 7 V @ VDD 10 V. Recommend a series resistor at J7.21 or moving the signal to J6 with clear labeling. Evidence: pinmap /PAD_SELECT members (J7.21, SW1.2, U4.10/11, U5.10/11); CD4053 ds VIH table; connector-pinout.md J7 table. |
| F5 | low | medium | CD4053 channel leakage into the 91.7k DC source impedance of the direct path can produce up to ~0.28 V output DC offset at 85°C worst case (~93 mV at 25°C max spec; negligible typical). Headroom-only effect since C25-C28 block DC to the ADC. Evidence: ds ON/OFF leakage table (±100 nA max 25°C, ±300 nA 85°C); R14 1M ∥ (R18+R19). |
| F6 | low | high | Unused mux section C on both U4 and U5 has all three analog terminals (pins 3, 4, 5) floating. Digital select S(C) is properly grounded (so C0 is connected to the floating common), and floating transmission-gate terminals are not a reliability hazard, but tying pins 3/4/5 to VREF or GND is standard practice to avoid a drifting node capacitively coupled (CIOS 0.2 pF) to active channels. Evidence: pinmap U4/U5 pins 3-5 = unconnected; ds feedthrough capacitance row; ds figure note "connect all unused inputs to either VDD or VSS" (digital context, lines 1430/1455). |
| F7 | low | manual_review | SW1 shorts /+9V to /GND through its own contacts if the fitted part is a shorting (make-before-break) type, since both throws go directly to rails with zero series resistance. The specified C&K OS102011MS2Q is non-shorting per vendor data (not in the provided datasheet set — could not verify here). A safer topology is pull-up + switch-to-ground. Evidence: pinmap SW1 (1=/GND, 2=/PAD_SELECT, 3=/+9V). |
| F8 | info | high | Pad polarity: PAD_SELECT low → A0/B0 (ATT, padded) selected; high → direct. Verify panel/silk labeling of SW1 matches ("pad engaged" = switch toward GND). Electrical wiring itself is correct. Evidence: ds line 882 (0 = VSS, 1 = VDD selects channel); pinmap A0/A1 net assignments. |

Everything else checked passes: U6 supply/CM/output/DC operating point; U4/U5 VDD/VSS/VEE single-supply wiring (VEE=VSS=GND is correct per ds — 3–20 V single-supply range, analog swing VEE..VDD covers the 4.35 V ± signal); INH grounded; select logic levels; DC bias paths through both mux positions; ESD diode standoff (12 V vs ≤8.7 V); AC-coupling corners (0.35 Hz in, ~2 Hz out); channel-to-channel component identity across all four channels; J2 pinout matches connector-pinout.md exactly.

Not verified (out of reach of provided data): actual electret capsule current/impedance (affects F1 magnitude and bias operating point), SW1 shorting/non-shorting contact type (F7), silkscreen labels, and the PCM1864 side of the ADC boundary (R38-R41 100k bleeds interact with the ADC's internal input bias — U7 was out of scope).
