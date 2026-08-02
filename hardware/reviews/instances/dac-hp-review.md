# Monitoring output section review — U9 PCM5102A, U10 TPA6132A2, RV1, J4, J5 (QuadPreRecorder Rev A)

Source of record: `/home/claude/review/pinmap.json` (cross-validated vs routed PCB, 0 mismatches).
Datasheets: `/home/claude/review/datasheets/text/pcm5102a_f1323e62dd.txt` (SLAS859C), `/home/claude/review/datasheets/text/tpa6132a2_0e8fad4997.txt` (SLOS597B).
Cross-checked against `hardware/architecture.md`, `connector-pinout.md`, and the three prior reviews in `hardware/reviews/` (re-verified, not trusted).

Verdicts: **pass** / **fail** / **warning** / **manual_review**.

---

## U9 — PCM5102APW (TSSOP-20), stereo I2S DAC

| Pin | Name | Net | Expected (datasheet) | Verdict |
|---:|---|---|---|---|
| 1 | CPVDD | /+3V3_A | Charge pump supply, "must be 3.3 V" (Table 12); 3.1–3.46 V range | pass |
| 2 | CAPP | /DAC_CAPP → C51.1 | Flying cap positive terminal; typical app 2.2 uF. C51 = 2.2 uF | pass |
| 3 | CPGND | /GND | Charge pump ground | pass |
| 4 | CAPM | /DAC_CAPM → C51.2 | Flying cap negative terminal; C51 = 2.2 uF across CAPP–CAPM | pass |
| 5 | VNEG | /DAC_VNEG → C52 (2.2 uF) to GND | "Negative charge pump rail terminal for decoupling, –3.3 V"; typical app 2.2 uF | pass |
| 6 | OUTL | /DAC_L → RV1.1 (gang 1 end) and R62 100R → /LINE_L → J4.T | 2.1 Vrms GND-centered line driver; min load 1 kΩ; TI recommended output filter = 470 Ω series + 2.2 nF shunt (EC note 3, app circuit p. line-out figure) | warning (no RC filter; see F2, F4) |
| 7 | OUTR | /DAC_R → RV1.4 (gang 2 end) and R63 100R → /LINE_R → J4.R | Same as OUTL | warning (F2, F4) |
| 8 | AVDD | /+3V3_A | Analog supply, must be 3.3 V. Decoupling near U9: C54 100nF (8.3 mm), C64 100nF (4.9 mm), C55 10uF (11 mm) on +3V3_A | pass |
| 9 | AGND | /GND | Analog ground; datasheet layout section allows shared AGND/DGND | pass |
| 10 | DEMP | /GND | De-emphasis: Off (Low) / On (High). Low = off — correct for 48 kHz monitor path | pass |
| 11 | FLT | /GND | Filter select: Normal latency (Low) / Low latency (High). Low = normal FIR | pass |
| 12 | SCK | /GND | "If BCK and LRCK start correctly while SCK remains at ground level for 16 successive LRCK periods, then the internal PLL starts, automatically generating an internal SCK from the BCK reference" (§9.3.5.3). Grounded SCK = intended 3-wire PLL mode. 48 kHz at 32fs (1.536 MHz) or 64fs (3.072 MHz) both in PLL Table 11 | pass |
| 13 | BCK | /DAC_BCLK_IC ← R57 33R ← /DAC_BCLK ← U8 pin 4 (BCLK2) + J7.8 | I2S bit clock from Teensy I2S2, series damping | pass |
| 14 | DIN | /DAC_DIN_IC ← R58 33R ← /DAC_DIN ← U8 pin 2 (OUT2) + J7.10 | I2S data from Teensy | pass |
| 15 | LRCK | /DAC_LRCLK_IC ← R59 33R ← /DAC_LRCLK ← U8 pin 3 (LRCLK2) + J7.9 | I2S word clock from Teensy | pass |
| 16 | FMT | /GND | Audio format: I2S (Low) / Left-justified (High). Low = I2S, matches Teensy I2S2 | pass |
| 17 | XSMT | /DAC_MUTE_IC ← R61 100R ← /DAC_MUTE (U8 pin 34, J7.11); R60 10k pull-up to /+3V3_D | "Soft mute (Low) / soft un-mute (High)". Controllable from Teensy = good. But pull-up direction makes default state UN-muted; XSMT edges also require tr/tf < 20 ns (§8.7) | warning (F1) |
| 18 | LDOO | /DAC_LDO → C53 (1 uF) to GND | "Should be used with a 0.1-µF decoupling cap" (Table 12); typical app shows 0.1 uF | manual_review (F5) |
| 19 | DGND | /GND | Digital ground | pass |
| 20 | DVDD | /+3V3_D (Teensy 3V3 output rail) | 1.8 V or 3.3 V; 3.3 V sets 3.3 V I/O — matches Teensy logic. Local C56 100nF (7.5 mm); 10 uF bulk (C45) is on the rail at U7, not local to U9 | pass |

