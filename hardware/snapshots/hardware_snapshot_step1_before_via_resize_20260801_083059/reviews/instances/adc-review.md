# U7 PCM1864DBT ADC Section Review — QuadPreRecorder Rev A

Scope: pin-level pre-order review of U7 (PCM1864DBT, TSSOP-30, 4-ch ADC, TDM slave to Teensy 4.1 SAI1, I2C control).
Facts source: /home/claude/review/pinmap.json (cross-validated vs routed PCB, 0 mismatches).
Datasheet: /home/claude/review/datasheets/text/pcm1864_272ada92bc.txt (SLAS831D, Mar 2018). Line references below are to that text file.

## 1. Full 30-pin table

| Pin | Name | Net | Expected (datasheet) | Verdict |
|----|------|-----|----------------------|---------|
| 1 | VINL2/VIN1M | /BLD_ADC | SE analog input 2-L (BLD channel); AC-coupled | pass |
| 2 | VINR2/VIN2M | /BRU_ADC | SE analog input 2-R (BRU channel); AC-coupled | pass |
| 3 | VINL1/VIN1P | /FLU_ADC | SE analog input 1-L (FLU channel); AC-coupled | pass |
| 4 | VINR1/VIN2P | /FRD_ADC | SE analog input 1-R (FRD channel); AC-coupled | pass |
| 5 | Mic Bias | /ADC_MICBIAS | Unused here; "decouple with external capacitor... can be left unconnected if not used" (ds L2237–2243). C38 1uF to GND fitted, no load. | pass |
| 6 | VREF | /ADC_VREF | "Connect 1-uF capacitor from this pin to AGND" (ds L546, L453). C39 1uF + C40 100nF fitted. | pass |
| 7 | AGND | /GND | Analog ground | pass |
| 8 | AVDD | /+3V3_A | 3.3V analog; "0.1-uF and 10-uF capacitors to AGND" (ds L548-equiv, L457). C41 100nF + C42 10uF on net (see 2.1). | pass |
| 9 | XO | NC | Crystal output; crystal unused (SCKI used instead) | pass |
| 10 | XI | NC | Crystal/1.8V MCLK input; unused. No explicit float/tie guidance located in datasheet; XI and SCK "are OR-ed internally" (ds L2711–2712). | manual_review |
| 11 | LDO | /ADC_LDO | Internal 1.8V LDO decoupling: "Connect 0.1-uF and 10-uF capacitors from this pin to DGND" (ds L553, L460–461). C43 100nF + C62 10uF fitted. Internal LDO used (not 1.8V bypass mode). | pass |
| 12 | DGND | /GND | Digital ground. AGND–DGND diff limit +/-0.3V (ds abs-max, L2225 area); common ground net satisfies this. | pass |
| 13 | DVDD | /+3V3_D | 3.3V digital; 0.1uF + 10uF to DGND. C44 100nF + C45 10uF on net (see 2.1). | pass |
| 14 | IOVDD | /+3V3_D | 3.3V I/O. 3.3V REQUIRED for TDM above 96kHz (ds L4058–4060, L4146–4148). Matches Teensy 3.3V logic. | pass |
| 15 | SCKI | /ADC_MCLK_IC | "CMOS level (3.3 V) master clock input", 1–50MHz (ds L558-equiv, L914, Table 4 L2579–2580). Driven by Teensy U8 pin 23 (D23/MCLK1) via R46 33R. Direction correct: Teensy sources MCLK, PCM1864 is clock consumer. | pass |
| 16 | LRCK | /ADC_LRCLK_IC | Word clock I/O, Schmitt input w/ internal 50k pull-down (ds L444, L560). Driven by Teensy pin 20 (D20/LRCLK1) via R47 33R — slave mode. | pass |
| 17 | BCK | /ADC_BCLK_IC | Bit clock I/O. Driven by Teensy pin 21 (D21/BCLK1) via R48 33R — slave mode. Wiring correct, but see Finding F1: 192kHz TDM needs BCK = 49.152MHz. | warning |
| 18 | DOUT | /ADC_TDM_IC | Audio data output; to Teensy pin 8 (D8/IN1, SAI1 RX) via R49 33R. Hi-Z between slots in TDM (ds L4046). | pass |
| 19 | GPIO3/INTC | NC | GPIO/interrupt, unused. No interrupt path to MCU — polling only (Finding F3). | pass |
| 20 | GPIO2/INTB/DMCLK | NC | GPIO/interrupt/DMIC clock, unused | pass |
| 21 | GPIO1/INTA/DMIN | NC | GPIO/interrupt/DMIC data, unused | pass |
| 22 | MISO/GPIO0/DMIN2 | NC | In I2C mode this is GPIO0/DMIN2 (ds L566–567); unused. Also means DOUT2 (secondary I2S output, GPIO-mapped, ds L3925–3929) is unavailable — relevant to F1 fallback options. | pass |
| 23 | MOSI/SDA | /I2C_SDA | I2C SDA (ds L568–569). To Teensy pin 18 (D18/SDA). Pull-up R44 4.7k to /+3V3_D (3.3V) — correct rail, correct value for 100/400kHz. | pass |
| 24 | MC/SCL | /I2C_SCL | I2C SCL (ds L570–571). To Teensy pin 19 (D19/SCL). Pull-up R45 4.7k to /+3V3_D (3.3V). | pass |
| 25 | MS/AD | /GND | In I2C mode: address pin (ds L572–573, Table 22 L4261). Low = I2C address 0x94 write / 7-bit 0x4A (Table 21 L4176–4179, Table 23 L4267). | pass |
| 26 | MD0 | /GND | "Control method select: I2C (tied low or not connected) or SPI (tied high)" (ds L574). Tied low = I2C mode. | pass |
| 27 | VINL4/VIN4M | NC | Unused analog input. "Do not connect unused analog input pins." (ds L2212) — floating is the documented handling. | pass |
| 28 | VINR4/VIN3M | NC | Unused analog input, floating per ds L2212 | pass |
| 29 | VINL3/VIN4P | NC | Unused analog input, floating per ds L2212 | pass |
| 30 | VINR3/VIN3P | NC | Unused analog input, floating per ds L2212 | pass |

## 2. External parts check

### 2.1 Decoupling per rail (actual refs from pinmap.json)
- AVDD (pin 8, /+3V3_A from U2 TPS7A2033 LDO): C41 100nF, C42 10uF, plus C54 100nF, C55 10uF, C64 100nF, C8 4.7uF shared with U9 PCM5102A on the same rail. Datasheet requirement (0.1uF + 10uF at AVDD) is met at net level. Which caps sit at U7 vs U9 is a layout/placement question, not resolvable from the netlist — verify 100nF+10uF land adjacent to U7 pin 8.
- DVDD (pin 13) and IOVDD (pin 14), /+3V3_D (Teensy 3.3V rail): C44 100nF, C45 10uF, C56 100nF, C63 100nF on net. Requirement met at net level; same placement caveat. Note IOVDD = 3.3V satisfies the >96kHz TDM I/O requirement (ds L4058–4060).
- LDO (pin 11, /ADC_LDO): C43 100nF + C62 10uF — exactly the datasheet-required 0.1uF + 10uF (ds L460–461).
- VREF (pin 6, /ADC_VREF): C39 1uF (datasheet-required, ds L453/546) + C40 100nF (extra HF bypass, harmless).
- Mic Bias (pin 5): C38 1uF; output otherwise unloaded (capsule bias is generated in the preamp stage, not by U7). Datasheet allows decoupled-or-floating (ds L2237–2243).