I2S pin-to-Teensy mapping verified against Teensy 4.1 I2S2 (BCLK2=4, LRCLK2=3, OUT2=2): correct.

## U10 — TPA6132A2RTE (WQFN-16 + EP), DirectPath headphone amp

| Pin | Name | Net | Expected (datasheet) | Verdict |
|---:|---|---|---|---|
| 1 | INL- | /HP_IN_L ← C57 680nF ← /HP_VOL_L (RV1.2 wiper) | "Left input for single-ended signals"; input coupling cap recommended: "Use input coupling capacitors to ensure inaudible turn-on pop" (§7.3.2). Zin at 0 dB = 19.8 kΩ → fc ≈ 11.8 Hz. Good | pass |
| 2 | INL+ | /GND | "Connect to ground for single-ended input" (pin table, and §"For single-ended input signals, connect INL+ and INR+ to ground") — direct ground is per datasheet, no cap required | pass |
| 3 | INR+ | /GND | Same as INL+ | pass |
| 4 | INR- | /HP_IN_R ← C58 680nF ← /HP_VOL_R (RV1.5 wiper) | Same as INL- | pass |
| 5 | OUTR | /HP_OUT_R → R66 10R → /HP_JACK_R → J5.R | DirectPath output, GND-centered, "requires no output dc-blocking capacitors" — none present, correct. 10R series costs ~2 dB into 16 Ω but is benign | pass |
| 6 | G0 | /+3V3_D (static high) | Gain select. VIH ≥ 1.3 V, abs max VDD+0.3 = 5.3 V, so 3.3 V on a 5 V-supplied part is legal | pass |
| 7 | G1 | /GND | With G0=high, G1=low: gain = 0 dB, Zin = 19.8 kΩ (EC table: "G0 ≥ 1.3 V, G1 = 0 V, (0 dB)") | pass |
| 8 | HPVSS | /HP_VSS → C60 2.2uF to GND | Pin table says 1 uF; EC test conditions use CHPVSS = 2.2 uF, so 2.2 uF is characterized-good | pass |
| 9 | CPN | /HP_CPN → C59.2 | Flying cap: "negative side of 1 uF capacitor between CPP and CPN". C59 = 1 uF | pass |
| 10 | PGND | /GND | Power ground | pass |
| 11 | CPP | /HP_CPP → C59.1 | Flying cap positive side, 1 uF | pass |
| 12 | HPVDD | /HPVDD → C61 2.2uF to GND, nothing else on net | "Connect to a 2.2 uF capacitor. Do not connect to VDD"; datasheet WARNING: HPVDD is internally generated (abs max 1.9 V). Net contains only C61 — correct | pass |
| 13 | EN | /HP_ENABLE ← U8 pin 33, J7.23; R64 100k pull-down to GND | "Connect to logic low to shutdown; logic high to activate"; VIH 1.3 V. Pull-down = amp off by default = pop-safe; matches datasheet-recommended sequencing (enable after source settles) | pass |
| 14 | VDD | /+5V; C65 2.2uF on rail | 2.3–5.5 V supply; "Place a 2.2 uF capacitor within 5 mm of the VDD pin". C65 is ~8.6 mm away in current layout | warning (F7, layout only) |
| 15 | SGND | /GND | Signal ground | pass |
| 16 | OUTL | /HP_OUT_L → R65 10R → /HP_JACK_L → J5.T | Same as OUTR | pass |
| 17 (EP) | Thermal pad | /GND | Exposed pad to GND | pass |

## RV1 — RK097 dual 10kA volume pot (MPN RK0971221-F15-C0-A103, custom footprint)

| Pin | Net | Role as wired |
|---:|---|---|
| 1 | /DAC_L | gang A end — signal in |
| 2 | /HP_VOL_L | gang A wiper → C57 → U10 INL- |
| 3 | /GND | gang A end — ground |
| 4 | /DAC_R | gang B end — signal in |
| 5 | /HP_VOL_R | gang B wiper → C58 → U10 INR- |
| 6 | /GND | gang B end — ground |

Topology is a correct passive volume divider (in / wiper / gnd per gang, gangs consistent with each other; DAC sees 10 kΩ ≥ 1 kΩ min load; wiper source impedance ≤ 2.5 kΩ against 19.8 kΩ amp input — fine). **manual_review (F3):** with the usual Alps convention (terminal 1 = full-CCW end), signal on pad 1 and ground on pad 3 puts maximum volume at full counter-clockwise and reverses the A-taper (audio taper becomes anti-log). Whether pad 1 of the custom footprint `RK097_Dual_Horizontal_NoEdgeGuide` (pads 1-2-3 in one row at 2.5 mm pitch, 4-5-6 in the second row) corresponds to the CCW terminal cannot be determined from netlist/PCB data — no RK097 datasheet in the cache. Verify against the Alps drawing before ordering; fix is a net swap of pins 1↔3 and 4↔6 if reversed.

## J5 — 3.5 mm headphone jack (CUI SJ1-3533NG)

| Pin | Net | Verdict |
|---|---|---|
| T | /HP_JACK_L ← R65 10R ← U10 OUTL | pass |
| R | /HP_JACK_R ← R66 10R ← U10 OUTR | pass |
| S | /GND | pass — DirectPath explicitly wants sleeve grounded: "The headphone connector shield pin connects to ground and will interface with headphones and non-headphone accessories" (§7.3.1) |

No output DC-blocking caps present — correct for DirectPath (verified none on /HP_OUT_x or /HP_JACK_x nets). Output short protection: built-in ("short-circuit and thermal-overload protection", §7.3/features) plus 10R series. pass.

## J4 — 1/4 in line out (Neutrik NRJ6HF)

| Pin | Net | Verdict |
|---|---|---|
| T | /LINE_L ← R62 100R ← U9 OUTL | warning (F2, F4) |
| R | /LINE_R ← R63 100R ← U9 OUTR | warning (F2, F4) |
| S | /GND | pass |

Driven directly from PCM5102A OUTL/OUTR through 100R only. Ground-centered 2.1 Vrms output means **no DC-blocking caps are needed and none are wrongly inserted** — correct. But: (a) TI's recommended line-out network is 470 Ω series + 2.2 nF shunt (datasheet EC note 3: "Output load is 10 kΩ, with 470-Ω output resistor and a 2.2-nF shunt capacitor (see recommended output filter)", and the line-out application figure shows 470R/2.2nF per channel) — the shunt cap is absent and the series R is 100R; (b) a TS (mono) plug in this TRS jack shorts R to S, loading OUTR with 100 Ω against the 1 kΩ minimum rated load; tip also sees momentary shorts during insertion.

## Control nets

- /DAC_MUTE: U8.34 → R61 100R → XSMT, with R60 10k pull-up to +3V3_D. Matches J7.11 per connector-pinout.md. Direction of pull is the issue (F1).
- /HP_ENABLE: U8.33 → EN direct, R64 100k pull-down. Matches J7.23. Correct pop-safe default; sequencing per TPA6132A2 §7.3.2 ("Activate the TPA6132A2 after all audio sources have been activated... On power-down, deactivate the TPA6132A2 before deactivating the audio input source") is achievable in firmware.

## Findings

**F1 — XSMT strapped to un-mute by default (R60 10k to +3V3_D)** — severity: medium, confidence: high.
Evidence: pinmap R60 {1: /+3V3_D, 2: /DAC_MUTE_IC}; PCM5102A pin table "XSMT 17 I Soft mute control: Soft mute (Low) / soft un-mute (High)". Before the Teensy boots and configures pin 34 (boot state = high-Z), the 10k pull-up holds XSMT high, so the DAC is un-muted whenever supplies are up. The power-path review's own mitigation ("firmware must keep DAC mute/headphone enable inactive during startup") is defeated for the DAC because the hardware default is un-muted. Practical impact is softened by clock-error auto-mute (§11.2: outputs attenuate on clock error) and by HP_ENABLE defaulting off, but the line out (J4) has no downstream mute. Secondary: if firmware ever tri-states the pin and lets the 10k pull-up create the rising edge, XSMT tr violates the <20 ns requirement (§8.7). Recommend R60 to GND instead (Teensy drives high to un-mute).

**F2 — No post-DAC low-pass/reconstruction filter (TI recommends 470 Ω + 2.2 nF)** — severity: medium, confidence: high.
Evidence: datasheet EC note 3 and line-out application figure (470R series, 2.2 nF shunt per channel); board has only R62/R63 = 100R and no shunt caps anywhere on /DAC_L, /DAC_R, /LINE_L, /LINE_R (pinmap net dump). Out-of-band delta-sigma noise goes unfiltered to J4 and into the HP amp. Commonly omitted in hobby PCM5102A boards, but datasheet-characterized performance assumes the filter; easy fix is 2.2 nF shunts at J4 and optionally at RV1 inputs.