### 2.2 Analog input network (per channel, FLU shown; FRD/BLD/BRU identical)
Preamp U6 OPA1654 out (/FLU_PRE) -> C25 4.7uF 16V (DC block) -> /FLU_ADC_SRC -> R34 100R -> /FLU_ADC -> U7 pin 3; on pin node: C29 10nF C0G to GND, R38 100k to GND. (Refs: C25–C28, R34–R37, C29–C32, R38–R41.)
- DC blocking caps: required — "DC blocking capacitors are required on the analog inputs... input pins are designed to bias to AVDD / 2" (ds L2206–2211). Present: 4.7uF. PASS.
- 20Hz flatness: PCM1864 input impedance = 10kOhm per pin SE (ds L714–716). HPF fc = 1/(2*pi*4.7uF*(100R + 10k||100k)) ~= 3.7Hz; response at 20Hz ~= -0.1dB. Flat. PASS.
- RF/anti-alias: 100R + 10nF -> fc ~= 159kHz. Reasonable.
- R38–R41 100k to GND sit on the ADC-pin side of the DC block and fight the pin's AVDD/2 self-bias — see Finding F2.
- Channel mapping: FLU->VINL1 (ADC1-L), FRD->VINR1 (ADC1-R), BLD->VINL2 (ADC2-L), BRU->VINR2 (ADC2-R). This is the canonical 4-channel single-ended set for the PCM1864 mux and matches the required TDM slot order FLU, FRD, BLD, BRU (firmware README).

### 2.3 Digital interface
- All four audio lines have 33R series damping at the source end (R46–R48 at Teensy side for MCLK/LRCLK/BCLK; R49 at ADC side for DOUT). Net names and Teensy pin functions match firmware README pin map (20/21/23 = ADC LRCLK/BCLK/MCLK, 8 = ADC TDM data) and connector-pinout.md J7 pins 4–7 (ADC_MCLK/BCLK/LRCLK/TDM, which stub onto the DB-25 debug connector).
- I2C: R44/R45 4.7k pull-ups to /+3V3_D = 3.3V (NOT 5V — pass). Bus shared with J3 TFT touch header and J7; PCM1864 at 0x4A, no known conflict with common CTP controllers (0x38) — firmware should confirm.
- No RESET pin exists on this device; reset/power-down are I2C register functions (PWRDN_CTRL Page.0 0x70, ds L4139 area). Nothing to wire — correct as-is.

## 3. Findings

### F1 — 192kHz 4-channel TDM as documented is not supported by the PCM1864 TDM frame format
- Severity: HIGH. Confidence: HIGH (datasheet constraint), system impact firmware-defined -> flagged manual_review.
- Evidence: "The frame rate in TDM mode fixed to 256 BCK per frame" (ds L3935–3936). Clock-error logic: at 176.4/192kHz LRCK, SCK/LRCK must be 128 or 256, and BCK/LRCK not in {256, 64, 48, 32} raises a BCK error -> "clock waiting state, tie I2S output to 0" (Table 16, ds L3294–3305). Max BCK 50MHz at IOVDD=3.3V (ds L917–918).
- Problem: architecture.md ("192 kHz, four-slot 32-bit TDM into one Teensy SAI receiver") and firmware README ("four 32-bit TDM slots") imply a 128-BCK frame (4x32 @ 192kHz -> BCK = 24.576MHz). The PCM1864 TDM frame is fixed at 256 BCK, so 192kHz TDM requires BCK = 49.152MHz — inside the chip's 50MHz limit only marginally, almost certainly beyond the Teensy 4.1 SAI bit-clock capability, and unreasonable through 33R damping plus DB-25 J7 stubs on a 2-layer board. A 128-BCK frame would additionally trip the BCK-error detector unless CLKDET_EN is cleared (ds L3307–3309), and even then the silicon's TDM engine expects 256 BCK/frame.
- Hardware consequence: pins are wired for exactly one DOUT; the 4-channel non-TDM alternative (DOUT2 on a GPIO, 2x stereo I2S at 192kHz, BCK 12.288MHz each — ds L3925–3929) is unavailable because GPIO0–GPIO3 (pins 19–22) are all NC.
- Realistic options with this PCB: (a) run 96kHz 4-ch TDM (256x96k = 24.576MHz BCK — clean, matches Teensy capability); (b) 192kHz limited to 2 channels I2S; (c) accept 49.152MHz BCK experiment (not recommended). Decide before ordering only if 192kHz/4ch is a hard requirement; the copper itself needs no change for option (a)/(b).