**F3 — RV1 rotation/taper direction unverifiable, likely reversed vs Alps convention** — severity: medium, confidence: medium (manual_review).
Evidence: pinmap RV1 (signal on pads 1/4, GND on pads 3/6); Alps RK097 convention places terminal 1 at full-CCW, in which case volume increases counter-clockwise and the 10kA log taper is reversed. Custom footprint pad-to-terminal mapping not confirmable from available data (no RK097 datasheet cached). Both gangs are wired identically, so L/R tracking is unaffected either way.

**F4 — Mono/TS plug in J4 shorts LINE_R to ground through only 100 Ω** — severity: low, confidence: high.
Evidence: J4 R = /LINE_R via R63 100R; PCM5102A EC "Load impedance 1 kΩ (min)". A TS plug (or TRS insertion transient) presents a 100 Ω load to OUTR at up to 2.1 Vrms (~21 mA). No damage rating is given in the datasheet; sustained operation out of spec. Raising R62/R63 toward 470R (matching F2) largely resolves this.

**F5 — LDOO cap is 1 uF vs datasheet-specified 0.1 uF** — severity: low, confidence: medium (manual_review).
Evidence: C53 = 1 uF on /DAC_LDO; Table 12: LDOO "Should be used with a 0.1-µF decoupling cap." Larger caps on this internal 1.8 V LDO output are widely used without issue, but it deviates from the stated value; no stability spec is published for the internal LDO.

**F6 — Headroom mismatch: 2.1 Vrms DAC into 0 dB amp with ~1.1 Vrms max output** — severity: low, confidence: high (informational).
Evidence: PCM5102A "Full-scale single-ended output 2.1 VRMS"; TPA6132A2 EC "VO Output voltage (Outputs in phase) THD = 1%, RL = 100 Ω: 1.1 VRMS" and §7.3.4 constant-max-output-power. At full pot, full-scale program clips the HP amp; roughly the top ~5.6 dB of pot travel is unusable at 0 dBFS. Acceptable by design (acoustic-shock limiting), but the panel behavior should be expected/documented; -6 dB gain strap (G0=G1=low) would trade level for clean full-rotation.

**F7 — U10 decoupling/charge-pump caps beyond datasheet placement distance** — severity: low, confidence: high (layout, pre-order note).
Evidence: TPA6132A2 §9.1 "Place a 2.2 uF capacitor within 5 mm of the VDD pin"; PCB positions: C65 (VDD) 8.6 mm, C59 (flying) 7.0 mm, C61 (HPVDD) 8.6 mm, C60 (HPVSS) 9.6 mm from U10 center. PCM5102A charge-pump caps C51/C52 at 7–9 mm vs "as close as possible" (§12.1). Degrades PSRR/charge-pump ripple margin; no netlist change needed, placement tighten only.

## Explicit verifications requested by scope

- SCK grounded = internal BCK-PLL mode: confirmed intended and supported (§9.3.5.3, Table 11). pass.
- CAPP/CAPM flying cap = 2.2 uF per datasheet: confirmed (C51). pass.
- XSMT controllable and checked against DAC_MUTE: confirmed wired to Teensy D34; pull direction flagged (F1).
- DAC outputs direct to pot and line out, no wrongly-inserted DC-block: confirmed correct for ground-centered output; missing recommended RC filter flagged (F2).
- TPA6132A2 input coupling caps present (C57/C58 680nF) and required per §7.3.2 for pop-free turn-on: confirmed. INL+/INR+ direct-grounded exactly per datasheet single-ended instruction (no caps needed — differs from TPA6130-class parts). pass.
- No HP output caps, jack sleeve grounded: confirmed correct for DirectPath. pass.
- HPVDD not tied to any supply rail (datasheet damage warning): confirmed — net contains only C61. pass.
- EP grounded: confirmed. pass.
- Gain strap G0=high/G1=low = 0 dB, legal logic levels: confirmed. pass.
- Prior-review claims re-verified: "EN pulled down 100k" true; "mute is pulled to a defined state" true but the defined state is un-muted (F1) — prior reviews did not surface this.

## Not verifiable from available data

RV1 custom-footprint pad-to-Alps-terminal orientation (F3); whether the NRJ6HF variant fitted has normalling/switch contacts (pinmap exposes only T/R/S); actual Teensy I2S2 BCK ratio and firmware GPIO boot behavior; audible significance of F1/F2 (bench items).