### F2 — R38–R41 (100k to GND) load the ADC input pins' internal AVDD/2 bias
- Severity: MEDIUM. Confidence: MEDIUM (exact internal topology not fully specified in datasheet).
- Evidence: "the input pins are designed to bias to AVDD / 2" (ds L2209–2210); "Input impedance per analog input pin: PCM1864... 10 kOhm" (ds L714–716).
- With 10k internal impedance to the AVDD/2 bias and 100k external to GND on the pin side of the DC-block cap, the pin settles near 1.5V instead of 1.65V (~15uA standing current, ~150mV DC shift). If the PGA amplifies this offset (PGA range here is used up to ~+32dB per architecture.md), the resulting DC offset can consume significant analog headroom before the digital HPF removes it. TI's reference input network places no DC path to GND on the ADC side of the coupling cap.
- Recommendation: DNP R38–R41 (the node's DC is already defined by the ADC's self-bias; the source side is DC-defined by the OPA1654 output), or increase to >=1M if a bleed is wanted.

### F3 — No interrupt line from U7 to the Teensy
- Severity: LOW. Confidence: HIGH.
- GPIO1/INTA, GPIO2/INTB, GPIO3/INTC (pins 21/20/19) all NC. Energysense/clip/DC-level interrupts (ds L3810 area) cannot reach the MCU; status must be polled over I2C. Acceptable for a recorder; note only.

### F4 — XI (pin 10) floating with no located datasheet guidance
- Severity: LOW. Confidence: MEDIUM. Verdict: manual_review.
- XI/XO unused (MCLK on SCKI). Datasheet states XI and SCK clocks are OR-ed internally (ds L2711–2712) but gives no explicit "tie or float" instruction for an unused XI; the crystal oscillator is register-enabled on software devices (ds L3055–3057), so a floating XI is very likely fine (TI EVM leaves the crystal footprint unpopulated). Not blocking.

### F5 — Decoupling cap placement not provable from netlist
- Severity: LOW. Confidence: HIGH (as a limitation).
- AVDD/DVDD rails are shared with U9/U8; required cap values exist on each net but per-pin adjacency (100nF+10uF at U7 pins 8 and 13, 100nF+10uF at pin 11, 1uF at pin 6) must be confirmed in layout. Prior schematic-review.md claims "input filters... placed at U7" and datasheet-summary.md claims bypassing "follows data sheet"; the values re-verify, the placement was not re-verifiable here.

### F6 — Clocking scheme achievability (firmware-defined)
- Verdict: manual_review (pass at hardware level).
- Teensy MCLK1 -> SCKI: at fs=192kHz the SCK/LRCK ratio must be 128 or 256 (Table 16, ds L3301); Teensy MCLK1 = 24.576MHz gives 128x192k — valid, or the on-chip PLL can be used from any 1–50MHz SCKI (ds L2565–2569). At 96kHz, 24.576MHz = 256x fs — also valid. Hardware supports the clock topology; register configuration (CLKDET, PLL/dividers, I2S_FMT/TDM_OSEL/TDM_LRCK_MODE, RX/TX TDM offsets — ds L4044–4068) is firmware's job.

## 4. Cross-document notes
- firmware README pin map and connector-pinout.md J7 (pins 4–7) agree with pinmap.json nets exactly.
- architecture.md's "192 kHz four-slot 32-bit TDM" claim conflicts with the PCM1864 fixed 256-BCK TDM frame (Finding F1). Prior reviews (schematic-review.md, datasheet-summary.md) did not catch this; their claims about 33R damping, bypassing values, and unused-pin handling re-verified as correct.

## 5. Not verified
- Physical placement/adjacency of decoupling caps (netlist-level review only).
- Teensy 4.1 (i.MX RT1062) SAI maximum bit-clock — stated from general knowledge (~25MHz class), not from an NXP datasheet in this repo.
- Actual firmware register configuration (TDM format, PLL, PGA settings) — does not exist in hardware.
- J3 touch-controller I2C address (assumed no conflict with 0x4A).
