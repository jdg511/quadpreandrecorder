# QuadPreRecorder Rev C3 (board `revc3teensy-final`, 2026-09-15): design review dossier

Generated 2026-09-15 from the exact files in the PCBWay handoff zip of 2026-09-15 (`hardware/QuadPreRecorder.kicad_sch` and `.kicad_pcb`, backup `QuadPreRecorder.kicad_pcb.revc3teensy-final-20260915`; the 2026-09-13 board and zip are void, see section 4). Every table below is read straight out of those files by the analyzers, then cross-checked against the board's pad-to-net data, so what you are reviewing is what will be built.

## 0. How to use this

The document is long on purpose. Sections 1 to 3 are the design as intended (in words and numbers), sections 4 to 9 are the design as drawn (every pin of every IC, transistor, diode and connector with the net it lands on and what is at the other end of that net), sections 10 to 13 are the arithmetic (set points, corners, currents), and sections 14 to 19 are the board, the checks, the parts and the bring-up list. If you only have an hour: read section 1, then check sections 4, 6 and 10 against the datasheets. Those are where a wrong pin or a wrong resistor would hide.

Files that go with this dossier: `QuadPreRecorder-schematic.pdf` (the schematic as drawn), `QuadPreRecorder-assembly-top.pdf` / `-bottom.pdf` (reference designators on the board), `QuadPreRecorder-top.png` / `-bottom.png` / `-isometric.png` (renders), and the PCBWay files delivered on 2026-09-15 (the 2026-09-13 set is void: it carried the wrong Teensy socket).

## 1. What the board is, in one page

A four-channel ambisonic microphone preamplifier and 192 kHz / 24-bit recorder for a Hammond 1590XX box. Four capsules (electret with on-board bias, or dynamic/balanced with the bias off) come in on one shielded RJ45. Each channel is a two-op-amp instrumentation stage (OPA1654, +20.1 dB, switchable -9.7 dB pad) into a PCM1864 four-channel ADC. A Teensy 4.1 records four mono WAVs to microSD over native SDIO, drives a 3.5-inch capacitive touch TFT, and decodes a real-time binaural monitor mix out of a PCM5102A DAC to a relay-muted 1/4-inch line jack and a TPA6130A2 I2C-volume headphone amp. Power is 9 V barrel, USB-C 5 V, or an internal 1S LiPo (BQ24074 charger), all boosted to 10.45 V and then regulated to a low-noise 9 V analog rail, a 5 V buck rail and two 3.3 V LDO rails for the converters.

| Item | Value |
|---|---|
| Board | 138.0 x 114.0 mm, 12 mm chamfered corners, 4 layers (F.Cu signal / In1.Cu GND / In2.Cu GND / B.Cu signal), 1.6 mm FR-4 |
| Schematic | 312 components, 93 unique parts, 213 nets, 1 DNP line, 0 missing MPN |
| PCB | 322 footprints (188 top / 134 bottom), 292 SMD + 12 THT, 523 vias, 3050 track segments, 10.6 m of track, 20 zones |
| Assembly | 293 placements (180 top, 113 bottom); BOM 95 lines, all with manufacturer part numbers; DNP R5, R38-R41 |
| Checks | ERC 0 errors / 0 warnings. DRC 0 violations / 0 unconnected / 0 parity at error severity; 220 cosmetic warnings (section 15). GND: 184 pads, one cluster |
| Firmware pins | Teensy 4.1: see section 8 |

## 2. Power tree (design intent, with the numbers to check)

```
J1 9 V barrel --F1 750 mA PTC--> +9V_FUSED --D1 B340A--+
                                                       |
J9 USB-C VBUS --F2 2 A PTC--> VBUS_FUSED --D10 B340A---+--> VBOOST_IN (5..9 V) --> U11 TPS61175 boost --> +10V5 (10.45 V)
                    |                                  |                                                   |
                    +--> U13 BQ24074 charger --> BAT_SYS --D14 B340A--+                +----------------------+----------------------+
                             |                                                         |                                             |
                    J10 1S LiPo (VBAT) ---> U13 (power path)                U12 ADP7142 LDO --> +9V (9.0 V analog)      U1 TPS62160 buck --> +5V (5.0 V)
                                                                                       |                                    |         |         |
                                                                          preamps U6/U16, U3 VREF (4.5 V),     U2 TPS7A2033 --> +3V3_A   U14 TPS7A2033 --> +3V3_DC   D3 SS14 --> TEENSY_VIN
                                                                          CD4053 U4/U5/U15, Q6 9 V mic bias     (PCM1864 AVDD, PCM5102A AVDD)  (PCM1864 DVDD/IOVDD, PCM5102A DVDD)  (Teensy 4.1, whose own
                                                                          +9V_MIC (R67/C66 filter)             Q8 5 V mic bias, TPA6130A2, relay K1, TFT VCC/backlight   regulator makes +3V3_D)
```

| Rail | Source | Set by | Nominal | Feeds |
|---|---|---|---|---|
| VBOOST_IN | D1 / D10 / D14 OR-ing (barrel, USB, battery) | diodes | 4.4 to 8.7 V | U11 boost only (plus D2 SMBJ12A clamp, C1 100 uF, C85 10 uF) |
| +10V5 | U11 TPS61175 boost | R80 75k / R81 10k on 1.229 V ref | 10.45 V | U12 LDO input, U1 buck input |
| +9V | U12 ADP7142 LDO | R130 130k / R131 20k on 1.2 V ref | 9.00 V | U6, U16 (op-amps), U3 (VREF), U4/U5/U15 (CD4053), Q6 (9 V mic bias), R106/R83 pull-ups |
| VREF | U3 TLE2426 rail splitter from +9V | fixed 1/2 | 4.50 V | analog mid-rail for every channel (1M, 33k, 90.9k, 100k returns) |
| +9V_MIC | Q6 (9 V) or Q8+D24 (5 V) into R67 100R / C66 100 uF | firmware | 9.0 / ~4.7 / 0 V | R6-R9 4.7k electret bias per channel, R104 100k bleed |
| +5V | U1 TPS62160 buck from +10V5 | R1 680k / R2 130k on 0.8 V ref | 4.98 V | U2, U14, D3 -> Teensy VIN, U10 headphone amp, K1 relay, Q8 5 V bias, J3 TFT VCC, R56 backlight, D4 power LED |
| +3V3_A | U2 TPS7A2033 (fixed 3.3 V) from +5V | fixed | 3.30 V | PCM1864 AVDD (pin 8), PCM5102A AVDD (pins 1, 8) |
| +3V3_DC | U14 TPS7A2033 (fixed 3.3 V) from +5V | fixed | 3.30 V | PCM1864 DVDD/IOVDD (13, 14), PCM5102A DVDD (20), TP12 |
| +3V3_D | Teensy 4.1 on-module regulator | Teensy | 3.30 V | every pull-up to the Teensy (I2C, buttons, nav, charger status) |
| TEENSY_VIN | +5V through D3 SS14 | diode | ~4.7 V | Teensy VIN (its VIN-VUSB link must be CUT) |
| ADC_LDO, DAC_LDO, ADC_VREF | PCM1864 / PCM5102A internal regulators | chips | 1.8 V class | decoupling only (C43/C62, C53, C39/C40) |
| VBAT / BAT_SYS | J10 battery / U13 power-path output | charger | 3.0-4.2 V / 4.4 V | U13, D14, R89/R90 gauge, Q3/Q4 soft-power latch |

## 3. Rail membership, as drawn

Every component pin that touches each supply rail, from the schematic netlist. Use this to spot a part on the wrong rail.

- **+10V5** (11 pins): C2.1, C3.1, C76.1, C77.1, C83.1, D12.1, R80.1, U1.2/3, U12.1/3
- **+9V** (21 pins): C34.1, C35.1, C36.1, C37.1, C74.1, C75.1, C88.1, C109.1, C110.1, Q6.2, R83.1, R98.1, R106.1, R130.1, U3.3, U4.16, U5.16, U6.4, U12.5, U15.16, U16.4
- **VREF** (27 pins): C10.1, C11.1, C105.2, C106.2, C107.2, C108.2, R14.2, R15.2, R16.2, R17.2, R19.2, R21.2, R23.2, R25.2, R114.2, R115.2, R116.2, R117.2, R122.2, R123.2, R124.2, R125.2, R126.2, R127.2, R128.2, R129.2, U3.1
- **+9V_MIC** (7 pins): C66.1, R6.1, R7.1, R8.1, R9.1, R67.2, R104.1
- **+5V** (25 pins): C4.1, C5.1, C6.1, C7.1, C61.1, C65.1, C95.1, D3.2, D13.1, J3.1, K1.1, L1.2, Q8.2, R1.1, R3.1, R54.1, R56.1, R101.1, U1.6, U2.1/3, U10.20/12, U14.1/3
- **+3V3_A** (10 pins): C8.1, C41.1, C42.1, C54.1, C55.1, C64.1, U2.5, U7.8, U9.1/8
- **+3V3_DC** (9 pins): C44.1, C45.1, C56.1, C96.1, TP12.1, U7.13/14, U9.20, U14.5
- **+3V3_D** (16 pins): R44.1, R45.1, R50.1, R51.1, R52.1, R53.1, R70.1, R71.1, R72.1, R73.1, R74.1, R94.1, R95.1, R96.1, R97.1, U8.3V3A
- **TEENSY_VIN** (3 pins): C46.1, D3.1, U8.VIN
- **VBOOST_IN** (8 pins): C1.1, C85.1, D1.1, D2.1, D10.1, D14.1, L2.1, U11.3
- **VBUS** (7 pins): D11.5, F2.1, J9.A4/A9/B4/B9, R77.1
- **VBUS_FUSED** (6 pins): C90.1, D10.2, D16.2, F2.2, U13.5/13
- **VBAT** (8 pins): C92.1, J10.1, Q3.2, R86.1, R87.1, R89.1, U13.2/3
- **BAT_SYS** (4 pins): C91.1, D14.2, U13.10/11
- **CHASSIS** (21 pins): C12.1, C13.2, C14.2, C15.2, C16.2, C97.2, C98.2, C99.2, C100.2, D6.2, D7.2, D8.2, D9.2, D20.2, D21.2, D22.2, D23.2, J2.SH, J9.SH, R4.1, R5.1

- **GND**: 183 pins on 137 components (not listed).

## 4. Integrated circuits, pin by pin

For every pin: the schematic net, what else sits on that net, and the net the PCB pad actually carries. The two net columns must agree on every row (they do: the parity check passed). The notes give the datasheet pin function to compare against; where I was not certain of a datasheet pin name I said so rather than guess.

### U11 TPS61175PWP (TPS61175PWPR) - Texas_HTSSOP-14-1EP_4.4x5mm_P0.65mm_EP3.4x5mm_Mask3.155x3.255mm

*TPS61175PWP boost. Datasheet (TI SLVS892): 1/2 SW, 3 VIN, 4 EN (abs max 20 V, VIH 1.2 V), 5 SS, 6 SYNC (tie to AGND when unused), 7 AGND, 8 COMP, 9 FB (1.229 V), 10 FREQ, 11 NC (must be grounded), 12-14 PGND, pad = AGND. As wired: every row matches; SYNC and NC are grounded as the datasheet asks.*

| Pin | Symbol pin name | Schematic net | Other ends of that net | PCB pad net |
|---:|---|---|---|---|
| 1 | SW | BOOST_SW | D12.2 (A), L2.2 | BOOST_SW |
| 2 | SW | BOOST_SW | D12.2 (A), L2.2 | BOOST_SW |
| 3 | VIN | VBOOST_IN | C1.1, C85.1, D1.1 (K), D2.1 (A1), D10.1 (K), D14.1 (K), L2.1 | VBOOST_IN |
| 4 | EN | BOOST_EN | D15.1 (K), D16.1 (K), D17.1 (K), Q4.3 (D), R88.1 | BOOST_EN |
| 5 | SS | BOOST_SS | C79.1 | BOOST_SS |
| 6 | SYNC | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 7 | AGND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 8 | COMP | BOOST_COMP | C81.1, R79.1 | BOOST_COMP |
| 9 | FB | BOOST_FB | R80.2, R81.1 | BOOST_FB |
| 10 | FREQ | BOOST_FREQ | R82.1 | BOOST_FREQ |
| 11 | NC | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 12 | PGND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 13 | PGND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 14 | PGND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 15 | EP | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |

### U12 ADP7142AUJZ (ADP7142AUJZ-R7) - TSOT-23-5

*ADP7142AUJZ LDO. Datasheet (ADI, Table 5): 1 VIN, 2 GND, 3 EN (may be tied to VIN), 4 SENSE/ADJ, 5 VOUT; VOUT = 1.2 V x (1 + R130/R131) = 9.00 V; 2.2 uF in/out minimum (C83 in, C74/C88 out). Matches.*

| Pin | Symbol pin name | Schematic net | Other ends of that net | PCB pad net |
|---:|---|---|---|---|
| 1 | VIN | +10V5 | C2.1, C3.1, C76.1, C77.1, C83.1, D12.1 (K), R80.1, U1.2 (VIN), U1.3 (EN) | +10V5 |
| 2 | GND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+168 more) | GND |
| 3 | EN | +10V5 | C2.1, C3.1, C76.1, C77.1, C83.1, D12.1 (K), R80.1, U1.2 (VIN), U1.3 (EN) | +10V5 |
| 4 | SENSE/ADJ | LDO_FB | R130.2, R131.1 | LDO_FB |
| 5 | VOUT | +9V | C34.1, C35.1, C36.1, C37.1, C74.1, C75.1, C88.1, C109.1, C110.1, Q6.2 (S), R83.1, R98.1, R106.1, R130.1, ... (+6 more) | +9V |

### U1 TPS62160DGK (TPS62160DGKR) - VSSOP-8_3x3mm_P0.65mm

*TPS62160DGK buck. Datasheet (TI SLVSAM2): 1 PGND, 2 VIN, 3 EN, 4 AGND, 5 FB (0.8 V), 6 VOS (output sense), 7 SW, 8 PG. As wired: EN tied to VIN (always on), VOS to +5V, FB from R1/R2. Matches. Note: the part has an internal 25 pF feed-forward cap VOS-FB; the external C4 22 pF across R1 is extra and harmless.*

| Pin | Symbol pin name | Schematic net | Other ends of that net | PCB pad net |
|---:|---|---|---|---|
| 1 | PGND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+167 more) | GND |
| 2 | VIN | +10V5 | C2.1, C3.1, C76.1, C77.1, C83.1, D12.1 (K), R80.1, U12.1 (VIN), U12.3 (EN) | +10V5 |
| 3 | EN | +10V5 | C2.1, C3.1, C76.1, C77.1, C83.1, D12.1 (K), R80.1, U12.1 (VIN), U12.3 (EN) | +10V5 |
| 4 | AGND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+167 more) | GND |
| 5 | FB | BUCK_FB | C4.2, R1.2, R2.1 | BUCK_FB |
| 6 | VOS | +5V | C4.1, C5.1, C6.1, C7.1, C61.1, C65.1, C95.1, D3.2 (A), D13.1 (K), J3.1 (Pin_1), K1.1, L1.2, Q8.2 (S), R1.1, ... (+10 more) | +5V |
| 7 | SW | BUCK_SW | L1.1 | BUCK_SW |
| 8 | PG | BUCK_PG | R3.2 | BUCK_PG |

### U2 TPS7A2033PDBV (TPS7A2033PDBVR) - SOT-23-5

*TPS7A2033PDBV 3.3 V LDO. Datasheet (TI): 1 IN, 2 GND, 3 EN (may be tied to IN), 4 NC, 5 OUT. Matches; 1 uF in (C7), 4.7 uF out (C8).*

| Pin | Symbol pin name | Schematic net | Other ends of that net | PCB pad net |
|---:|---|---|---|---|
| 1 | IN | +5V | C4.1, C5.1, C6.1, C7.1, C61.1, C65.1, C95.1, D3.2 (A), D13.1 (K), J3.1 (Pin_1), K1.1, L1.2, Q8.2 (S), R1.1, ... (+9 more) | +5V |
| 2 | GND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+168 more) | GND |
| 3 | EN | +5V | C4.1, C5.1, C6.1, C7.1, C61.1, C65.1, C95.1, D3.2 (A), D13.1 (K), J3.1 (Pin_1), K1.1, L1.2, Q8.2 (S), R1.1, ... (+9 more) | +5V |
| 4 | NC | NO_CONNECT | (nothing else: single-pin net) | - |
| 5 | OUT | +3V3_A | C8.1, C41.1, C42.1, C54.1, C55.1, C64.1, U7.8 (AVDD), U9.1 (CPVDD), U9.8 (AVDD) | +3V3_A |

### U14 TPS7A2033PDBV (TPS7A2033PDBVR) - SOT-23-5

*Same part as U2 for the converter digital rail. Matches; C95 in, C96 out.*

| Pin | Symbol pin name | Schematic net | Other ends of that net | PCB pad net |
|---:|---|---|---|---|
| 1 | IN | +5V | C4.1, C5.1, C6.1, C7.1, C61.1, C65.1, C95.1, D3.2 (A), D13.1 (K), J3.1 (Pin_1), K1.1, L1.2, Q8.2 (S), R1.1, ... (+9 more) | +5V |
| 2 | GND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+168 more) | GND |
| 3 | EN | +5V | C4.1, C5.1, C6.1, C7.1, C61.1, C65.1, C95.1, D3.2 (A), D13.1 (K), J3.1 (Pin_1), K1.1, L1.2, Q8.2 (S), R1.1, ... (+9 more) | +5V |
| 4 | NC | NO_CONNECT | (nothing else: single-pin net) | - |
| 5 | OUT | +3V3_DC | C44.1, C45.1, C56.1, C96.1, TP12.1, U7.13 (DVDD), U7.14 (IOVDD), U9.20 (DVDD) | +3V3_DC |

### U3 TLE2426ID (TLE2426IDR) - SOIC-8_3.9x4.9mm_P1.27mm

*TLE2426ID rail splitter. Datasheet: 1 OUT, 2 COMMON, 3 IN, 4-7 NC, 8 NR (noise-reduction cap C9 1 uF). Matches.*

| Pin | Symbol pin name | Schematic net | Other ends of that net | PCB pad net |
|---:|---|---|---|---|
| 1 | OUT | VREF | C10.1, C11.1, C105.2, C106.2, C107.2, C108.2, R14.2, R15.2, R16.2, R17.2, R19.2, R21.2, R23.2, R25.2, ... (+12 more) | VREF |
| 2 | COMMON | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+168 more) | GND |
| 3 | IN | +9V | C34.1, C35.1, C36.1, C37.1, C74.1, C75.1, C88.1, C109.1, C110.1, Q6.2 (S), R83.1, R98.1, R106.1, R130.1, ... (+6 more) | +9V |
| 4 | NC | NO_CONNECT | (nothing else: single-pin net) | - |
| 5 | NC | NO_CONNECT | (nothing else: single-pin net) | - |
| 6 | NC | NO_CONNECT | (nothing else: single-pin net) | - |
| 7 | NC | NO_CONNECT | (nothing else: single-pin net) | - |
| 8 | NOISE_REDUCTION | VREF_NR | C9.1 | VREF_NR |

### U13 BQ24074RGT (BQ24074RGTR) - VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm

*BQ24074RGT charger. Datasheet (TI, RGT): 1 TS, 2/3 BAT, 4 CE (low = charging enabled), 5 EN2, 6 EN1, 7 /PGOOD, 8 VSS, 9 /CHG, 10/11 OUT, 12 ILIM, 13 IN, 14 TMR (GND = safety timers off), 15 ITERM (open = 10 %), 16 ISET, pad VSS. As wired: CE = GND (charging on), EN2 = VBUS_FUSED (high when USB present), EN1 = GND -> input limit set by R91 (1610/1.1k = 1.46 A), TMR = GND, ITERM open, ISET R92 1.2k -> 890/1.2k = 0.74 A. Matches the design intent exactly.*

| Pin | Symbol pin name | Schematic net | Other ends of that net | PCB pad net |
|---:|---|---|---|---|
| 1 | TS | CHG_TS | R93.1 | CHG_TS |
| 2 | BAT | VBAT | C92.1, J10.1 (Pin_1), Q3.2 (S), R86.1, R87.1, R89.1 | VBAT |
| 3 | BAT | VBAT | C92.1, J10.1 (Pin_1), Q3.2 (S), R86.1, R87.1, R89.1 | VBAT |
| 4 | ~{CE} | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+164 more) | GND |
| 5 | EN2 | VBUS_FUSED | C90.1, D10.2 (A), D16.2 (A), F2.2 | VBUS_FUSED |
| 6 | EN1 | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+164 more) | GND |
| 7 | ~{PGOOD} | PGOOD_N | R95.2, U8.25 (D25) | PGOOD_N |
| 8 | VSS | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+164 more) | GND |
| 9 | ~{CHG} | CHG_STAT_N | R94.2, U8.17 (D17) | CHG_STAT_N |
| 10 | OUT | BAT_SYS | C91.1, D14.2 (A) | BAT_SYS |
| 11 | OUT | BAT_SYS | C91.1, D14.2 (A) | BAT_SYS |
| 12 | ILIM | CHG_ILIM | R91.1 | CHG_ILIM |
| 13 | IN | VBUS_FUSED | C90.1, D10.2 (A), D16.2 (A), F2.2 | VBUS_FUSED |
| 14 | TMR | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+164 more) | GND |
| 15 | ITERM | NO_CONNECT | (nothing else: single-pin net) | - |
| 16 | ISET | CHG_ISET | R92.1 | CHG_ISET |
| 17 | VSS | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+164 more) | GND |

### U6 OPA1654 (OPA1654AIPWR) - TSSOP-14_4.4x5mm_P0.65mm

*OPA1654 quad, TSSOP-14: 1 OUT A, 2 -IN A, 3 +IN A, 4 V+, 5 +IN B, 6 -IN B, 7 OUT B, 8 OUT C, 9 -IN C, 10 +IN C, 11 V-, 12 +IN D, 13 -IN D, 14 OUT D. Hot-leg amplifiers (A2). Units A/B/C/D = FLU/FRD/BLD/BRU. Matches.*

| Pin | Symbol pin name | Schematic net | Other ends of that net | PCB pad net |
|---:|---|---|---|---|
| 1 |  | FLU_PRE | C21.1, C25.1, R30.1 | FLU_PRE |
| 2 | - | FLU_FB | C21.2, R26.1, R30.2 | FLU_FB |
| 3 | + | FLU_PAD | U4.14 (A) | FLU_PAD |
| 4 | V+ | +9V | C34.1, C35.1, C36.1, C37.1, C74.1, C75.1, C88.1, C109.1, C110.1, Q6.2 (S), R83.1, R98.1, R106.1, R130.1, ... (+6 more) | +9V |
| 5 | + | FRD_PAD | U4.15 (B) | FRD_PAD |
| 6 | - | FRD_FB | C22.2, R27.1, R31.2 | FRD_FB |
| 7 |  | FRD_PRE | C22.1, C26.1, R31.1 | FRD_PRE |
| 8 |  | BLD_PRE | C23.1, C27.1, R32.1 | BLD_PRE |
| 9 | - | BLD_FB | C23.2, R28.1, R32.2 | BLD_FB |
| 10 | + | BLD_PAD | U5.14 (A) | BLD_PAD |
| 11 | V- | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+168 more) | GND |
| 12 | + | BRU_PAD | U5.15 (B) | BRU_PAD |
| 13 | - | BRU_FB | C24.2, R29.1, R33.2 | BRU_FB |
| 14 |  | BRU_PRE | C24.1, C28.1, R33.1 | BRU_PRE |

### U16 OPA1654 (OPA1654AIPWR) - TSSOP-14_4.4x5mm_P0.65mm

*OPA1654 quad, same pinout. Cold-leg amplifiers (A1), units A/B/C/D = FLU/FRD/BLD/BRU. Matches.*

| Pin | Symbol pin name | Schematic net | Other ends of that net | PCB pad net |
|---:|---|---|---|---|
| 1 |  | FLU_CPRE | R26.2, R118.2 | FLU_CPRE |
| 2 | - | FLU_CFB | C105.1, R118.1, R122.1 | FLU_CFB |
| 3 | + | FLU_ACC | C101.2, R114.1, R126.1 | FLU_ACC |
| 4 | V+ | +9V | C34.1, C35.1, C36.1, C37.1, C74.1, C75.1, C88.1, C109.1, C110.1, Q6.2 (S), R83.1, R98.1, R106.1, R130.1, ... (+6 more) | +9V |
| 5 | + | FRD_ACC | C102.2, R115.1, R127.1 | FRD_ACC |
| 6 | - | FRD_CFB | C106.1, R119.1, R123.1 | FRD_CFB |
| 7 |  | FRD_CPRE | R27.2, R119.2 | FRD_CPRE |
| 8 |  | BLD_CPRE | R28.2, R120.2 | BLD_CPRE |
| 9 | - | BLD_CFB | C107.1, R120.1, R124.1 | BLD_CFB |
| 10 | + | BLD_ACC | C103.2, R116.1, R128.1 | BLD_ACC |
| 11 | V- | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+168 more) | GND |
| 12 | + | BRU_ACC | C104.2, R117.1, R129.1 | BRU_ACC |
| 13 | - | BRU_CFB | C108.1, R121.1, R125.1 | BRU_CFB |
| 14 |  | BRU_CPRE | R29.2, R121.2 | BRU_CPRE |

### U4 CD4053BPW (CD4053BPWR) - TSSOP-16_4.4x5mm_P0.65mm

*CD4053B triple SPDT. Datasheet (TI): 1 BY, 2 BX, 3 CY, 4 C common, 5 CX, 6 INH, 7 VEE, 8 VSS, 9 sel C, 10 sel B, 11 sel A, 12 AX, 13 AY, 14 A common, 15 B common, 16 VDD. Common connects to Y when the select is HIGH, X when LOW. As wired: A: common 14 = FLU_PAD, AY 13 = FLU_AC (direct, select high = default), AX 12 = FLU_ATT (pad). B: common 15 = FRD_PAD, BY 1 = FRD_AC, BX 2 = FRD_ATT. C: common 4 = FLU_MICC, CY 3 = GND (grounded when COLD_SEL high = electret default), CX 5 = NC (released). INH, VEE = GND, VDD = +9V. Matches.*

| Pin | Symbol pin name | Schematic net | Other ends of that net | PCB pad net |
|---:|---|---|---|---|
| 1 | B1 | FRD_AC | C18.2, R15.1, R20.1 | FRD_AC |
| 2 | B0 | FRD_ATT | R20.2, R21.1 | FRD_ATT |
| 3 | C1 | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+165 more) | GND |
| 4 | C | FLU_MICC | C97.1, C101.1, R110.2 | FLU_MICC |
| 5 | C0 | NO_CONNECT | (nothing else: single-pin net) | - |
| 6 | INH | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+165 more) | GND |
| 7 | VEE | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+165 more) | GND |
| 8 | VSS | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+165 more) | GND |
| 9 | S3 | COLD_SEL | Q5.3 (D), R106.2, U5.9 (S3), U15.9 (S3), U15.10 (S2) | COLD_SEL |
| 10 | S2 | PAD_SELECT | C33.1, Q1.3 (D), R83.2, U5.10 (S2), U5.11 (S1) | PAD_SELECT |
| 11 | S1 | PAD_SELECT | C33.1, Q1.3 (D), R83.2, U5.10 (S2), U5.11 (S1) | PAD_SELECT |
| 12 | A0 | FLU_ATT | R18.2, R19.1 | FLU_ATT |
| 13 | A1 | FLU_AC | C17.2, R14.1, R18.1 | FLU_AC |
| 14 | A | FLU_PAD | U6.3 (+) | FLU_PAD |
| 15 | B | FRD_PAD | U6.5 (+) | FRD_PAD |
| 16 | VDD | +9V | C34.1, C35.1, C36.1, C37.1, C74.1, C75.1, C88.1, C109.1, C110.1, Q6.2 (S), R83.1, R98.1, R106.1, R130.1, ... (+6 more) | +9V |

### U5 CD4053BPW (CD4053BPWR) - TSSOP-16_4.4x5mm_P0.65mm

*Second CD4053B: A = BLD pad, B = BRU pad, C = BLD cold-leg ground. Matches the same pattern.*

| Pin | Symbol pin name | Schematic net | Other ends of that net | PCB pad net |
|---:|---|---|---|---|
| 1 | B1 | BRU_AC | C20.2, R17.1, R24.1 | BRU_AC |
| 2 | B0 | BRU_ATT | R24.2, R25.1 | BRU_ATT |
| 3 | C1 | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+165 more) | GND |
| 4 | C | BLD_MICC | C99.1, C103.1, R112.2 | BLD_MICC |
| 5 | C0 | NO_CONNECT | (nothing else: single-pin net) | - |
| 6 | INH | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+165 more) | GND |
| 7 | VEE | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+165 more) | GND |
| 8 | VSS | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+165 more) | GND |
| 9 | S3 | COLD_SEL | Q5.3 (D), R106.2, U4.9 (S3), U15.9 (S3), U15.10 (S2) | COLD_SEL |
| 10 | S2 | PAD_SELECT | C33.1, Q1.3 (D), R83.2, U4.10 (S2), U4.11 (S1) | PAD_SELECT |
| 11 | S1 | PAD_SELECT | C33.1, Q1.3 (D), R83.2, U4.10 (S2), U4.11 (S1) | PAD_SELECT |
| 12 | A0 | BLD_ATT | R22.2, R23.1 | BLD_ATT |
| 13 | A1 | BLD_AC | C19.2, R16.1, R22.1 | BLD_AC |
| 14 | A | BLD_PAD | U6.10 (+) | BLD_PAD |
| 15 | B | BRU_PAD | U6.12 (+) | BRU_PAD |
| 16 | VDD | +9V | C34.1, C35.1, C36.1, C37.1, C74.1, C75.1, C88.1, C109.1, C110.1, Q6.2 (S), R83.1, R98.1, R106.1, R130.1, ... (+6 more) | +9V |

### U15 CD4053BPW (CD4053BPWR) - TSSOP-16_4.4x5mm_P0.65mm

*Third CD4053B: B section grounds FRD_MICC (common 15, BY 1 = GND, BX 2 = NC, sel B 10 = COLD_SEL), C section grounds BRU_MICC (common 4, CY 3 = GND, CX 5 = NC, sel C 9 = COLD_SEL). A section unused (sel A = GND, AY = GND, AX/common NC). Matches.*

| Pin | Symbol pin name | Schematic net | Other ends of that net | PCB pad net |
|---:|---|---|---|---|
| 1 | B1 | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 2 | B0 | NO_CONNECT | (nothing else: single-pin net) | - |
| 3 | C1 | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 4 | C | BRU_MICC | C100.1, C104.1, R113.2 | BRU_MICC |
| 5 | C0 | NO_CONNECT | (nothing else: single-pin net) | - |
| 6 | INH | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 7 | VEE | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 8 | VSS | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 9 | S3 | COLD_SEL | Q5.3 (D), R106.2, U4.9 (S3), U5.9 (S3) | COLD_SEL |
| 10 | S2 | COLD_SEL | Q5.3 (D), R106.2, U4.9 (S3), U5.9 (S3) | COLD_SEL |
| 11 | S1 | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 12 | A0 | NO_CONNECT | (nothing else: single-pin net) | - |
| 13 | A1 | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 14 | A | NO_CONNECT | (nothing else: single-pin net) | - |
| 15 | B | FRD_MICC | C98.1, C102.1, R111.2 | FRD_MICC |
| 16 | VDD | +9V | C34.1, C35.1, C36.1, C37.1, C74.1, C75.1, C88.1, C109.1, C110.1, Q6.2 (S), R83.1, R98.1, R106.1, R130.1, ... (+6 more) | +9V |

### U7 PCM1864DBT (PCM1864DBTR) - TSSOP-30_4.4x7.8mm_P0.5mm

*PCM1864DBT ADC. Datasheet (TI): 1 VINL2, 2 VINR2, 3 VINL1, 4 VINR1, 5 MICBIAS (may be left open), 6 VREF (1 uF), 7 AGND, 8 AVDD (0.1 + 10 uF), 9 XO, 10 XI (crystal/1.8 V clock, unused), 11 LDO (0.1 + 10 uF), 12 DGND, 13 DVDD, 14 IOVDD, 15 SCKI (3.3 V master clock), 16 LRCK, 17 BCK, 18 DOUT, 19 GPIO3, 20 GPIO2, 21 GPIO1, 22 GPIO0 (DOUT2 in I2C mode), 23 SDA, 24 SCL, 25 MS/AD (I2C address), 26 MD0 (low = I2C), 27 VINL4, 28 VINR4, 29 VINL3, 30 VINR3. As wired: channel map is ADC1-L = FLU, ADC1-R = FRD, ADC2-L = BLD, ADC2-R = BRU; AD and MD0 low = I2C mode, address 0x4A. Matches.*

| Pin | Symbol pin name | Schematic net | Other ends of that net | PCB pad net |
|---:|---|---|---|---|
| 1 | VINL2/VIN1M | BLD_ADC | C31.1, R36.2, R40.1 | BLD_ADC |
| 2 | VINR2/VIN2M | BRU_ADC | C32.1, R37.2, R41.1 | BRU_ADC |
| 3 | VINL1/VIN1P | FLU_ADC | C29.1, R34.2, R38.1 | FLU_ADC |
| 4 | VINR1/VIN2P | FRD_ADC | C30.1, R35.2, R39.1 | FRD_ADC |
| 5 | Mic_Bias | NO_CONNECT | (nothing else: single-pin net) | - |
| 6 | VREF | ADC_VREF | C39.1, C40.1 | ADC_VREF |
| 7 | AGND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+165 more) | GND |
| 8 | AVDD | +3V3_A | C8.1, C41.1, C42.1, C54.1, C55.1, C64.1, U2.5 (OUT), U9.1 (CPVDD), U9.8 (AVDD) | +3V3_A |
| 9 | XO | NO_CONNECT | (nothing else: single-pin net) | - |
| 10 | XI | NO_CONNECT | (nothing else: single-pin net) | - |
| 11 | LDO | ADC_LDO | C43.1, C62.1 | ADC_LDO |
| 12 | DGND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+165 more) | GND |
| 13 | DVDD | +3V3_DC | C44.1, C45.1, C56.1, C96.1, TP12.1, U9.20 (DVDD), U14.5 (OUT) | +3V3_DC |
| 14 | IOVDD | +3V3_DC | C44.1, C45.1, C56.1, C96.1, TP12.1, U9.20 (DVDD), U14.5 (OUT) | +3V3_DC |
| 15 | SCKI | ADC_MCLK_IC | R46.2 | ADC_MCLK_IC |
| 16 | LRCK | ADC_LRCLK_IC | R47.2 | ADC_LRCLK_IC |
| 17 | BCK | ADC_BCLK_IC | R48.2 | ADC_BCLK_IC |
| 18 | DOUT | ADC_TDM_IC | R49.1 | ADC_TDM_IC |
| 19 | GPIO3/INTC | NO_CONNECT | (nothing else: single-pin net) | - |
| 20 | GPIO2/INTB/DMCLK | NO_CONNECT | (nothing else: single-pin net) | - |
| 21 | GPIO1/INTA/DMIN | NO_CONNECT | (nothing else: single-pin net) | - |
| 22 | MISO/GPIO0/DMIN2 | ADC_DOUT2_IC | R69.1 | ADC_DOUT2_IC |
| 23 | MOSI/SDA | I2C_SDA | J3.12 (Pin_12), R44.2, U8.18 (D18/SDA), U10.7 (SDA) | I2C_SDA |
| 24 | MC/SCL | I2C_SCL | J3.10 (Pin_10), R45.2, U8.19 (D19/SCL), U10.8 (SCL) | I2C_SCL |
| 25 | MS/AD | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+165 more) | GND |
| 26 | MD0 | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+165 more) | GND |
| 27 | VINL4/VIN4M | NO_CONNECT | (nothing else: single-pin net) | - |
| 28 | VINR4/VIN3M | NO_CONNECT | (nothing else: single-pin net) | - |
| 29 | VINL3/VIN4P | NO_CONNECT | (nothing else: single-pin net) | - |
| 30 | VINR3/VIN3P | NO_CONNECT | (nothing else: single-pin net) | - |

### U9 PCM5102A (PCM5102APWR) - TSSOP-20_4.4x6.5mm_P0.65mm

*PCM5102A DAC. Datasheet (TI): 1 CPVDD, 2 CAPP, 3 CPGND, 4 CAPM, 5 VNEG, 6 OUTL, 7 OUTR, 8 AVDD, 9 AGND, 10 DEMP, 11 FLT, 12 SCK, 13 BCK, 14 DIN, 15 LRCK, 16 FMT, 17 XSMT, 18 LDOO, 19 DGND, 20 DVDD. As wired: DEMP = GND (off), FLT = GND (normal latency), SCK = GND (no master clock: the chip runs its BCK PLL, which TI allows when SCK is grounded), FMT = GND (I2S), XSMT from Teensy 34 with 10k pull-down, CAPP-CAPM 2.2 uF, VNEG 2.2 uF, LDOO 1 uF. Matches.*

| Pin | Symbol pin name | Schematic net | Other ends of that net | PCB pad net |
|---:|---|---|---|---|
| 1 | CPVDD | +3V3_A | C8.1, C41.1, C42.1, C54.1, C55.1, C64.1, U2.5 (OUT), U7.8 (AVDD) | +3V3_A |
| 2 | CAPP | DAC_CAPP | C51.1 | DAC_CAPP |
| 3 | CPGND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 4 | CAPM | DAC_CAPM | C51.2 | DAC_CAPM |
| 5 | VNEG | DAC_VNEG | C52.1 | DAC_VNEG |
| 6 | OUTL | DAC_L | R62.1 | DAC_L |
| 7 | OUTR | DAC_R | R63.1 | DAC_R |
| 8 | AVDD | +3V3_A | C8.1, C41.1, C42.1, C54.1, C55.1, C64.1, U2.5 (OUT), U7.8 (AVDD) | +3V3_A |
| 9 | AGND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 10 | DEMP | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 11 | FLT | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 12 | SCK | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 13 | BCK | DAC_BCLK_IC | R57.2 | DAC_BCLK_IC |
| 14 | DIN | DAC_DIN_IC | R58.2 | DAC_DIN_IC |
| 15 | LRCK | DAC_LRCLK_IC | R59.2 | DAC_LRCLK_IC |
| 16 | FMT | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 17 | XSMT | DAC_MUTE_IC | R60.1, R61.2 | DAC_MUTE_IC |
| 18 | LDOO | DAC_LDO | C53.1 | DAC_LDO |
| 19 | DGND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+162 more) | GND |
| 20 | DVDD | +3V3_DC | C44.1, C45.1, C56.1, C96.1, TP12.1, U7.13 (DVDD), U7.14 (IOVDD), U14.5 (OUT) | +3V3_DC |

### U10 TPA6130A2RTJ (TPA6130A2RTJR) - WQFN-20-1EP_4x4mm_P0.5mm_EP2.7x2.7mm

*TPA6130A2RTJ headphone amp. Datasheet (TI): 1 LEFTINM, 2 LEFTINP, 3 GND, 4 RIGHTINP, 5 RIGHTINM, 6 /SD (active low, VIH 1.3 V, 5 V tolerant), 7 SDA, 8 SCL (5 V tolerant, work with 3.3 V pull-ups), 9/10 GND, 11 HPRIGHT, 12 VDD, 13 GND, 14 HPLEFT, 15/16 CPVSS, 17 CPN, 18 CPP, 19 GND, 20 VDD, pad GND. I2C address 0x60. As wired: single-ended drive into INM with INP AC-grounded through matched caps, 1 uF charge-pump caps, SD from Teensy 33 with 100k pull-down. Matches.*

| Pin | Symbol pin name | Schematic net | Other ends of that net | PCB pad net |
|---:|---|---|---|---|
| 1 | LEFTINM | HP_IN_L | C57.2 | HP_IN_L |
| 2 | LEFTINP | HP_INP_L | C86.1 | HP_INP_L |
| 3 | GND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+163 more) | GND |
| 4 | RIGHTINP | HP_INP_R | C87.1 | HP_INP_R |
| 5 | RIGHTINM | HP_IN_R | C58.2 | HP_IN_R |
| 6 | ~{SD} | HP_ENABLE | R64.1, U8.33 (D33) | HP_ENABLE |
| 7 | SDA | I2C_SDA | J3.12 (Pin_12), R44.2, U7.23 (MOSI/SDA), U8.18 (D18/SDA) | I2C_SDA |
| 8 | SCL | I2C_SCL | J3.10 (Pin_10), R45.2, U7.24 (MC/SCL), U8.19 (D19/SCL) | I2C_SCL |
| 9 | GND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+163 more) | GND |
| 10 | GND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+163 more) | GND |
| 11 | HPRIGHT | HP_OUT_R | R66.1 | HP_OUT_R |
| 12 | VDD | +5V | C4.1, C5.1, C6.1, C7.1, C61.1, C65.1, C95.1, D3.2 (A), D13.1 (K), J3.1 (Pin_1), K1.1, L1.2, Q8.2 (S), R1.1, ... (+9 more) | +5V |
| 13 | GND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+163 more) | GND |
| 14 | HPLEFT | HP_OUT_L | R65.1 | HP_OUT_L |
| 15 | CPVSS | HP_VSS | C60.1 | HP_VSS |
| 16 | CPVSS | HP_VSS | C60.1 | HP_VSS |
| 17 | CPN | HP_CPN | C59.2 | HP_CPN |
| 18 | CPP | HP_CPP | C59.1 | HP_CPP |
| 19 | GND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+163 more) | GND |
| 20 | VDD_CP | +5V | C4.1, C5.1, C6.1, C7.1, C61.1, C65.1, C95.1, D3.2 (A), D13.1 (K), J3.1 (Pin_1), K1.1, L1.2, Q8.2 (S), R1.1, ... (+9 more) | +5V |
| 21 | EP | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+163 more) | GND |

### U8 Teensy 4.1 (TEENSY41) - Teensy41_Socket

*Teensy 4.1 module (socketed). Pin map in section 8.*

| Pin | Symbol pin name | Schematic net | Other ends of that net | PCB pad net |
|---:|---|---|---|---|
| 0 | D0/RX1 | MIC5_CTRL | R102.1 | MIC5_CTRL |
| 1 | D1/TX1 | MIC9_CTRL | R99.1 | MIC9_CTRL |
| 2 | D2/OUT2 | DAC_DIN | R58.1, TP11.1 | DAC_DIN |
| 3 | D3/LRCLK2 | DAC_LRCLK | R59.1, TP10.1 | DAC_LRCLK |
| 4 | D4/BCLK2 | DAC_BCLK | R57.1, TP9.1 | DAC_BCLK |
| 5 | D5 | LINE_MUTE | R84.1 | LINE_MUTE |
| 6 | D6 | ADC_DOUT2 | R69.2, TP7.1 | ADC_DOUT2 |
| 7 | D7/OUT1A | TFT_RST | J3.4 (Pin_4) | TFT_RST |
| 8 | D8/IN1 | ADC_TDM | R49.2, TP6.1 | ADC_TDM |
| 9 | D9 | TFT_DC | J3.5 (Pin_5) | TFT_DC |
| 10 | D10/CS | TFT_CS | J3.3 (Pin_3) | TFT_CS |
| 11 | D11/MOSI | SPI_MOSI | J3.6 (Pin_6) | SPI_MOSI |
| 12 | D12/MISO | SPI_MISO | J3.9 (Pin_9) | SPI_MISO |
| 13 | D13/SCK | SPI_SCK | J3.7 (Pin_7) | SPI_SCK |
| 14 | D14 | CTP_RST | J3.11 (Pin_11) | CTP_RST |
| 15 | D15 | VBUS_SENSE | C78.1, R77.2, R78.1 | VBUS_SENSE |
| 16 | D16 | BAT_SENSE | C89.1, R89.2, R90.1 | BAT_SENSE |
| 17 | D17 | CHG_STAT_N | R94.2, U13.9 (~{CHG}) | CHG_STAT_N |
| 18 | D18/SDA | I2C_SDA | J3.12 (Pin_12), R44.2, U7.23 (MOSI/SDA), U10.7 (SDA) | I2C_SDA |
| 19 | D19/SCL | I2C_SCL | J3.10 (Pin_10), R45.2, U7.24 (MC/SCL), U10.8 (SCL) | I2C_SCL |
| 20 | D20/LRCLK1 | ADC_LRCLK | R47.1, TP5.1 | ADC_LRCLK |
| 21 | D21/BCLK1 | ADC_BCLK | R48.1, TP4.1 | ADC_BCLK |
| 22 | D22 | TOUCH_IRQ | J3.13 (Pin_13) | TOUCH_IRQ |
| 23 | D23/MCLK1 | ADC_MCLK | R46.1, TP3.1 | ADC_MCLK |
| 24 | D24 | KEEP_ON | D15.2 (A) | KEEP_ON |
| 25 | D25 | PGOOD_N | R95.2, U13.7 (~{PGOOD}) | PGOOD_N |
| 26 | D26 | NAV_ENC_A | C93.1, R96.2, SW4.8 (E_A) | NAV_ENC_A |
| 27 | D27 | NAV_ENC_B | C94.1, R97.2, SW4.7 (E_B) | NAV_ENC_B |
| 28 | D28 | REC_BUTTON | C47.1, D18.2 (A), R50.2 | REC_BUTTON |
| 29 | D29 | GAIN_A | C48.1, R51.2, SW3.A (A) | GAIN_A |
| 30 | D30 | GAIN_B | C49.1, R52.2, SW3.B (B) | GAIN_B |
| 31 | D31 | GAIN_PUSH | C50.1, D19.2 (A), R53.2 | GAIN_PUSH |
| 32 | D32 | PAD_CTRL | R42.1 | PAD_CTRL |
| 33 | D33 | HP_ENABLE | R64.1, U10.6 (~{SD}) | HP_ENABLE |
| 34 | D34 | DAC_MUTE | R61.1 | DAC_MUTE |
| 35 | D35 | REC_LED | R55.1 | REC_LED |
| 36 | D36 | NAV_UP | C69.1, R70.2, SW4.C (C/UP) | NAV_UP |
| 37 | D37 | NAV_DOWN | C70.1, R71.2, SW4.A (A/DOWN) | NAV_DOWN |
| 38 | D38 | NAV_LEFT | C71.1, R72.2, SW4.D (D/LEFT) | NAV_LEFT |
| 39 | D39 | NAV_RIGHT | C72.1, R73.2, SW4.B (B/RIGHT) | NAV_RIGHT |
| 40 | D40 | NAV_PUSH | C73.1, R74.2, SW4.5 (PUSH) | NAV_PUSH |
| 41 | D41 | COLD_CTRL | R107.1 | COLD_CTRL |
| 3V3A | 3V3 | +3V3_D | R44.1, R45.1, R50.1, R51.1, R52.1, R53.1, R70.1, R71.1, R72.1, R73.1, R74.1, R94.1, R95.1, R96.1, ... (+1 more) | +3V3_D |
| 3V3B | 3V3 | NO_CONNECT | (nothing else: single-pin net) | - |
| GND1 | GND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+166 more) | GND |
| GND2 | GND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+166 more) | GND |
| GND3 | GND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+166 more) | GND |
| VIN | VIN | TEENSY_VIN | C46.1, D3.1 (K) | TEENSY_VIN |

### Datasheet cross-check summary

Pin functions were compared against the current manufacturer datasheets on 2026-09-15 (TI: TPS61175, TPS62160, TPS7A20, BQ24074, PCM1864, PCM5102A, TPA6130A2, CD4053B; ADI: ADP7142). Every power, ground, feedback, enable, mode and I/O pin of U1, U2, U3, U4, U5, U7, U9, U10, U11, U12, U13, U14, U15 lands where the datasheet says it should; the CD4053 common/X/Y assignment and select polarity give 'direct' and 'cold leg grounded' as the power-up defaults; the BQ24074 strapping (CE low, EN2 high, EN1 low, TMR low, ITERM open) implements the 0.74 A / 1.46 A / no-timer intent in the design notes; PCM5102A mode pins give I2S, normal filter, no de-emphasis, BCK-PLL clocking; PCM1864 is in I2C mode at 0x4A with GPIO0 as the second data line. OPA1654 units use the standard quad pinout. Transistor and diode pin orders are checked in section 5. **The Teensy 4.1 socket footprint (U8) failed this check** and is the one real error the review found; see the box below and section 16.

> **Teensy 4.1 socket, found 2026-09-15 (this is what stopped the order).** The project footprint `Teensy41_Socket` was compared against PJRC's dimension drawing (`dimensions_teensy41.png`), the PJRC pinout card and the XenGi `Teensy4.1` symbol (pins 1-48 numbered DIP-style). Two errors, both dating from Rev B, never caught because no board was built: (1) the two socket rows were drawn 17.78 mm apart; the module's rows are 15.24 mm (0.6 in) apart on a 17.78 mm wide body, so the module could not have been plugged in; (2) the right row, USB end first, was drawn VIN, GND, 23 ... 13, 41 ... 33, GND, 3V3 but the module is VIN, GND, **3V3**, 23 ... 13, **GND**, 41 ... 33, so 22 of the 24 right-row pads sat one position off: ADC_MCLK would have landed on the Teensy's 3.3 V pin, every right-side signal on the neighbouring pin, and +3V3_D on I/O 33. The left row (GND, 0 to 12, 3V3, 24 to 32) was correct. The schematic, netlist and BOM are unaffected: only pad positions changed. Fix: `tools/generate_footprints.py` corrected (rows 15.24 mm, right order VIN GND 3V3B 23-13 GND3 41-33, outline 17.78 wide), the second 3.3 V pin (3V3B) made a no-connect in `tools/generate_schematic.py` (both 3.3 V pins are the same regulator output inside the module), and the board fully re-routed through the Rev C3 pipeline (`tools/full_route_body.ps1`, Freerouting 1.9) because moving the right pin row 2.54 mm inward took away the corridor six long control lines used; then the Rev C3 post passes, DRC at every severity, audio audits and a rebuilt fab package. Sections 8 and 13 below describe the corrected board.

## 5. Transistors and diodes

SOT-23 pin order matters: KiCad's 2N7002 symbol is 1 = G, 2 = S, 3 = D, and the AO3401A symbol is 1 = G, 2 = S, 3 = D. Both match the Nexperia 2N7002 and AOS AO3401A datasheets (gate pin 1, source pin 2, drain pin 3). For the diodes, KiCad pin 1 = cathode (K) and pin 2 = anode (A).

| Ref | Part | Pin 1 | Pin 2 | Pin 3 | Role |
|---|---|---|---|---|---|
| Q6 | AO3401A AO3401A | G: MIC9_G [MIC9_G] | S: +9V [+9V] | D: BIAS_SRC [BIAS_SRC] | 9 V mic-bias high-side P-FET (+9V -> BIAS_SRC) |
| Q7 | 2N7002 2N7002NXAKR | G: MIC9_CTRL_G [MIC9_CTRL_G] | S: GND [GND] | D: MIC9_G [MIC9_G] | Gate driver for Q6 (MIC9_CTRL high -> Q6 on) |
| Q8 | AO3401A AO3401A | G: MIC5_G [MIC5_G] | S: +5V [+5V] | D: BIAS5 [BIAS5] | 5 V mic-bias high-side P-FET (+5V -> BIAS5 -> D24 -> BIAS_SRC) |
| Q9 | 2N7002 2N7002NXAKR | G: MIC5_CTRL_G [MIC5_CTRL_G] | S: GND [GND] | D: MIC5_G [MIC5_G] | Gate driver for Q8 (MIC5_CTRL high -> Q8 on) |
| Q3 | AO3401A AO3401A | G: REC_SW [REC_SW] | S: VBAT [VBAT] | D: PWR_LATCH_MID [PWR_LATCH_MID] | Soft-power latch, RECORD side (P-FET, source VBAT) |
| Q4 | AO3401A AO3401A | G: GAIN_SW [GAIN_SW] | S: PWR_LATCH_MID [PWR_LATCH_MID] | D: BOOST_EN [BOOST_EN] | Soft-power latch, encoder-push side (P-FET, in series with Q3, drain -> BOOST_EN) |
| Q5 | 2N7002 2N7002NXAKR | G: COLD_CTRL_G [COLD_CTRL_G] | S: GND [GND] | D: COLD_SEL [COLD_SEL] | Cold-leg mode level shifter: COLD_CTRL high -> COLD_SEL low = cold legs released (dynamic/balanced mode) |
| Q1 | 2N7002 2N7002NXAKR | G: PAD_CTRL_G [PAD_CTRL_G] | S: GND [GND] | D: PAD_SELECT [PAD_SELECT] | Pad select level shifter: Teensy PAD_CTRL high -> pulls PAD_SELECT (0/9 V) low = -9.7 dB pad in |
| Q2 | 2N7002 2N7002NXAKR | G: LINE_MUTE_G [LINE_MUTE_G] | S: GND [GND] | D: LINE_MUTE_K [LINE_MUTE_K] | Relay coil driver: LINE_MUTE high -> K1 energised -> line jack tips grounded |

Diodes (K = cathode = pin 1, A = anode = pin 2):

| Ref | Part | Pin 1 (K) net | Pin 2 (A) net | Current flows | Role |
|---|---|---|---|---|---|
| D1 | B340A 40V 3A B340A-13-F | VBOOST_IN [VBOOST_IN] | +9V_FUSED [+9V_FUSED] | +9V_FUSED -> VBOOST_IN | barrel -> VBOOST_IN OR-ing |
| D2 | SMBJ12A SMBJ12A | VBOOST_IN [VBOOST_IN] | GND [GND] | GND -> VBOOST_IN | SMBJ12A TVS clamp on VBOOST_IN |
| D3 | SS14 SS14 | TEENSY_VIN [TEENSY_VIN] | +5V [+5V] | +5V -> TEENSY_VIN | +5V -> Teensy VIN (blocks USB back-feed) |
| D4 | POWER BLUE WP7113QBC/D | GND [GND] | PWR_LED_A [PWR_LED_A] | PWR_LED_A -> GND | blue power LED (front wall) |
| D5 | RECORD RED WP7113ID | GND [GND] | REC_LED_A [REC_LED_A] | REC_LED_A -> GND | red record LED (front wall) |
| D10 | B340A 40V 3A B340A-13-F | VBOOST_IN [VBOOST_IN] | VBUS_FUSED [VBUS_FUSED] | VBUS_FUSED -> VBOOST_IN | USB -> VBOOST_IN OR-ing |
| D11 | USBLC6-2SC6 | 1=USB_DP, 2=GND, 3=USB_DM, 4=USB_DM, 5=VBUS, 6=USB_DP | | | USBLC6-2SC6 USB ESD array |
| D12 | B340A 40V 3A B340A-13-F | +10V5 [+10V5] | BOOST_SW [BOOST_SW] | BOOST_SW -> +10V5 | boost rectifier (SW -> +10V5) |
| D13 | 1N4148W 1N4148W-7-F | +5V [+5V] | LINE_MUTE_K [LINE_MUTE_K] | LINE_MUTE_K -> +5V | relay flyback across K1 coil |
| D14 | B340A 40V 3A B340A-13-F | VBOOST_IN [VBOOST_IN] | BAT_SYS [BAT_SYS] | BAT_SYS -> VBOOST_IN | charger OUT / battery -> VBOOST_IN OR-ing |
| D15 | 1N4148W 1N4148W-7-F | BOOST_EN [BOOST_EN] | KEEP_ON [KEEP_ON] | KEEP_ON -> BOOST_EN | KEEP_ON -> BOOST_EN |
| D16 | 1N4148W 1N4148W-7-F | BOOST_EN [BOOST_EN] | VBUS_FUSED [VBUS_FUSED] | VBUS_FUSED -> BOOST_EN | USB present -> BOOST_EN |
| D17 | 1N4148W 1N4148W-7-F | BOOST_EN [BOOST_EN] | +9V_FUSED [+9V_FUSED] | +9V_FUSED -> BOOST_EN | barrel present -> BOOST_EN |
| D18 | 1N4148W 1N4148W-7-F | REC_SW [REC_SW] | REC_BUTTON [REC_BUTTON] | REC_BUTTON -> REC_SW | isolates REC_SW from the Teensy REC_BUTTON input |
| D19 | 1N4148W 1N4148W-7-F | GAIN_SW [GAIN_SW] | GAIN_PUSH [GAIN_PUSH] | GAIN_PUSH -> GAIN_SW | isolates GAIN_SW from GAIN_PUSH |
| D24 | BAT54 BAT54-7-F | BIAS_SRC [BIAS_SRC] | BIAS5 [BIAS5] | BIAS5 -> BIAS_SRC | BAT54: 5 V bias -> BIAS_SRC, blocks 9 V from the +5V rail |

Input ESD diodes D6-D9 (hot legs) and D20-D23 (cold legs) are Nexperia PESD12VL1BA (12 V bidirectional, low capacitance) from each RAW/RAWC input to CHASSIS:

| Ref | Pin 1 | Pin 2 |
|---|---|---|
| D6 | FLU_RAW [FLU_RAW] | CHASSIS [CHASSIS] |
| D7 | FRD_RAW [FRD_RAW] | CHASSIS [CHASSIS] |
| D8 | BLD_RAW [BLD_RAW] | CHASSIS [CHASSIS] |
| D9 | BRU_RAW [BRU_RAW] | CHASSIS [CHASSIS] |
| D20 | FLU_RAWC [FLU_RAWC] | CHASSIS [CHASSIS] |
| D21 | FRD_RAWC [FRD_RAWC] | CHASSIS [CHASSIS] |
| D22 | BLD_RAWC [BLD_RAWC] | CHASSIS [CHASSIS] |
| D23 | BRU_RAWC [BRU_RAWC] | CHASSIS [CHASSIS] |

## 6. Connectors, switches, relay

### J2 AMBISONIC MIC RJ45 (RJHSE-5380)

| Pin | Pin name | Net | Other ends | PCB pad net |
|---|---|---|---|---|
| 1 |  | FLU_RAW | D6.1 (A1), R10.1 | FLU_RAW |
| 2 |  | FLU_RAWC | D20.1 (A1), R110.1 | FLU_RAWC |
| 3 |  | FRD_RAW | D7.1 (A1), R11.1 | FRD_RAW |
| 4 |  | BLD_RAW | D8.1 (A1), R12.1 | BLD_RAW |
| 5 |  | BLD_RAWC | D22.1 (A1), R112.1 | BLD_RAWC |
| 6 |  | FRD_RAWC | D21.1 (A1), R111.1 | FRD_RAWC |
| 7 |  | BRU_RAW | D9.1 (A1), R13.1 | BRU_RAW |
| 8 |  | BRU_RAWC | D23.1 (A1), R113.1 | BRU_RAWC |
| SH |  | CHASSIS | C12.1, C13.2, C14.2, C15.2, C16.2, C97.2, C98.2, C99.2, C100.2, D6.2 (A2), D7.2 (A2), D8.2 (A2), D9.2 (A2), D20.2 (A2), ... (+6 more) | CHASSIS |

### J9 USB-C POWER + DATA (TYPE-C-31-M-12)

| Pin | Pin name | Net | Other ends | PCB pad net |
|---|---|---|---|---|
| A1 | GND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+165 more) | GND |
| A12 | GND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+165 more) | GND |
| A4 | VBUS | VBUS | D11.5 (VBUS), F2.1, R77.1 | VBUS |
| A5 | CC1 | USB_CC1 | R75.1 | USB_CC1 |
| A6 | D+ | USB_DP | D11.1 (I/O1), D11.6 (I/O1), TP1.1 | USB_DP |
| A7 | D- | USB_DM | D11.3 (I/O2), D11.4 (I/O2), TP2.1 | USB_DM |
| A8 | SBU1 | __unnamed_0 | (nothing else: single-pin net) | - |
| A9 | VBUS | VBUS | D11.5 (VBUS), F2.1, R77.1 | VBUS |
| B1 | GND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+165 more) | GND |
| B12 | GND | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+165 more) | GND |
| B4 | VBUS | VBUS | D11.5 (VBUS), F2.1, R77.1 | VBUS |
| B5 | CC2 | USB_CC2 | R76.1 | USB_CC2 |
| B6 | D+ | USB_DP | D11.1 (I/O1), D11.6 (I/O1), TP1.1 | USB_DP |
| B7 | D- | USB_DM | D11.3 (I/O2), D11.4 (I/O2), TP2.1 | USB_DM |
| B8 | SBU2 | __unnamed_1 | (nothing else: single-pin net) | - |
| B9 | VBUS | VBUS | D11.5 (VBUS), F2.1, R77.1 | VBUS |
| SH | SHIELD | CHASSIS | C12.1, C13.2, C14.2, C15.2, C16.2, C97.2, C98.2, C99.2, C100.2, D6.2 (A2), D7.2 (A2), D8.2 (A2), D9.2 (A2), D20.2 (A2), ... (+6 more) | CHASSIS |

### J1 9V DC IN (PJ-102AH)

| Pin | Pin name | Net | Other ends | PCB pad net |
|---|---|---|---|---|
| 1 |  | +9V_IN | F1.1 | +9V_IN |
| 2 |  | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+167 more) | GND |
| 3 |  | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+167 more) | GND |

### J10 BATTERY 1S LiPo (B2B-PH-K-S)

| Pin | Pin name | Net | Other ends | PCB pad net |
|---|---|---|---|---|
| 1 | Pin_1 | VBAT | C92.1, Q3.2 (S), R86.1, R87.1, R89.1, U13.2 (BAT), U13.3 (BAT) | VBAT |
| 2 | Pin_2 | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+168 more) | GND |

### J3 MSP3526 TFT 3.5IN 14PIN SOCKET (PPTC141LFBN-RC)

| Pin | Pin name | Net | Other ends | PCB pad net |
|---|---|---|---|---|
| 1 | Pin_1 | +5V | C4.1, C5.1, C6.1, C7.1, C61.1, C65.1, C95.1, D3.2 (A), D13.1 (K), K1.1, L1.2, Q8.2 (S), R1.1, R3.1, ... (+10 more) | +5V |
| 2 | Pin_2 | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+168 more) | GND |
| 3 | Pin_3 | TFT_CS | U8.10 (D10/CS) | TFT_CS |
| 4 | Pin_4 | TFT_RST | U8.7 (D7/OUT1A) | TFT_RST |
| 5 | Pin_5 | TFT_DC | U8.9 (D9) | TFT_DC |
| 6 | Pin_6 | SPI_MOSI | U8.11 (D11/MOSI) | SPI_MOSI |
| 7 | Pin_7 | SPI_SCK | U8.13 (D13/SCK) | SPI_SCK |
| 8 | Pin_8 | TFT_LED | R56.2 | TFT_LED |
| 9 | Pin_9 | SPI_MISO | U8.12 (D12/MISO) | SPI_MISO |
| 10 | Pin_10 | I2C_SCL | R45.2, U7.24 (MC/SCL), U8.19 (D19/SCL), U10.8 (SCL) | I2C_SCL |
| 11 | Pin_11 | CTP_RST | U8.14 (D14) | CTP_RST |
| 12 | Pin_12 | I2C_SDA | R44.2, U7.23 (MOSI/SDA), U8.18 (D18/SDA), U10.7 (SDA) | I2C_SDA |
| 13 | Pin_13 | TOUCH_IRQ | U8.22 (D22) | TOUCH_IRQ |
| 14 | Pin_14 | __unnamed_27 | (nothing else: single-pin net) | - |

### J4 1/4in BINAURAL LINE OUT (NRJ6HF)

| Pin | Pin name | Net | Other ends | PCB pad net |
|---|---|---|---|---|
| R |  | LINE_JACK_R | K1.6 | LINE_JACK_R |
| S |  | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+168 more) | GND |
| T |  | LINE_JACK_L | K1.3 | LINE_JACK_L |

### J5 1/8in BINAURAL HEADPHONE OUT (SJ1-3533NG)

| Pin | Pin name | Net | Other ends | PCB pad net |
|---|---|---|---|---|
| R |  | HP_JACK_R | R66.2 | HP_JACK_R |
| S |  | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+168 more) | GND |
| T |  | HP_JACK_L | R65.2 | HP_JACK_L |

### K1 G6K-2F-Y 5VDC (G6K-2F-Y DC5)

| Pin | Pin name | Net | Other ends | PCB pad net |
|---|---|---|---|---|
| 1 |  | +5V | C4.1, C5.1, C6.1, C7.1, C61.1, C65.1, C95.1, D3.2 (A), D13.1 (K), J3.1 (Pin_1), L1.2, Q8.2 (S), R1.1, R3.1, ... (+10 more) | +5V |
| 2 |  | LINE_L | C57.1, C67.1, R62.2 | LINE_L |
| 3 |  | LINE_JACK_L | J4.T | LINE_JACK_L |
| 4 |  | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+167 more) | GND |
| 5 |  | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+167 more) | GND |
| 6 |  | LINE_JACK_R | J4.R | LINE_JACK_R |
| 7 |  | LINE_R | C58.1, C68.1, R63.2 | LINE_R |
| 8 |  | LINE_MUTE_K | D13.2 (A), Q2.3 (D) | LINE_MUTE_K |

### SW2 RECORD START/STOP (TS02-66-150-BK-160-LCR-D)

| Pin | Pin name | Net | Other ends | PCB pad net |
|---|---|---|---|---|
| 1 | 1 | REC_SW | D18.1 (K), Q3.1 (G), R86.2 | REC_SW |
| 2 | 2 | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+168 more) | GND |

### SW3 MASTER GAIN (EC11E15244G1)

| Pin | Pin name | Net | Other ends | PCB pad net |
|---|---|---|---|---|
| A | A | GAIN_A | C48.1, R51.2, U8.29 (D29) | GAIN_A |
| B | B | GAIN_B | C49.1, R52.2, U8.30 (D30) | GAIN_B |
| C | C | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+167 more) | GND |
| S1 | S1 | GAIN_SW | D19.1 (K), Q4.1 (G), R87.2 | GAIN_SW |
| S2 | S2 | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+167 more) | GND |

### SW4 TFT MENU NAV (RKJXT1F42001)

| Pin | Pin name | Net | Other ends | PCB pad net |
|---|---|---|---|---|
| 5 | PUSH | NAV_PUSH | C73.1, R74.2, U8.40 (D40) | NAV_PUSH |
| 6 | COM | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+167 more) | GND |
| 7 | E_B | NAV_ENC_B | C94.1, R97.2, U8.27 (D27) | NAV_ENC_B |
| 8 | E_A | NAV_ENC_A | C93.1, R96.2, U8.26 (D26) | NAV_ENC_A |
| 9 | E_C | GND | C1.2, C2.2, C3.2, C5.2, C6.2, C7.2, C8.2, C9.2, C10.2, C11.2, C12.2, C29.2, C30.2, C31.2, ... (+167 more) | GND |
| 10 | NC | __unnamed_26 | (nothing else: single-pin net) | - |
| A | A/DOWN | NAV_DOWN | C70.1, R71.2, U8.37 (D37) | NAV_DOWN |
| B | B/RIGHT | NAV_RIGHT | C72.1, R73.2, U8.39 (D39) | NAV_RIGHT |
| C | C/UP | NAV_UP | C69.1, R70.2, U8.36 (D36) | NAV_UP |
| D | D/LEFT | NAV_LEFT | C71.1, R72.2, U8.38 (D38) | NAV_LEFT |

K1 sense to verify at bring-up (Omron G6K-2F-Y drawing): coil 1 (+) / 8 (-); contacts 2/7 NC, 3/6 COM, 4/5 NO. As wired: COM 3/6 = jack tips, NC 2/7 = LINE_L/R (audio passes with the coil off), NO 4/5 = GND (tips grounded when energised).

## 7. Every net, with its pins

212 nets. Power and ground nets are summarised in section 3; everything else is listed here so a wrong label is easy to spot. Format: `NET: ref.pin, ref.pin, ...`.

- `+9V_FUSED` (3): D1.2, D17.2, F1.2
- `+9V_IN` (2): F1.1, J1.1
- `ADC_BCLK` (3): R48.1, TP4.1, U8.21
- `ADC_BCLK_IC` (2): R48.2, U7.17
- `ADC_DOUT2` (3): R69.2, TP7.1, U8.6
- `ADC_DOUT2_IC` (2): R69.1, U7.22
- `ADC_LDO` (3): C43.1, C62.1, U7.11
- `ADC_LRCLK` (3): R47.1, TP5.1, U8.20
- `ADC_LRCLK_IC` (2): R47.2, U7.16
- `ADC_MCLK` (3): R46.1, TP3.1, U8.23
- `ADC_MCLK_IC` (2): R46.2, U7.15
- `ADC_TDM` (3): R49.2, TP6.1, U8.8
- `ADC_TDM_IC` (2): R49.1, U7.18
- `ADC_VREF` (3): C39.1, C40.1, U7.6
- `BAT_SENSE` (4): C89.1, R89.2, R90.1, U8.16
- `BIAS5` (2): D24.2, Q8.3
- `BIAS_SRC` (3): D24.1, Q6.3, R67.1
- `BLD_AC` (4): C19.2, R16.1, R22.1, U5.13
- `BLD_ACC` (4): C103.2, R116.1, R128.1, U16.10
- `BLD_ADC` (4): C31.1, R36.2, R40.1, U7.1
- `BLD_ADC_SRC` (2): C27.2, R36.1
- `BLD_ATT` (3): R22.2, R23.1, U5.12
- `BLD_CFB` (4): C107.1, R120.1, R124.1, U16.9
- `BLD_CPRE` (3): R28.2, R120.2, U16.8
- `BLD_FB` (4): C23.2, R28.1, R32.2, U6.9
- `BLD_MIC` (4): C15.1, C19.1, R8.2, R12.2
- `BLD_MICC` (4): C99.1, C103.1, R112.2, U5.4
- `BLD_PAD` (2): U5.14, U6.10
- `BLD_PRE` (4): C23.1, C27.1, R32.1, U6.8
- `BLD_RAW` (3): D8.1, J2.4, R12.1
- `BLD_RAWC` (3): D22.1, J2.5, R112.1
- `BOOST_COMP` (3): C81.1, R79.1, U11.8
- `BOOST_COMP_C` (2): C80.1, R79.2
- `BOOST_EN` (6): D15.1, D16.1, D17.1, Q4.3, R88.1, U11.4
- `BOOST_FB` (3): R80.2, R81.1, U11.9
- `BOOST_FREQ` (2): R82.1, U11.10
- `BOOST_SS` (2): C79.1, U11.5
- `BOOST_SW` (4): D12.2, L2.2, U11.1, U11.2
- `BRU_AC` (4): C20.2, R17.1, R24.1, U5.1
- `BRU_ACC` (4): C104.2, R117.1, R129.1, U16.12
- `BRU_ADC` (4): C32.1, R37.2, R41.1, U7.2
- `BRU_ADC_SRC` (2): C28.2, R37.1
- `BRU_ATT` (3): R24.2, R25.1, U5.2
- `BRU_CFB` (4): C108.1, R121.1, R125.1, U16.13
- `BRU_CPRE` (3): R29.2, R121.2, U16.14
- `BRU_FB` (4): C24.2, R29.1, R33.2, U6.13
- `BRU_MIC` (4): C16.1, C20.1, R9.2, R13.2
- `BRU_MICC` (4): C100.1, C104.1, R113.2, U15.4
- `BRU_PAD` (2): U5.15, U6.12
- `BRU_PRE` (4): C24.1, C28.1, R33.1, U6.14
- `BRU_RAW` (3): D9.1, J2.7, R13.1
- `BRU_RAWC` (3): D23.1, J2.8, R113.1
- `BUCK_FB` (4): C4.2, R1.2, R2.1, U1.5
- `BUCK_PG` (2): R3.2, U1.8
- `BUCK_SW` (2): L1.1, U1.7
- `CHG_ILIM` (2): R91.1, U13.12
- `CHG_ISET` (2): R92.1, U13.16
- `CHG_STAT_N` (3): R94.2, U8.17, U13.9
- `CHG_TS` (2): R93.1, U13.1
- `COLD_CTRL` (2): R107.1, U8.41
- `COLD_CTRL_G` (3): Q5.1, R107.2, R108.1
- `COLD_SEL` (6): Q5.3, R106.2, U4.9, U5.9, U15.9, U15.10
- `CTP_RST` (2): J3.11, U8.14
- `DAC_BCLK` (3): R57.1, TP9.1, U8.4
- `DAC_BCLK_IC` (2): R57.2, U9.13
- `DAC_CAPM` (2): C51.2, U9.4
- `DAC_CAPP` (2): C51.1, U9.2
- `DAC_DIN` (3): R58.1, TP11.1, U8.2
- `DAC_DIN_IC` (2): R58.2, U9.14
- `DAC_L` (2): R62.1, U9.6
- `DAC_LDO` (2): C53.1, U9.18
- `DAC_LRCLK` (3): R59.1, TP10.1, U8.3
- `DAC_LRCLK_IC` (2): R59.2, U9.15
- `DAC_MUTE` (2): R61.1, U8.34
- `DAC_MUTE_IC` (3): R60.1, R61.2, U9.17
- `DAC_R` (2): R63.1, U9.7
- `DAC_VNEG` (2): C52.1, U9.5
- `FLU_AC` (4): C17.2, R14.1, R18.1, U4.13
- `FLU_ACC` (4): C101.2, R114.1, R126.1, U16.3
- `FLU_ADC` (4): C29.1, R34.2, R38.1, U7.3
- `FLU_ADC_SRC` (2): C25.2, R34.1
- `FLU_ATT` (3): R18.2, R19.1, U4.12
- `FLU_CFB` (4): C105.1, R118.1, R122.1, U16.2
- `FLU_CPRE` (3): R26.2, R118.2, U16.1
- `FLU_FB` (4): C21.2, R26.1, R30.2, U6.2
- `FLU_MIC` (4): C13.1, C17.1, R6.2, R10.2
- `FLU_MICC` (4): C97.1, C101.1, R110.2, U4.4
- `FLU_PAD` (2): U4.14, U6.3
- `FLU_PRE` (4): C21.1, C25.1, R30.1, U6.1
- `FLU_RAW` (3): D6.1, J2.1, R10.1
- `FLU_RAWC` (3): D20.1, J2.2, R110.1
- `FRD_AC` (4): C18.2, R15.1, R20.1, U4.1
- `FRD_ACC` (4): C102.2, R115.1, R127.1, U16.5
- `FRD_ADC` (4): C30.1, R35.2, R39.1, U7.4
- `FRD_ADC_SRC` (2): C26.2, R35.1
- `FRD_ATT` (3): R20.2, R21.1, U4.2
- `FRD_CFB` (4): C106.1, R119.1, R123.1, U16.6
- `FRD_CPRE` (3): R27.2, R119.2, U16.7
- `FRD_FB` (4): C22.2, R27.1, R31.2, U6.6
- `FRD_MIC` (4): C14.1, C18.1, R7.2, R11.2
- `FRD_MICC` (4): C98.1, C102.1, R111.2, U15.15
- `FRD_PAD` (2): U4.15, U6.5
- `FRD_PRE` (4): C22.1, C26.1, R31.1, U6.7
- `FRD_RAW` (3): D7.1, J2.3, R11.1
- `FRD_RAWC` (3): D21.1, J2.6, R111.1
- `GAIN_A` (4): C48.1, R51.2, SW3.A, U8.29
- `GAIN_B` (4): C49.1, R52.2, SW3.B, U8.30
- `GAIN_PUSH` (4): C50.1, D19.2, R53.2, U8.31
- `GAIN_SW` (4): D19.1, Q4.1, R87.2, SW3.S1
- `HP_CPN` (2): C59.2, U10.17
- `HP_CPP` (2): C59.1, U10.18
- `HP_ENABLE` (3): R64.1, U8.33, U10.6
- `HP_INP_L` (2): C86.1, U10.2
- `HP_INP_R` (2): C87.1, U10.4
- `HP_IN_L` (2): C57.2, U10.1
- `HP_IN_R` (2): C58.2, U10.5
- `HP_JACK_L` (2): J5.T, R65.2
- `HP_JACK_R` (2): J5.R, R66.2
- `HP_OUT_L` (2): R65.1, U10.14
- `HP_OUT_R` (2): R66.1, U10.11
- `HP_VSS` (3): C60.1, U10.15, U10.16
- `I2C_SCL` (5): J3.10, R45.2, U7.24, U8.19, U10.8
- `I2C_SDA` (5): J3.12, R44.2, U7.23, U8.18, U10.7
- `KEEP_ON` (2): D15.2, U8.24
- `LDO_FB` (3): R130.2, R131.1, U12.4
- `LINE_JACK_L` (2): J4.T, K1.3
- `LINE_JACK_R` (2): J4.R, K1.6
- `LINE_L` (4): C57.1, C67.1, K1.2, R62.2
- `LINE_MUTE` (2): R84.1, U8.5
- `LINE_MUTE_G` (3): Q2.1, R84.2, R85.1
- `LINE_MUTE_K` (3): D13.2, K1.8, Q2.3
- `LINE_R` (4): C58.1, C68.1, K1.7, R63.2
- `MIC5_CTRL` (2): R102.1, U8.0
- `MIC5_CTRL_G` (3): Q9.1, R102.2, R103.1
- `MIC5_G` (3): Q8.1, Q9.3, R101.2
- `MIC9_CTRL` (2): R99.1, U8.1
- `MIC9_CTRL_G` (3): Q7.1, R99.2, R100.1
- `MIC9_G` (3): Q6.1, Q7.3, R98.2
- `NAV_DOWN` (4): C70.1, R71.2, SW4.A, U8.37
- `NAV_ENC_A` (4): C93.1, R96.2, SW4.8, U8.26
- `NAV_ENC_B` (4): C94.1, R97.2, SW4.7, U8.27
- `NAV_LEFT` (4): C71.1, R72.2, SW4.D, U8.38
- `NAV_PUSH` (4): C73.1, R74.2, SW4.5, U8.40
- `NAV_RIGHT` (4): C72.1, R73.2, SW4.B, U8.39
- `NAV_UP` (4): C69.1, R70.2, SW4.C, U8.36
- `PAD_CTRL` (2): R42.1, U8.32
- `PAD_CTRL_G` (3): Q1.1, R42.2, R43.1
- `PAD_SELECT` (7): C33.1, Q1.3, R83.2, U4.10, U4.11, U5.10, U5.11
- `PGOOD_N` (3): R95.2, U8.25, U13.7
- `PWR_LATCH_MID` (2): Q3.3, Q4.2
- `PWR_LED_A` (2): D4.2, R54.2
- `REC_BUTTON` (4): C47.1, D18.2, R50.2, U8.28
- `REC_LED` (2): R55.1, U8.35
- `REC_LED_A` (2): D5.2, R55.2
- `REC_SW` (4): D18.1, Q3.1, R86.2, SW2.1
- `SPI_MISO` (2): J3.9, U8.12
- `SPI_MOSI` (2): J3.6, U8.11
- `SPI_SCK` (2): J3.7, U8.13
- `TFT_CS` (2): J3.3, U8.10
- `TFT_DC` (2): J3.5, U8.9
- `TFT_LED` (2): J3.8, R56.2
- `TFT_RST` (2): J3.4, U8.7
- `TOUCH_IRQ` (2): J3.13, U8.22
- `USB_CC1` (2): J9.A5, R75.1
- `USB_CC2` (2): J9.B5, R76.1
- `USB_DM` (5): D11.3, D11.4, J9.A7, J9.B7, TP2.1
- `USB_DP` (5): D11.1, D11.6, J9.A6, J9.B6, TP1.1
- `VBUS_SENSE` (4): C78.1, R77.2, R78.1, U8.15
- `VREF_NR` (2): C9.1, U3.8
- `__unnamed_0` (1): J9.A8
- `__unnamed_1` (1): J9.B8
- `__unnamed_10` (1): U5.5
- `__unnamed_11` (1): U15.2
- `__unnamed_12` (1): U15.5
- `__unnamed_13` (1): U15.12
- `__unnamed_14` (1): U15.14
- `__unnamed_15` (1): U7.5
- `__unnamed_16` (1): U7.9
- `__unnamed_17` (1): U7.10
- `__unnamed_18` (1): U7.19
- `__unnamed_19` (1): U7.20
- `__unnamed_2` (1): U2.4
- `__unnamed_20` (1): U7.21
- `__unnamed_21` (1): U7.27
- `__unnamed_22` (1): U7.28
- `__unnamed_23` (1): U7.29
- `__unnamed_24` (1): U7.30
- `__unnamed_25` (1): U8.3V3B
- `__unnamed_26` (1): SW4.10
- `__unnamed_27` (1): J3.14
- `__unnamed_3` (1): U14.4
- `__unnamed_4` (1): U3.4
- `__unnamed_5` (1): U3.5
- `__unnamed_6` (1): U3.6
- `__unnamed_7` (1): U3.7
- `__unnamed_8` (1): U13.15
- `__unnamed_9` (1): U4.5

## 8. Teensy 4.1 pin map (U8)

| Teensy pin | Net | Direction | Function |
|---|---|---|---|
| 0 | MIC5_CTRL | out | high = 5 V electret bias (via R102 -> Q9 -> Q8) |
| 1 | MIC9_CTRL | out | high = 9 V electret bias (via R99 -> Q7 -> Q6). Never both high; both low = bias off |
| 2 | DAC_DIN | out (I2S) | PCM5102A data (R58 33R) |
| 3 | DAC_LRCLK | out (I2S) | PCM5102A LRCK (R59 33R) |
| 4 | DAC_BCLK | out (I2S) | PCM5102A BCK (R57 33R) |
| 5 | LINE_MUTE | out | high = relay K1 energised = line out muted (via R84 -> Q2) |
| 6 | ADC_DOUT2 | in (I2S) | PCM1864 second data line (GPIO0 as DOUT2, R69 33R) |
| 7 | TFT_RST | out | TFT reset (J3 pin 4) |
| 8 | ADC_TDM | in (I2S) | PCM1864 DOUT (R49 33R) |
| 9 | TFT_DC | out | TFT data/command (J3 pin 5) |
| 10 | TFT_CS | out | TFT chip select (J3 pin 3) |
| 11 | SPI_MOSI | out | TFT SDI (J3 pin 6) |
| 12 | SPI_MISO | in | TFT SDO (J3 pin 9) |
| 13 | SPI_SCK | out | TFT SCK (J3 pin 7) |
| 14 | CTP_RST | out | touch controller reset (J3 pin 11) |
| 15 | VBUS_SENSE | analog in | USB VBUS / 3.13 (100k/47k): 5 V -> 1.60 V |
| 16 | BAT_SENSE | analog in | VBAT / 2 (1M/1M): 4.2 V -> 2.10 V |
| 17 | CHG_STAT_N | in | charger /CHG (open drain, R94 100k pull-up), low = charging |
| 18 | I2C_SDA | I2C | PCM1864, TPA6130A2 (0x60), FT6336U touch; R44 4.7k pull-up |
| 19 | I2C_SCL | I2C | same bus; R45 4.7k pull-up |
| 20 | ADC_LRCLK | out (I2S) | PCM1864 LRCK (R47 33R) |
| 21 | ADC_BCLK | out (I2S) | PCM1864 BCK (R48 33R) |
| 22 | TOUCH_IRQ | in | FT6336U interrupt (J3 pin 13) |
| 23 | ADC_MCLK | out | PCM1864 SCK master clock (R46 33R) |
| 24 | KEEP_ON | out | high holds BOOST_EN through D15 (soft-power latch) |
| 25 | PGOOD_N | in | charger /PGOOD (R95 100k pull-up), low = USB power good |
| 26 | NAV_ENC_A | in | SW4 encoder phase A (R96 10k / C93 10n) |
| 27 | NAV_ENC_B | in | SW4 encoder phase B (R97 10k / C94 10n) |
| 28 | REC_BUTTON | in | SW2 record button through D18 (R50 10k / C47 100n), active low |
| 29 | GAIN_A | in | SW3 encoder phase A (R51 10k / C48 10n) |
| 30 | GAIN_B | in | SW3 encoder phase B (R52 10k / C49 10n) |
| 31 | GAIN_PUSH | in | SW3 push through D19 (R53 10k / C50 100n), active low |
| 32 | PAD_CTRL | out | high = -9.7 dB pad engaged (via R42 -> Q1). Firmware must keep it LOW in dynamic-mic mode |
| 33 | HP_ENABLE | out | TPA6130A2 /SD: high = headphone amp on (R64 100k pull-down) |
| 34 | DAC_MUTE | out | PCM5102A XSMT: high = un-mute (R61 100R, R60 10k pull-DOWN) |
| 35 | REC_LED | out | red LED D5 through R55 1k |
| 36 | NAV_UP | in | SW4 (R70 10k / C69 100n), active low |
| 37 | NAV_DOWN | in | SW4 (R71 / C70) |
| 38 | NAV_LEFT | in | SW4 (R72 / C71) |
| 39 | NAV_RIGHT | in | SW4 (R73 / C72) |
| 40 | NAV_PUSH | in | SW4 centre push (R74 / C73) |
| 41 | COLD_CTRL | out | high = cold legs released = dynamic/balanced mode (via R107 -> Q5). Low/boot = electret mode (cold legs grounded) |
| VIN | TEENSY_VIN | power | +5V through D3 (cut the VIN-VUSB link on the module) |
| 3.3V (3V3A, left row) | +3V3_D | power out | Teensy regulator output: all pull-ups |
| 3.3V (3V3B, right row, next to VIN/GND) | no connect | power out | same regulator output inside the module; left NC since 2026-09-15 (see section 16) |
| GND (x3) | GND | power |  |
| USB D+/D- pads | TP1 / TP2 | wires | underside USB-device pads wired to TP1 (D+) and TP2 (D-) |

Teensy pins with a net that are not in the table above: 3V3A=+3V3_D, GND1=GND, GND2=GND, GND3=GND.

## 9. The analog channel, stage by stage (values as drawn, one channel; the other three are identical)

Reference allocation is regular: channel n = FLU(1), FRD(2), BLD(3), BRU(4). Hot leg parts: R(5+n) bias, R(9+n) 100R, C(12+n) 100p, C(16+n) 4u7, R(13+n) 1M, R(18+2(n-1)) 68k / R(19+2(n-1)) 33k pad, R(26+n-1) 10k, R(30+n-1) 90.9k, C(20+n) 22p, C(24+n) 4u7, R(34+n-1) 100R, C(28+n) 10n, R(38+n-1) 100k DNP. Cold leg: R(109+n) 100R, C(96+n) 100p, C(100+n) 4u7, R(113+n) 1M, R(125+n) 100k, R(117+n) 10k, R(121+n) 90.9k, C(104+n) 22p.

| Stage | Parts (FLU) | Function | Number to check |
|---|---|---|---|
| Bias feed | R6 4.7k from +9V_MIC to FLU_MIC | electret phantom (2-wire) | 9 V / 4.7k = 1.9 mA max into a shorted capsule; typical capsule 0.5 mA at ~6.5 V |
| RF stop | R10 100R + C13 100p to CHASSIS (hot), R110 100R + C97 100p (cold), D6/D20 PESD | keeps RF off the pair, symmetrical both legs | corner 1/(2 pi 100 x 100p) = 16 MHz |
| Coupling | C17 4.7 uF PMLCAP (hot), C101 4.7 uF (cold) | blocks the bias / mic DC | into 1M: 0.034 Hz; into the 92k hot load: 0.37 Hz (both far below audio) |
| Input bias | R14 1M hot -> VREF; R114 1M + R126 100k cold -> VREF | both inputs sit at VREF = 4.5 V | hot sees 1M parallel 101k = 92k, cold 1M parallel 100k = 91k (balanced within 1 %) |
| Pad | R18 68k / R19 33k 0.1 % to VREF, switched by U4 (A section) | direct or -9.7 dB | 33/(68+33) = 0.327 = -9.7 dB; select high (default) = direct |
| Cold-leg ground | U4 C section (pins 4/3), COLD_SEL pin 9 | electret mode grounds FLU_MICC | CD4053 on-resistance ~120 R at 9 V |
| A1 (cold amp) | U16 unit A: + = FLU_ACC, out = FLU_CPRE, R118 10k CFB-CPRE, R122 90.9k CFB-VREF, C105 22p across R122 | non-inverting gain 1 + 10k/90.9k = 1.11 | C105 gives the zero that tracks A2's pole |
| A2 (hot amp) | U6 unit A: + = FLU_PAD, out = FLU_PRE, R26 10k FB-CPRE, R30 90.9k PRE-FB, C21 22p across R30 | Vout = (1 + 90.9/10)(hot - cold) = 10.09 x = +20.08 dB | -3 dB at 1/(2 pi 90.9k x 22p) = 80 kHz; SPICE: 20.06 dB, 71 kHz |
| Output coupling | C25 4.7 uF PMLCAP -> R34 100R -> C29 10 nF C0G -> PCM1864 VINL1 | re-biases to the ADC's own AVDD/2 | RC corner 1/(2 pi 100 x 10n) = 159 kHz (anti-alias); R38 100k DNP |

Full-scale check: PCM1864 input is 2.1 Vrms (single-ended, 0 dB PGA), which with the 10.09x (+20.08 dB) gain is 0.21 Vrms at the capsule. The op-amp itself, on a 9 V single supply centred at 4.5 V, swings about 4.4 V peak = 3.1 Vrms (OPA1654 rail-to-rail output, ~100 mV from each rail), which is 0.31 Vrms referred to the input; so the ADC reaches full scale (0.21 Vrms in) before the op-amp clips (0.31 Vrms in), and hot electret levels need the -9.7 dB pad.

### Mic-mode logic (all four channels together)

| Screen setting | Teensy 1 MIC9_CTRL | Teensy 0 MIC5_CTRL | Teensy 41 COLD_CTRL | Q6 | Q8 | +9V_MIC | COLD_SEL (U4/U5/U15 pin 9) | Cold legs | Pad allowed |
|---|---|---|---|---|---|---|---|---|---|
| Boot / unknown | low | low | low | off | off | 0 V (bleeds through R104) | high (R106 to +9V) | grounded | yes |
| Electret 9 V | high | low | low | on | off | 9.0 V | high | grounded | yes |
| Electret 5 V | low | high | low | off | on | ~4.7 V (D24 drop) | high | grounded | yes |
| Dynamic / balanced | low | low | high | off | off | 0 V | low (Q5 pulls it down) | released into A1 | NO (firmware lockout) |

Sequencing rule for firmware: when leaving a bias mode, drop MIC9/MIC5 first, wait for +9V_MIC to bleed (R104 100k x C66 100 uF = 10 s time constant; read it back is not possible, so wait or accept a thump), then raise COLD_CTRL. Never raise a bias with COLD_CTRL high.

## 10. Arithmetic on every set point (check these against the datasheets)

| What | Parts | Formula | Result | Datasheet / expectation |
|---|---|---|---|---|
| Boost output +10V5 | R80 75k, R81 10k | 1.229 x (1 + 75/10) | 10.45 V | TPS61175 Vfb 1.229 V; input 4.4-9 V OK (must be below output) |
| Boost frequency | R82 80.6k | TPS61175 curve | ~1.2 MHz | datasheet table: 80.6k ~ 1.2 MHz |
| Boost soft start | C79 47 nF | ~ | ~ms | standard value |
| Boost compensation | R79 10k, C80 4.7n, C81 47p | type II | zero 3.4 kHz, pole 340 kHz | verify load step on the bench |
| LDO output +9V | R130 130k, R131 20k | 1.2 x (1 + 130/20) | 9.00 V | ADP7142 Vref 1.2 V; dropout at 40 mA << 1.45 V headroom |
| LDO dissipation | 10.45 - 9.0 = 1.45 V x 25-40 mA | | 36-58 mW | TSOT 170 C/W -> +6-10 C |
| Buck output +5V | R1 680k, R2 130k, C4 22p | 0.8 x (1 + 680/130) | 4.98 V | TPS62160 Vfb 0.8 V; C4 feed-forward per datasheet |
| Buck PG pull-up | R3 100k to +5V | | | BUCK_PG unused elsewhere |
| 3.3 V LDOs | U2, U14 fixed | | 3.30 V | TPS7A2033: EN tied to IN, 1 uF in / 4.7 uF out (C7/C8, C95/C96) |
| VREF | U3 TLE2426 | +9V / 2 | 4.50 V | C9 1 uF on NR pin, C10 47 uF + C11 100 nF on OUT |
| Mic bias filter | R67 100R, C66 100 uF | 1/(2 pi RC) | 16 Hz | 1.9 mA x 4 max through 100R = 0.76 V drop worst case, typical 0.2 V |
| Mic bias bleed | R104 100k, C66 100 uF | tau | 10 s | bias falls to 1 V in ~22 s after switching off |
| Electret bias current | R6-R9 4.7k | (9 - Vcap)/4.7k | ~0.5-0.9 mA | capsule FET typical 0.5 mA |
| VBUS sense | R77 100k, R78 47k | 5 x 47/147 | 1.60 V | Teensy ADC 3.3 V max |
| Battery sense | R89 1M, R90 1M, C89 100n | 4.2 / 2 | 2.10 V | 2 uA drain; RC 0.05 s |
| Charger current | R92 1.2k ISET | 890 / 1.2k | 0.74 A | BQ24074 K_ISET = 890 |
| Charger input limit | R91 1.1k ILIM | 1610 / 1.1k | 1.46 A | EN2 (pin 5) = VBUS_FUSED = high, EN1 (pin 6) = GND -> 'set by ILIM resistor' row of the BQ24074 truth table (verified against the datasheet 2026-09-15) |
| Charger TS | R93 10k to GND | | always in range | pack PCM provides protection |
| Charger timer / termination | TMR pin 14 = GND, ITERM pin 15 open | | timers off, ITERM = 10 % of ISET (74 mA) | matches the design note; CE (pin 4) = GND = charging enabled |
| Power LED | R54 2.2k from +5V, D4 blue Vf 3.0 | (5 - 3)/2.2k | 0.9 mA | dim but visible; raise R54 current if needed |
| Record LED | R55 1k from Teensy pin 35, D5 red Vf 2.0 | (3.3 - 2)/1k | 1.3 mA | Teensy 4 mA/pin guideline |
| TFT backlight | R56 100R from +5V | | ~20 mA class | module has its own LED driver? verify; 95 mA spec at full brightness |
| Relay coil | K1 5 V, 21 mA; Q2 2N7002; D13 flyback | | | Q2 Rds 2 R at 3.3 V gate: fine |
| I2C pull-ups | R44/R45 4.7k to +3V3_D | | 0.7 mA per line | three slaves: PCM1864, TPA6130A2 (0x60), FT6336U (0x38) |
| ADC clock terminations | R46-R49, R69, R57-R59 33R | | | series at the driver |
| DAC output filter | R62/R63 470R, C67/C68 2.2n C0G | 1/(2 pi 470 x 2.2n) | 154 kHz | TI recommended |
| Headphone input | C57/C58 2.2 uF PMLCAP into TPA6130A2 20k | 1/(2 pi 20k x 2.2u) | 3.6 Hz | C86/C87 match on INP |
| Headphone output | R65/R66 10R | | | isolation into the 3.5 mm jack |
| Soft power pull-ups | R86/R87 1M to VBAT, R88 1M to GND | | ~4 uA off-state | D15-D19 1N4148W (25 nA leakage) |
| Line-out relay sense | K1 NC = pass | | | verify at bring-up |

## 11. Digital audio and control buses

| Bus | Master | Slave(s) | Nets | Rate / notes |
|---|---|---|---|---|
| ADC I2S/TDM | Teensy SAI1 (MCLK 23, BCLK 21, LRCLK 20) | PCM1864 SCK/BCK/LRCK; data back on DOUT (pin 18 -> Teensy 8) and DOUT2 (GPIO0 pin 22 -> Teensy 6) | ADC_MCLK/BCLK/LRCLK/TDM/DOUT2, 33R each | 192 kHz, 2x I2S (four channels on two data lines); PCM1864 is the I2S slave |
| DAC I2S | Teensy (BCLK 4, LRCLK 3, DIN 2) | PCM5102A | DAC_BCLK/LRCLK/DIN, 33R each | 48 kHz binaural; PCM5102A generates its own internal clock (no MCLK) |
| I2C | Teensy 18/19 | PCM1864 (addr by MD0/MD1 = pins 25/26 = GND: 0x4A), TPA6130A2 (0x60), FT6336U touch (0x38) | I2C_SDA/SCL, 4.7k to +3V3_D | 400 kHz OK |
| SPI | Teensy 11/12/13 | ST7796U TFT (CS 10, DC 9, RST 7) | SPI_MOSI/MISO/SCK, TFT_* | display only |

PCM1864 mode/address pins as drawn: MD0/ADR1 (25) = GND, MD1/ADR0 (26) = GND -> software (I2C) control mode, address 0x4A (0x94 write). GPIO0 (22) is used as DOUT2; GPIO1-3 (19-21) are no connect. Section 4 lists each pin.

PCM5102A hard-wired mode pins: FLT (11) = GND (normal latency filter), DEMP (12) = GND (de-emphasis off), FMT (16) = GND (I2S), XSMT (17) driven by Teensy 34 with a 10k pull-DOWN (muted until firmware un-mutes).

## 12. Decoupling, pad to pad (mm)

Distance from each supply pin's pad to the nearest same-net capacitor pad, measured on the board.

| IC pin | Rail | Nearest caps (distance mm) |
|---|---|---|
| U7.8 | +3V3_A | C41 (1.4), C42 (5.4) |
| U7.13 | +3V3_DC | C44 (1.5), C45 (5.0) |
| U7.14 | +3V3_DC | C44 (1.4), C45 (5.0) |
| U7.6 | ADC_VREF | C40 (1.6), C39 (3.0) |
| U7.11 | ADC_LDO | C43 (1.4), C62 (5.1) |
| U9.1 | +3V3_A | C54 (1.3), C64 (4.7) |
| U9.8 | +3V3_A | C64 (1.3), C55 (3.6) |
| U9.20 | +3V3_DC | C56 (1.3), C45 (18.0) |
| U9.18 | DAC_LDO | C53 (1.3) |
| U9.5 | DAC_VNEG | C52 (2.8) |
| U10.12 | +5V | C65 (1.5), C61 (5.4) |
| U10.20 | +5V | C61 (1.7), C65 (5.0) |
| U10.15 | HP_VSS | C60 (1.6) |
| U10.16 | HP_VSS | C60 (2.5) |
| U6.4 | +9V | C37 (8.0), C36 (8.5) |
| U16.4 | +9V | C109 (8.7), C35 (10.0) |
| U3.3 | +9V | C34 (14.0), C36 (15.6) |
| U4.16 | +9V | C36 (3.4), C34 (4.0) |
| U5.16 | +9V | C35 (7.7), C110 (12.2) |
| U15.16 | +9V | C35 (4.1), C110 (10.6) |
| U12.1 | +10V5 | C83 (3.4), C76 (12.6) |
| U12.3 | +10V5 | C83 (2.9), C76 (14.4) |
| U12.5 | +9V | C88 (4.9), C75 (6.8) |
| U1.2 | +10V5 | C2 (6.4), C3 (10.8) |
| U1.3 | +10V5 | C2 (5.9), C3 (10.5) |
| U1.6 | +5V | C4 (6.7), C5 (8.4) |
| U11.3 | VBOOST_IN | C1 (7.9), C85 (14.6) |
| U2.1 | +5V | C7 (4.9), C95 (8.0) |
| U2.3 | +5V | C7 (4.7), C95 (9.6) |
| U2.5 | +3V3_A | C8 (3.4), C55 (9.4) |
| U14.1 | +5V | C95 (5.3), C7 (7.2) |
| U14.3 | +5V | C7 (5.9), C95 (6.5) |
| U14.5 | +3V3_DC | C96 (3.3), C45 (8.9) |
| U13.5 | VBUS_FUSED | C90 (5.2) |
| U13.13 | VBUS_FUSED | C90 (6.3) |
| U13.10 | BAT_SYS | C91 (4.1) |
| U13.11 | BAT_SYS | C91 (4.0) |
| U13.2 | VBAT | C92 (12.2) |
| U13.3 | VBAT | C92 (11.8) |

Reading: the converters (U7, U9, U10) have their 100 nF within 1.3-1.7 mm (placed under the pins). The buck U1 has its 100 nF 6 mm and 10 uF 10 mm from VIN (acceptable, on the Rev D list). The op-amps see their 100 nF at 8-9 mm on a planed 9 V LDO rail (fine for audio bandwidth). U13 charger: C90 5-6 mm from IN, C91/C92 on OUT/BAT.

## 13. Board: stackup, placement, mechanical

Stackup (in the board file): F.Cu 35 um / 0.21 mm prepreg / In1.Cu 35 um GND / 1.065 mm core / In2.Cu 35 um GND / 0.21 mm prepreg / B.Cu 35 um. All routing is on F.Cu and B.Cu; In1/In2 are solid GND (93 % fill each, one region) with rule areas that forbid tracks and vias on them. Copper-to-edge keepout 0.65 mm. Design rules: 0.20 mm track / 0.15 mm clearance, 0.30 mm supply tracks, vias 0.6/0.3 (185) and 0.8/0.4 (338).

Mounting / wall items (from the board): 4 x 3.2 mm corner holes, 2 x 3.25 mm (display standoffs?), 1 x 3.0 mm, 2 x 0.65 NPTH (J4 pegs), 3 fiducials per side.

### Placement table (every placed part: side, centre in mm from the board's top-left, rotation)

| Ref | Value | Side | X | Y | Rot | Footprint |
|---|---|---|---:|---:|---:|---|
| C1 | 100uF 25V | Top | 17.0000 | 24.5000 | 0.00 | CP_Elec_6.3x5.8 |
| C2 | 100nF 25V | Top | 108.0000 | 92.5000 | 0.00 | C_0805_2012Metric |
| C3 | 10uF 25V | Top | 114.0000 | 92.5000 | 0.00 | C_1206_3216Metric |
| C4 | 22pF C0G | Top | 113.0000 | 84.0000 | 0.00 | C_0603_1608Metric |
| C5 | 22uF 10V | Top | 117.0000 | 88.0000 | 0.00 | C_1206_3216Metric |
| C6 | 22uF 10V | Top | 123.0000 | 88.0000 | 0.00 | C_1206_3216Metric |
| C7 | 1uF 10V | Bottom | 92.5000 | 55.0000 | 0.00 | C_0805_2012Metric |
| C8 | 4.7uF 10V | Bottom | 92.5000 | 59.0000 | 0.00 | C_0805_2012Metric |
| C9 | 1uF 10V | Top | 42.0000 | 31.0000 | 0.00 | C_0805_2012Metric |
| C10 | 47uF 10V | Top | 47.0000 | 31.0000 | 0.00 | C_1206_3216Metric |
| C11 | 100nF | Top | 51.5000 | 31.0000 | 0.00 | C_0603_1608Metric |
| C12 | 1nF 1kV C0G | Top | 10.5000 | 64.0000 | 0.00 | C_0805_2012Metric |
| C13 | 100pF C0G | Top | 38.0000 | 85.5000 | 90.00 | C_0603_1608Metric |
| C14 | 100pF C0G | Top | 38.0000 | 91.8000 | 90.00 | C_0603_1608Metric |
| C15 | 100pF C0G | Top | 38.0000 | 98.1000 | 90.00 | C_0603_1608Metric |
| C16 | 100pF C0G | Top | 38.0000 | 104.4000 | 90.00 | C_0603_1608Metric |
| C17 | 4.7uF 35V FILM | Top | 42.0000 | 85.5000 | 90.00 | C_1812_4532Metric |
| C18 | 4.7uF 35V FILM | Top | 42.0000 | 91.8000 | 90.00 | C_1812_4532Metric |
| C19 | 4.7uF 35V FILM | Top | 42.0000 | 98.1000 | 90.00 | C_1812_4532Metric |
| C20 | 4.7uF 35V FILM | Top | 42.0000 | 104.4000 | 90.00 | C_1812_4532Metric |
| C21 | 22pF C0G | Bottom | 70.0000 | 85.5000 | 90.00 | C_0603_1608Metric |
| C22 | 22pF C0G | Bottom | 70.0000 | 91.8000 | 90.00 | C_0603_1608Metric |
| C23 | 22pF C0G | Bottom | 70.0000 | 98.1000 | 90.00 | C_0603_1608Metric |
| C24 | 22pF C0G | Bottom | 70.0000 | 104.4000 | 90.00 | C_0603_1608Metric |
| C25 | 4.7uF 35V FILM | Top | 74.0000 | 85.5000 | 90.00 | C_1812_4532Metric |
| C26 | 4.7uF 35V FILM | Top | 74.0000 | 91.8000 | 90.00 | C_1812_4532Metric |
| C27 | 4.7uF 35V FILM | Top | 74.0000 | 98.1000 | 90.00 | C_1812_4532Metric |
| C28 | 4.7uF 35V FILM | Top | 74.0000 | 104.4000 | 90.00 | C_1812_4532Metric |
| C29 | 10nF C0G | Top | 82.0000 | 85.5000 | 90.00 | C_0603_1608Metric |
| C30 | 10nF C0G | Top | 82.0000 | 91.8000 | 90.00 | C_0603_1608Metric |
| C31 | 10nF C0G | Top | 82.0000 | 98.1000 | 90.00 | C_0603_1608Metric |
| C32 | 10nF C0G | Top | 82.0000 | 104.4000 | 90.00 | C_0603_1608Metric |
| C33 | 100nF | Top | 10.5000 | 61.0000 | 0.00 | C_0603_1608Metric |
| C34 | 100nF | Bottom | 40.0000 | 40.0000 | 0.00 | C_0603_1608Metric |
| C35 | 100nF | Bottom | 40.0000 | 60.5000 | 0.00 | C_0603_1608Metric |
| C36 | 100nF | Bottom | 47.0000 | 42.0000 | 0.00 | C_0603_1608Metric |
| C37 | 10uF 16V | Bottom | 51.0000 | 42.0000 | 0.00 | C_1206_3216Metric |
| C39 | 1uF | Bottom | 83.0000 | 45.9000 | 0.00 | C_0805_2012Metric |
| C40 | 100nF | Bottom | 82.8000 | 47.7000 | 0.00 | C_0603_1608Metric |
| C41 | 100nF | Bottom | 82.8000 | 49.3000 | 0.00 | C_0603_1608Metric |
| C42 | 10uF | Bottom | 87.1000 | 47.4000 | 0.00 | C_1206_3216Metric |
| C43 | 100nF | Bottom | 82.8000 | 50.9000 | 0.00 | C_0603_1608Metric |
| C44 | 100nF | Bottom | 82.8000 | 52.5000 | 0.00 | C_0603_1608Metric |
| C45 | 10uF | Bottom | 87.1000 | 52.3000 | 0.00 | C_1206_3216Metric |
| C46 | 10uF | Bottom | 48.0000 | 56.0000 | 0.00 | C_1206_3216Metric |
| C47 | 100nF | Bottom | 106.0000 | 16.0000 | 0.00 | C_0603_1608Metric |
| C48 | 10nF | Bottom | 102.0000 | 24.0000 | 0.00 | C_0603_1608Metric |
| C49 | 10nF | Bottom | 106.0000 | 24.0000 | 0.00 | C_0603_1608Metric |
| C50 | 100nF | Bottom | 110.0000 | 24.0000 | 0.00 | C_0603_1608Metric |
| C51 | 2.2uF | Top | 94.7000 | 48.4000 | -90.00 | C_0805_2012Metric |
| C52 | 2.2uF | Top | 94.7000 | 51.9000 | -90.00 | C_0805_2012Metric |
| C53 | 1uF | Bottom | 102.3300 | 48.6500 | 0.00 | C_0603_1608Metric |
| C54 | 100nF | Bottom | 97.7000 | 47.0800 | 180.00 | C_0603_1608Metric |
| C55 | 10uF | Bottom | 99.9000 | 55.0000 | 0.00 | C_1206_3216Metric |
| C56 | 100nF | Bottom | 102.3000 | 47.0800 | 0.00 | C_0603_1608Metric |
| C57 | 2.2uF 25V FILM | Top | 106.4000 | 54.6000 | 0.00 | C_1210_3225Metric |
| C58 | 2.2uF 25V FILM | Top | 106.4000 | 60.2000 | 0.00 | C_1210_3225Metric |
| C59 | 1uF | Top | 112.7500 | 52.2000 | 0.00 | C_0603_1608Metric |
| C60 | 1uF | Top | 116.2500 | 54.6000 | 0.00 | C_0603_1608Metric |
| C61 | 1uF | Top | 110.3000 | 51.7500 | 90.00 | C_0603_1608Metric |
| C62 | 10uF | Bottom | 87.1000 | 49.8500 | 0.00 | C_1206_3216Metric |
| C64 | 100nF | Bottom | 97.7000 | 51.6200 | 180.00 | C_0603_1608Metric |
| C65 | 1uF | Top | 116.2500 | 56.2000 | 0.00 | C_0603_1608Metric |
| C66 | 100uF 16V | Bottom | 34.0000 | 74.0000 | 0.00 | CP_Elec_6.3x5.8 |
| C67 | 2.2nF C0G | Top | 93.0000 | 55.0000 | 0.00 | C_0603_1608Metric |
| C68 | 2.2nF C0G | Top | 96.5000 | 55.0000 | 0.00 | C_0603_1608Metric |
| C69 | 100nF | Bottom | 102.0000 | 32.0000 | 0.00 | C_0603_1608Metric |
| C70 | 100nF | Bottom | 106.0000 | 32.0000 | 0.00 | C_0603_1608Metric |
| C71 | 100nF | Bottom | 110.0000 | 32.0000 | 0.00 | C_0603_1608Metric |
| C72 | 100nF | Bottom | 114.0000 | 32.0000 | 0.00 | C_0603_1608Metric |
| C73 | 100nF | Bottom | 118.0000 | 32.0000 | 0.00 | C_0603_1608Metric |
| C74 | 10uF 16V | Top | 18.5000 | 45.0000 | 0.00 | C_1206_3216Metric |
| C75 | 100nF | Top | 17.0000 | 53.5000 | 0.00 | C_0603_1608Metric |
| C76 | 10uF 25V | Top | 13.5000 | 37.5000 | 0.00 | C_1206_3216Metric |
| C77 | 10uF 25V | Top | 18.5000 | 37.5000 | 0.00 | C_1206_3216Metric |
| C78 | 100nF | Top | 48.0000 | 14.0000 | 0.00 | C_0603_1608Metric |
| C79 | 47nF | Bottom | 15.0000 | 29.0000 | 90.00 | C_0603_1608Metric |
| C80 | 4.7nF C0G | Top | 5.0000 | 45.0000 | 0.00 | C_0603_1608Metric |
| C81 | 47pF C0G | Top | 9.0000 | 45.0000 | 0.00 | C_0603_1608Metric |
| C83 | 2.2uF | Top | 5.5000 | 50.5000 | 90.00 | C_0805_2012Metric |
| C85 | 10uF 25V | Top | 20.5000 | 18.5000 | 90.00 | C_1206_3216Metric |
| C86 | 2.2uF 25V FILM | Top | 100.4000 | 55.7000 | 180.00 | C_1210_3225Metric |
| C87 | 2.2uF 25V FILM | Top | 100.4000 | 59.1000 | 180.00 | C_1210_3225Metric |
| C88 | 10uF 16V | Top | 17.0000 | 50.0000 | 0.00 | C_1206_3216Metric |
| C89 | 100nF | Top | 132.0000 | 31.5000 | 0.00 | C_0603_1608Metric |
| C90 | 10uF 10V | Top | 124.0000 | 15.0000 | 90.00 | C_0805_2012Metric |
| C91 | 10uF 10V | Top | 135.0000 | 15.0000 | 90.00 | C_0805_2012Metric |
| C92 | 10uF 10V | Top | 136.0000 | 24.5000 | 90.00 | C_0805_2012Metric |
| C93 | 10nF | Bottom | 110.0000 | 36.0000 | 0.00 | C_0603_1608Metric |
| C94 | 10nF | Bottom | 114.0000 | 36.0000 | 0.00 | C_0603_1608Metric |
| C95 | 1uF 10V | Bottom | 92.5000 | 63.0000 | 0.00 | C_0805_2012Metric |
| C96 | 4.7uF 10V | Bottom | 88.0000 | 63.0000 | 0.00 | C_0805_2012Metric |
| C97 | 100pF C0G | Bottom | 36.0000 | 85.5000 | 90.00 | C_0603_1608Metric |
| C98 | 100pF C0G | Bottom | 36.0000 | 91.8000 | 90.00 | C_0603_1608Metric |
| C99 | 100pF C0G | Bottom | 36.0000 | 98.1000 | 90.00 | C_0603_1608Metric |
| C100 | 100pF C0G | Bottom | 36.0000 | 104.4000 | 90.00 | C_0603_1608Metric |
| C101 | 4.7uF 35V FILM | Bottom | 44.0000 | 85.5000 | 90.00 | C_1812_4532Metric |
| C102 | 4.7uF 35V FILM | Bottom | 44.0000 | 91.8000 | 90.00 | C_1812_4532Metric |
| C103 | 4.7uF 35V FILM | Bottom | 44.0000 | 98.1000 | 90.00 | C_1812_4532Metric |
| C104 | 4.7uF 35V FILM | Bottom | 44.0000 | 104.4000 | 90.00 | C_1812_4532Metric |
| C105 | 22pF C0G | Bottom | 63.0000 | 85.5000 | 90.00 | C_0603_1608Metric |
| C106 | 22pF C0G | Bottom | 63.0000 | 91.8000 | 90.00 | C_0603_1608Metric |
| C107 | 22pF C0G | Bottom | 63.0000 | 98.1000 | 90.00 | C_0603_1608Metric |
| C108 | 22pF C0G | Bottom | 63.0000 | 104.4000 | 90.00 | C_0603_1608Metric |
| C109 | 100nF | Top | 57.5000 | 58.5000 | 90.00 | C_0603_1608Metric |
| C110 | 100nF | Top | 33.5000 | 60.5000 | 0.00 | C_0603_1608Metric |
| D1 | B340A 40V 3A | Top | 14.5000 | 18.5000 | 0.00 | D_SMA |
| D2 | SMBJ12A | Top | 8.0000 | 23.5000 | 0.00 | D_SMB |
| D3 | SS14 | Bottom | 48.0000 | 60.0000 | 0.00 | D_SMA |
| D4 | POWER BLUE | Top | 64.7300 | 112.1000 | 0.00 | LED_D3.0mm_Horizontal_O1.27mm_Z6.0mm |
| D5 | RECORD RED | Top | 74.7300 | 112.1000 | 0.00 | LED_D3.0mm_Horizontal_O1.27mm_Z6.0mm |
| D6 | PESD12VL1BA | Top | 24.0000 | 68.0000 | 90.00 | D_SOD-323 |
| D7 | PESD12VL1BA | Top | 24.0000 | 72.0000 | 90.00 | D_SOD-323 |
| D8 | PESD12VL1BA | Top | 24.0000 | 76.0000 | 90.00 | D_SOD-323 |
| D9 | PESD12VL1BA | Top | 24.0000 | 80.0000 | 90.00 | D_SOD-323 |
| D10 | B340A 40V 3A | Top | 52.0000 | 10.5000 | 0.00 | D_SMA |
| D11 | USBLC6-2SC6 | Top | 40.0000 | 12.8000 | 0.00 | SOT-23-6 |
| D12 | B340A 40V 3A | Top | 7.0000 | 37.5000 | 0.00 | D_SMA |
| D13 | 1N4148W | Top | 104.0000 | 100.5000 | 0.00 | D_SOD-123 |
| D14 | B340A 40V 3A | Top | 131.0000 | 24.5000 | 0.00 | D_SMA |
| D15 | 1N4148W | Top | 123.5000 | 28.2000 | 0.00 | D_SOD-123 |
| D16 | 1N4148W | Top | 128.3000 | 28.2000 | 0.00 | D_SOD-123 |
| D17 | 1N4148W | Top | 133.1000 | 28.2000 | 0.00 | D_SOD-123 |
| D18 | 1N4148W | Bottom | 98.0000 | 16.0000 | 0.00 | D_SOD-123 |
| D19 | 1N4148W | Bottom | 98.0000 | 20.0000 | 0.00 | D_SOD-123 |
| D20 | PESD12VL1BA | Bottom | 40.0000 | 85.5000 | 90.00 | D_SOD-323 |
| D21 | PESD12VL1BA | Bottom | 40.0000 | 91.8000 | 90.00 | D_SOD-323 |
| D22 | PESD12VL1BA | Bottom | 40.0000 | 98.1000 | 90.00 | D_SOD-323 |
| D23 | PESD12VL1BA | Bottom | 40.0000 | 104.4000 | 90.00 | D_SOD-323 |
| D24 | BAT54 | Top | 34.0000 | 82.5000 | 0.00 | D_SOD-123 |
| F1 | 750mA PTC | Top | 7.0000 | 18.5000 | 0.00 | Fuse_1206_3216Metric |
| F2 | 2A PTC | Top | 52.0000 | 6.0000 | 0.00 | Fuse_1206_3216Metric |
| J1 | 9V DC IN | Top | 17.5000 | 8.2000 | 180.00 | BarrelJack_CUI_PJ-102AH_Horizontal |
| J2 | AMBISONIC MIC RJ45 | Top | 4.0000 | 74.0000 | -90.00 | RJ45_Amphenol_RJHSE5380 |
| J3 | MSP3526 TFT 3.5IN 14PIN SOCKET | Top | 25.0000 | 19.2400 | 0.00 | PinSocket_1x14_P2.54mm_Vertical |
| J4 | 1/4in BINAURAL LINE OUT | Top | 26.0000 | 98.0000 | -90.00 | Jack_6.35mm_Neutrik_NRJ6HF_Horizontal |
| J5 | 1/8in BINAURAL HEADPHONE OUT | Top | 135.9000 | 41.0000 | -90.00 | Jack_3.5mm_CUI_SJ1-3533NG_Horizontal |
| J9 | USB-C POWER + DATA | Top | 40.0000 | 2.6000 | 180.00 | USB_C_Receptacle_HRO_TYPE-C-31-M-12 |
| J10 | BATTERY 1S LiPo | Bottom | 121.0000 | 109.5000 | 0.00 | JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical |
| K1 | G6K-2F-Y 5VDC | Top | 113.0000 | 103.5000 | 0.00 | Relay_DPDT_Omron_G6K-2F-Y |
| L1 | 2.2uH 1.5A | Top | 111.5000 | 88.0000 | 0.00 | L_Abracon_ASPIAIG-F4020 |
| L2 | 10uH 2A | Top | 18.0000 | 31.5000 | 0.00 | L_Bourns_SRN6045TA |
| Q1 | 2N7002 | Top | 6.0000 | 58.0000 | 0.00 | SOT-23 |
| Q2 | 2N7002 | Top | 104.0000 | 104.0000 | 0.00 | SOT-23 |
| Q3 | AO3401A | Top | 30.0000 | 67.0000 | 0.00 | SOT-23 |
| Q4 | AO3401A | Top | 30.0000 | 71.0000 | 0.00 | SOT-23 |
| Q5 | 2N7002 | Top | 34.0000 | 64.5000 | 0.00 | SOT-23 |
| Q6 | AO3401A | Top | 34.0000 | 75.5000 | 0.00 | SOT-23 |
| Q7 | 2N7002 | Top | 34.0000 | 79.5000 | 0.00 | SOT-23 |
| Q8 | AO3401A | Top | 38.0000 | 75.5000 | 180.00 | SOT-23 |
| Q9 | 2N7002 | Top | 38.0000 | 79.5000 | 180.00 | SOT-23 |
| R1 | 680k | Top | 105.0000 | 84.0000 | 0.00 | R_0603_1608Metric |
| R2 | 130k | Top | 109.0000 | 84.0000 | 0.00 | R_0603_1608Metric |
| R3 | 100k | Top | 117.0000 | 84.0000 | 0.00 | R_0603_1608Metric |
| R4 | 1M | Top | 6.0000 | 64.0000 | 0.00 | R_0603_1608Metric |
| R6 | 4.7k ELECTRET BIAS | Top | 30.0000 | 85.5000 | 90.00 | R_0603_1608Metric |
| R7 | 4.7k ELECTRET BIAS | Top | 30.0000 | 91.8000 | 90.00 | R_0603_1608Metric |
| R8 | 4.7k ELECTRET BIAS | Top | 30.0000 | 98.1000 | 90.00 | R_0603_1608Metric |
| R9 | 4.7k ELECTRET BIAS | Top | 30.0000 | 104.4000 | 90.00 | R_0603_1608Metric |
| R10 | 100R RF | Top | 34.0000 | 85.5000 | 90.00 | R_0603_1608Metric |
| R11 | 100R RF | Top | 34.0000 | 91.8000 | 90.00 | R_0603_1608Metric |
| R12 | 100R RF | Top | 34.0000 | 98.1000 | 90.00 | R_0603_1608Metric |
| R13 | 100R RF | Top | 34.0000 | 104.4000 | 90.00 | R_0603_1608Metric |
| R14 | 1M | Top | 46.0000 | 85.5000 | 90.00 | R_0603_1608Metric |
| R15 | 1M | Top | 46.0000 | 91.8000 | 90.00 | R_0603_1608Metric |
| R16 | 1M | Top | 46.0000 | 98.1000 | 90.00 | R_0603_1608Metric |
| R17 | 1M | Top | 46.0000 | 104.4000 | 90.00 | R_0603_1608Metric |
| R18 | 68k 0.1% | Top | 50.0000 | 85.5000 | 90.00 | R_0603_1608Metric |
| R19 | 33k 0.1% | Top | 54.0000 | 85.5000 | 90.00 | R_0603_1608Metric |
| R20 | 68k 0.1% | Top | 50.0000 | 91.8000 | 90.00 | R_0603_1608Metric |
| R21 | 33k 0.1% | Top | 54.0000 | 91.8000 | 90.00 | R_0603_1608Metric |
| R22 | 68k 0.1% | Top | 50.0000 | 98.1000 | 90.00 | R_0603_1608Metric |
| R23 | 33k 0.1% | Top | 54.0000 | 98.1000 | 90.00 | R_0603_1608Metric |
| R24 | 68k 0.1% | Top | 50.0000 | 104.4000 | 90.00 | R_0603_1608Metric |
| R25 | 33k 0.1% | Top | 54.0000 | 104.4000 | 90.00 | R_0603_1608Metric |
| R26 | 10k 0.1% | Bottom | 60.0000 | 85.5000 | 90.00 | R_0603_1608Metric |
| R27 | 10k 0.1% | Bottom | 60.0000 | 91.8000 | 90.00 | R_0603_1608Metric |
| R28 | 10k 0.1% | Bottom | 60.0000 | 98.1000 | 90.00 | R_0603_1608Metric |
| R29 | 10k 0.1% | Bottom | 60.0000 | 104.4000 | 90.00 | R_0603_1608Metric |
| R30 | 90.9k 0.1% | Bottom | 66.0000 | 85.5000 | 90.00 | R_0603_1608Metric |
| R31 | 90.9k 0.1% | Bottom | 66.0000 | 91.8000 | 90.00 | R_0603_1608Metric |
| R32 | 90.9k 0.1% | Bottom | 66.0000 | 98.1000 | 90.00 | R_0603_1608Metric |
| R33 | 90.9k 0.1% | Bottom | 66.0000 | 104.4000 | 90.00 | R_0603_1608Metric |
| R34 | 100R | Top | 78.0000 | 85.5000 | 90.00 | R_0603_1608Metric |
| R35 | 100R | Top | 78.0000 | 91.8000 | 90.00 | R_0603_1608Metric |
| R36 | 100R | Top | 78.0000 | 98.1000 | 90.00 | R_0603_1608Metric |
| R37 | 100R | Top | 78.0000 | 104.4000 | 90.00 | R_0603_1608Metric |
| R42 | 100R | Top | 10.5000 | 57.5000 | 0.00 | R_0603_1608Metric |
| R43 | 100k | Top | 14.5000 | 57.5000 | 0.00 | R_0603_1608Metric |
| R44 | 4.7k | Bottom | 96.0000 | 40.0000 | 0.00 | R_0603_1608Metric |
| R45 | 4.7k | Bottom | 100.0000 | 40.0000 | 0.00 | R_0603_1608Metric |
| R46 | 33R | Bottom | 104.0000 | 40.0000 | 0.00 | R_0603_1608Metric |
| R47 | 33R | Bottom | 108.0000 | 40.0000 | 0.00 | R_0603_1608Metric |
| R48 | 33R | Bottom | 112.0000 | 40.0000 | 0.00 | R_0603_1608Metric |
| R49 | 33R | Bottom | 116.0000 | 40.0000 | 0.00 | R_0603_1608Metric |
| R50 | 10k | Bottom | 102.0000 | 16.0000 | 0.00 | R_0603_1608Metric |
| R51 | 10k | Bottom | 102.0000 | 20.0000 | 0.00 | R_0603_1608Metric |
| R52 | 10k | Bottom | 106.0000 | 20.0000 | 0.00 | R_0603_1608Metric |
| R53 | 10k | Bottom | 110.0000 | 20.0000 | 0.00 | R_0603_1608Metric |
| R54 | 2.2k | Top | 70.0000 | 108.0000 | 0.00 | R_0603_1608Metric |
| R55 | 1k | Top | 78.0000 | 108.0000 | 0.00 | R_0603_1608Metric |
| R56 | 100R TFT BACKLIGHT | Top | 88.0000 | 57.0000 | 0.00 | R_0805_2012Metric |
| R57 | 33R | Bottom | 86.5000 | 44.5000 | 0.00 | R_0603_1608Metric |
| R58 | 33R | Bottom | 90.5000 | 44.5000 | 0.00 | R_0603_1608Metric |
| R59 | 33R | Bottom | 94.5000 | 44.5000 | 0.00 | R_0603_1608Metric |
| R60 | 10k | Bottom | 98.5000 | 44.5000 | 0.00 | R_0603_1608Metric |
| R61 | 100R | Bottom | 102.5000 | 44.5000 | 0.00 | R_0603_1608Metric |
| R62 | 470R | Top | 93.0000 | 58.0000 | 0.00 | R_0603_1608Metric |
| R63 | 470R | Top | 96.5000 | 58.0000 | 0.00 | R_0603_1608Metric |
| R64 | 100k | Top | 108.0000 | 48.0000 | 0.00 | R_0603_1608Metric |
| R65 | 10R | Top | 125.0000 | 64.0000 | 0.00 | R_0603_1608Metric |
| R66 | 10R | Top | 125.0000 | 67.5000 | 0.00 | R_0603_1608Metric |
| R67 | 100R MIC BIAS FILTER | Top | 28.0000 | 80.0000 | 0.00 | R_0603_1608Metric |
| R69 | 33R | Bottom | 120.0000 | 40.0000 | 0.00 | R_0603_1608Metric |
| R70 | 10k | Bottom | 102.0000 | 28.0000 | 0.00 | R_0603_1608Metric |
| R71 | 10k | Bottom | 106.0000 | 28.0000 | 0.00 | R_0603_1608Metric |
| R72 | 10k | Bottom | 110.0000 | 28.0000 | 0.00 | R_0603_1608Metric |
| R73 | 10k | Bottom | 114.0000 | 28.0000 | 0.00 | R_0603_1608Metric |
| R74 | 10k | Bottom | 118.0000 | 28.0000 | 0.00 | R_0603_1608Metric |
| R75 | 5.1k | Top | 33.0000 | 9.0000 | 90.00 | R_0603_1608Metric |
| R76 | 5.1k | Top | 47.0000 | 9.0000 | 90.00 | R_0603_1608Metric |
| R77 | 100k | Top | 56.0000 | 14.0000 | 0.00 | R_0603_1608Metric |
| R78 | 47k | Top | 52.0000 | 14.0000 | 0.00 | R_0603_1608Metric |
| R79 | 10k | Top | 17.0000 | 41.5000 | 0.00 | R_0603_1608Metric |
| R80 | 75k | Top | 5.0000 | 41.5000 | 0.00 | R_0603_1608Metric |
| R81 | 10k | Top | 9.0000 | 41.5000 | 0.00 | R_0603_1608Metric |
| R82 | 80.6k | Top | 13.0000 | 41.5000 | 0.00 | R_0603_1608Metric |
| R83 | 10k | Top | 18.5000 | 57.5000 | 0.00 | R_0603_1608Metric |
| R84 | 100R | Top | 100.0000 | 104.0000 | 0.00 | R_0603_1608Metric |
| R85 | 100k | Top | 100.0000 | 107.5000 | 0.00 | R_0603_1608Metric |
| R86 | 1M | Top | 30.0000 | 74.5000 | 0.00 | R_0603_1608Metric |
| R87 | 1M | Top | 30.0000 | 77.5000 | 0.00 | R_0603_1608Metric |
| R88 | 1M | Top | 136.5000 | 28.5000 | 90.00 | R_0603_1608Metric |
| R89 | 1M | Top | 124.0000 | 31.5000 | 0.00 | R_0603_1608Metric |
| R90 | 1M | Top | 128.0000 | 31.5000 | 0.00 | R_0603_1608Metric |
| R91 | 1.1k ILIM | Top | 123.5000 | 20.5000 | 0.00 | R_0603_1608Metric |
| R92 | 1.2k ISET | Top | 127.0000 | 20.5000 | 0.00 | R_0603_1608Metric |
| R93 | 10k TS | Top | 130.5000 | 20.5000 | 0.00 | R_0603_1608Metric |
| R94 | 100k | Top | 134.0000 | 20.5000 | 0.00 | R_0603_1608Metric |
| R95 | 100k | Top | 124.0000 | 24.5000 | 0.00 | R_0603_1608Metric |
| R96 | 10k | Bottom | 102.0000 | 36.0000 | 0.00 | R_0603_1608Metric |
| R97 | 10k | Bottom | 106.0000 | 36.0000 | 0.00 | R_0603_1608Metric |
| R98 | 100k | Top | 41.0000 | 74.0000 | 90.00 | R_0603_1608Metric |
| R99 | 100R | Top | 41.0000 | 80.2000 | 90.00 | R_0603_1608Metric |
| R100 | 100k | Top | 26.5000 | 70.9000 | 90.00 | R_0603_1608Metric |
| R101 | 100k | Top | 41.0000 | 77.1000 | 90.00 | R_0603_1608Metric |
| R102 | 100R | Top | 38.0000 | 82.5000 | 0.00 | R_0603_1608Metric |
| R103 | 100k | Top | 26.5000 | 74.0000 | 90.00 | R_0603_1608Metric |
| R104 | 100k BLEED | Top | 26.5000 | 77.1000 | 90.00 | R_0603_1608Metric |
| R106 | 10k | Top | 34.5000 | 68.5000 | 0.00 | R_0603_1608Metric |
| R107 | 100R | Top | 38.0000 | 68.5000 | 0.00 | R_0603_1608Metric |
| R108 | 100k | Top | 34.5000 | 71.5000 | 0.00 | R_0603_1608Metric |
| R110 | 100R RF | Bottom | 32.0000 | 85.5000 | 90.00 | R_0603_1608Metric |
| R111 | 100R RF | Bottom | 32.0000 | 91.8000 | 90.00 | R_0603_1608Metric |
| R112 | 100R RF | Bottom | 32.0000 | 98.1000 | 90.00 | R_0603_1608Metric |
| R113 | 100R RF | Bottom | 32.0000 | 104.4000 | 90.00 | R_0603_1608Metric |
| R114 | 1M | Bottom | 48.0000 | 85.5000 | 90.00 | R_0603_1608Metric |
| R115 | 1M | Bottom | 48.0000 | 91.8000 | 90.00 | R_0603_1608Metric |
| R116 | 1M | Bottom | 48.0000 | 98.1000 | 90.00 | R_0603_1608Metric |
| R117 | 1M | Bottom | 48.0000 | 104.4000 | 90.00 | R_0603_1608Metric |
| R118 | 10k 0.1% | Bottom | 52.0000 | 85.5000 | 90.00 | R_0603_1608Metric |
| R119 | 10k 0.1% | Bottom | 52.0000 | 91.8000 | 90.00 | R_0603_1608Metric |
| R120 | 10k 0.1% | Bottom | 52.0000 | 98.1000 | 90.00 | R_0603_1608Metric |
| R121 | 10k 0.1% | Bottom | 52.0000 | 104.4000 | 90.00 | R_0603_1608Metric |
| R122 | 90.9k 0.1% | Bottom | 56.0000 | 85.5000 | 90.00 | R_0603_1608Metric |
| R123 | 90.9k 0.1% | Bottom | 56.0000 | 91.8000 | 90.00 | R_0603_1608Metric |
| R124 | 90.9k 0.1% | Bottom | 56.0000 | 98.1000 | 90.00 | R_0603_1608Metric |
| R125 | 90.9k 0.1% | Bottom | 56.0000 | 104.4000 | 90.00 | R_0603_1608Metric |
| R126 | 100k | Bottom | 50.0000 | 85.5000 | 90.00 | R_0603_1608Metric |
| R127 | 100k | Bottom | 50.0000 | 91.8000 | 90.00 | R_0603_1608Metric |
| R128 | 100k | Bottom | 50.0000 | 98.1000 | 90.00 | R_0603_1608Metric |
| R129 | 100k | Bottom | 50.0000 | 104.4000 | 90.00 | R_0603_1608Metric |
| R130 | 130k | Top | 13.3000 | 48.6000 | 90.00 | R_0603_1608Metric |
| R131 | 20k | Top | 13.3000 | 52.4000 | 90.00 | R_0603_1608Metric |
| SW2 | RECORD START/STOP | Top | 43.7500 | 71.2500 | 0.00 | SW_PUSH_6mm |
| SW3 | MASTER GAIN | Top | 61.5000 | 71.0000 | 0.00 | RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm |
| SW4 | TFT MENU NAV | Top | 91.0000 | 73.5000 | 0.00 | SW_Nav5_ALPS_RKJXT1F42001 |
| U1 | TPS62160DGK | Top | 105.0000 | 88.0000 | 0.00 | VSSOP-8_3x3mm_P0.65mm |
| U2 | TPS7A2033PDBV | Bottom | 88.0000 | 55.6000 | 0.00 | SOT-23-5 |
| U3 | TLE2426ID | Top | 46.0000 | 26.0000 | 0.00 | SOIC-8_3.9x4.9mm_P1.27mm |
| U4 | CD4053BPW | Top | 40.0000 | 44.0000 | 0.00 | TSSOP-16_4.4x5mm_P0.65mm |
| U5 | CD4053BPW | Top | 40.0000 | 56.0000 | 0.00 | TSSOP-16_4.4x5mm_P0.65mm |
| U6 | OPA1654 | Top | 52.0000 | 50.0000 | 0.00 | TSSOP-14_4.4x5mm_P0.65mm |
| U7 | PCM1864DBT | Top | 83.5000 | 49.5000 | 0.00 | TSSOP-30_4.4x7.8mm_P0.5mm |
| U8 | Teensy 4.1 | Bottom | 60.0000 | 62.5000 | 0.00 | Teensy41_Socket |
| U9 | PCM5102A | Top | 100.0000 | 50.0000 | 0.00 | TSSOP-20_4.4x6.5mm_P0.65mm |
| U10 | TPA6130A2RTJ | Top | 112.0000 | 56.0000 | 0.00 | WQFN-20-1EP_4x4mm_P0.5mm_EP2.7x2.7mm |
| U11 | TPS61175PWP | Top | 9.5000 | 31.5000 | 180.00 | Texas_HTSSOP-14-1EP_4.4x5mm_P0.65mm_EP3.4x5mm_Mask3.155x3.255mm |
| U12 | ADP7142AUJZ | Top | 9.5000 | 50.5000 | 0.00 | TSOT-23-5 |
| U13 | BQ24074RGT | Top | 129.5000 | 16.5000 | 0.00 | VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm |
| U14 | TPS7A2033PDBV | Bottom | 88.0000 | 59.5000 | 0.00 | SOT-23-5 |
| U15 | CD4053BPW | Top | 40.5000 | 63.0000 | 0.00 | TSSOP-16_4.4x5mm_P0.65mm |
| U16 | OPA1654 | Top | 52.0000 | 61.5000 | 0.00 | TSSOP-14_4.4x5mm_P0.65mm |

(Y in the CPL is negative-down per KiCad; shown here as positive distance from the top edge. Test points TP1-TP14 and fiducials are not placements.)

### Test points (bottom side)

| TP | Net | Position |
|---|---|---|
| TP1 | USB_DP | (56.5, 18.0) B.Cu |
| TP2 | USB_DM | (56.5, 21.5) B.Cu |
| TP3 | ADC_MCLK | (84.5, 36.5) B.Cu |
| TP4 | ADC_BCLK | (88.0, 36.5) B.Cu |
| TP5 | ADC_LRCLK | (91.5, 36.5) B.Cu |
| TP6 | ADC_TDM | (95.0, 36.5) B.Cu |
| TP7 | ADC_DOUT2 | (98.5, 36.5) B.Cu |
| TP8 | GND | (81.0, 36.5) B.Cu |
| TP9 | DAC_BCLK | (86.5, 42.2) B.Cu |
| TP10 | DAC_LRCLK | (90.5, 42.2) B.Cu |
| TP11 | DAC_DIN | (94.5, 42.2) B.Cu |
| TP12 | +3V3_DC | (84.0, 63.0) B.Cu |
| TP13 | GND | (82.5, 42.2) B.Cu |
| TP14 | GND | (81.0, 59.5) B.Cu |

## 14. Longest and most exposed nets

| Net | Length (mm) | Segments | Vias | Layers |
|---|---:|---:|---:|---|
| +5V | 364.0 | 126 | 10 | B.Cu 162, F.Cu 202 |
| CHASSIS | 250.9 | 77 | 4 | B.Cu 159, F.Cu 92 |
| VBAT | 234.1 | 54 | 6 | B.Cu 118, F.Cu 116 |
| VREF | 219.2 | 94 | 2 | B.Cu 141, F.Cu 79 |
| +9V | 205.9 | 74 | 4 | B.Cu 59, F.Cu 146 |
| I2C_SCL | 182.6 | 52 | 3 | B.Cu 62, F.Cu 120 |
| +10V5 | 180.8 | 44 | 4 | B.Cu 28, F.Cu 153 |
| BOOST_EN | 173.3 | 30 | 3 | B.Cu 54, F.Cu 120 |
| VBOOST_IN | 169.2 | 36 | 0 | F.Cu 169 |
| +3V3_D | 164.6 | 64 | 5 | B.Cu 73, F.Cu 92 |
| +9V_FUSED | 160.4 | 17 | 2 | B.Cu 31, F.Cu 130 |
| GAIN_SW | 157.2 | 38 | 2 | B.Cu 103, F.Cu 54 |
| GND | 154.5 | 186 | 302 | B.Cu 39, F.Cu 116 |
| NAV_ENC_A | 150.3 | 37 | 3 | B.Cu 136, F.Cu 14 |
| I2C_SDA | 144.6 | 45 | 3 | B.Cu 50, F.Cu 95 |
| REC_SW | 137.6 | 25 | 2 | B.Cu 93, F.Cu 45 |
| GAIN_B | 135.8 | 18 | 1 | B.Cu 89, F.Cu 46 |
| NAV_DOWN | 122.1 | 33 | 1 | B.Cu 114, F.Cu 8 |
| NAV_ENC_B | 121.2 | 22 | 2 | B.Cu 82, F.Cu 39 |
| TFT_LED | 116.4 | 38 | 5 | B.Cu 41, F.Cu 75 |
| NAV_PUSH | 115.4 | 23 | 0 | B.Cu 115 |
| NAV_RIGHT | 114.1 | 23 | 0 | B.Cu 114 |
| GAIN_A | 113.8 | 17 | 1 | B.Cu 84, F.Cu 30 |
| NAV_UP | 112.4 | 22 | 1 | B.Cu 97, F.Cu 15 |
| VBUS_FUSED | 111.9 | 30 | 2 | B.Cu 9, F.Cu 103 |
| NAV_LEFT | 107.8 | 25 | 1 | B.Cu 106, F.Cu 2 |
| REC_LED | 107.2 | 22 | 1 | B.Cu 104, F.Cu 3 |
| HP_ENABLE | 101.8 | 15 | 3 | B.Cu 78, F.Cu 23 |
| BRU_CPRE | 96.3 | 18 | 1 | B.Cu 77, F.Cu 20 |
| LINE_JACK_L | 96.2 | 16 | 2 | B.Cu 6, F.Cu 90 |

Crosstalk audit (tools/audio_audit2.py on the final board): 0 broadside pairs (clock over analog on facing layers), 12 same-layer parallel clock/analog runs totalling 45.9 mm; worst ADC_TDM_IC beside BRU_ADC 9.9 mm at 0.15 mm on B.Cu near (83, 64), then ADC_MCLK_IC beside BLD_ADC 8.1 mm at 0.30 mm. The victims are the 10 nF-terminated _ADC nodes. Bench item.

## 15. DRC and ERC, every severity

ERC: 0 errors, 0 warnings (CD4053 switch pins are typed passive in the embedded symbol so the bidirectional-to-power warnings do not fire).

DRC with `--severity-all --all-track-errors --schematic-parity` on the final board:

| Rule | Count | Severity | What it is |
|---|---:|---|---|
| footprint_symbol_field_mismatch | 199 | warning | schematic symbols carry an AltMPN field the footprints do not; informational |
| net_conflict | 199 | warning | the generated schematic uses root-sheet local labels, which KiCad names '/NET' while the board says 'NET'; connectivity is identical (parity 0 at error level) |
| silk_overlap | 105 | warning | reference designator text overlapping other silk text; cosmetic, the assembly PDFs are the readable copy |
| silk_over_copper | 98 | warning | reference text crossing a pad; the Gerber export subtracts the solder mask so nothing prints on copper |
| silk_edge_clearance | 17 | warning | connector outlines (J2, J4, D4, D5) drawn past the board edge because the parts overhang the wall |

Errors: 0. Unconnected: 0. The all-severity run after the 2026-09-15 re-route also listed 4 hole_to_hole warnings (GND stitching vias dropped into the J10, SW2 and U8 GND pad holes by the stitching pass); those vias were removed before the counts above were taken. The In1/In2 layer types are power, TP1/TP2 are excluded from the BOM, and the U11/U13 exposed-pad thermal vias are in place, all re-applied after the re-route.

## 16. Analyzer findings and how each was dispositioned

| Source | Rule | Finding | Disposition |
|---|---|---|---|
| Dossier | - | Teensy 4.1 socket footprint: rows 17.78 mm apart (module 15.24 mm) and right row shifted one position (3V3/GND misplaced, 22 signals on the wrong pin) | FIXED 2026-09-15: footprint corrected, board patched and re-routed, DRC clean, fab package rebuilt; the 2026-09-13 PCBWay zip is void |
| LM Studio | qwen3.8-27b | 17-packet local-model review, 2026-09-17: 160 lines, 13 BLOCKER claims | ALL FALSE on inspection (pinout and datasheet guesses); 3 prompts checked out; C92 placement added to Rev D. See hardware/reviews/lm-studio-triple-check-20260917.md |
| Fab package | - | Gerber set had only F.Cu and B.Cu (exporter list never updated for 4 layers) | FIXED 2026-09-13: In1/In2 exported; job file lists Copper L1-L4 |
| DRC all-sev | hole_to_hole | GND stitching vias drilled inside SW3 pad S2 and beside SW2 pad 2 | FIXED: vias removed |
| PCB | TV-001 | U13 exposed pad had 0 thermal vias; U11 had 1 | FIXED: U13 +2, U11 +4 (0.3 mm, bottom tented) |
| Cross | PS-002 | +3V3_A and CHASSIS 'two islands' (hand routes ending inside a pad / 0.4 um off a track end) | FIXED: re-seated on pad centre / exact endpoint; KiCad had already counted them connected |
| EMC | SU-001 x3 | 'adjacent signal layers': In1/In2 were typed signal in the board file | FIXED: typed power |
| Sch | - | TP1/TP2 in BOM without MPN | FIXED: excluded from BOM on schematic and board |
| PCB | track_dangling | 6 um HP_OUT_L sliver | FIXED: deleted |
| EMC | SW-003 | U1 buck hot loop 30-50 mm2 (C2 6 mm, C3 10.5 mm from VIN) | ACCEPTED: digital rail, 45 mm from preamps, metal box; Rev D: pull C2/C3 to the pins |
| EMC | DC-001 | OPA1654 nearest 100 nF 8.5 mm | ACCEPTED: 9 V LDO rail with two planes, audio bandwidth; Rev D note |
| EMC | CK-001 x11 | clock nets on outer layers | ACCEPTED: inherent to SIG/GND/GND/SIG; planes are adjacent to both routing layers |
| EMC | GP-001 | 'reference plane gaps' 75-92 % coverage on TFT_*, ADC_LRCLK, REC_LED_A | FALSE POSITIVE: coverage lost to via/THT anti-pads in the solid planes, not slots |
| EMC | IO-001 | no ferrite/ESD on the headphone jack J5 | ACCEPTED: TPA6130A2 has internal short-circuit protection; hobby-grade; Rev D could add 2 ferrites |
| EMC | IO-002 / CG-AUD | RJ45 J2 has no GND pins | BY DESIGN: cable shield to CHASSIS, signal returns are the cold legs |
| EMC | PD-001 x3 | PDN anti-resonance at 83-316 MHz on +5V, VBOOST_IN, +9V | NOT APPLICABLE: audio rails, MHz-class loads only |
| EMC | SW-001 U14 | 'switching harmonics' from U14 | FALSE POSITIVE: U14 is an LDO |
| EMC | DP-003/004 | USB D+/D- change layers / on outer layer | ACCEPTED: 12 Mbit full speed, 20 mm on board then a wire |
| EMC | RP-001 | layer transitions without a GND via within 1 mm | ACCEPTED: two solid GND planes carry the return; 329 stitching vias |
| EMC | XT-001 | ADC_BCLK/LRCLK/MCLK close spacing | ACCEPTED: clock-to-clock, same bus |
| Thermal | TS-001 | U12 'Tj 484 C' | FALSE POSITIVE: tool assumed 4.5 V out at 0.3 A; real 60 mW |
| Sch | PP-001 x3 | U11 VIN, U7 LDO pin, U8 VIN 'no DC path to a rail' | BY DESIGN: diode-fed rails and an internal-LDO output |
| Sch | VM-001 x3 | I2C_SDA/SCL and HP_ENABLE 3.3 V into the 5 V-supplied TPA6130A2 | BY DESIGN: TPA6130A2 I2C and /SD accept 1.8-3.3 V logic |
| Sch | RS-001 x5 | +9V_FUSED, +9V_MIC, PWR_LATCH_MID, PWR_LED_A, VBUS_SENSE 'no source' | BY DESIGN: fuse/filter/divider nodes named like rails |
| Sch | PU-001 | U11 EN and Teensy MISO without pull-up | BY DESIGN: EN has R88 1M pull-down and diode sources; MISO is driven by the TFT |
| Sch | UC-001/002 | no cap / no TVS on VBUS at J9 | BY DESIGN: D11 USBLC6 pin 5 is on VBUS (tool missed it); C90 10 uF sits after F2 |
| PCB | KO-001 x50 | vias 'inside keepout' | FALSE POSITIVE: bounding-box test against the triangular chamfer keepouts; KiCad DRC = 0 |
| PCB | PM-002 | D4, D5, J2, J4 courtyards past the board edge | BY DESIGN: wall-mounted parts |
| PCB | VP-001 x8 | via-in-pad on the U7 decoupling caps | ACCEPTED: 0.3 mm, bottom tented; order notes tell PCBWay |
| PCB | SK-001 | silk over a Q5 pad | COSMETIC: mask-subtracted at export |
| SPICE | - | 102 subcircuits: 90 pass, 0 fail, 12 skip (VREF bulk cap, not a filter) | OK |
| SPICE (ina_sim) | - | INA: gain 20.06 dB, -3 dB 71 kHz, CMRR 67 dB worst 100 Hz-1 kHz, 62 dB @10k, 58 dB @20k, 56 dB @50 Hz with +/-10 % caps, EIN -109.3 dBu | OK |

## 17. Bill of materials with sourcing (95 lines)

| Designators | Qty/board | Value | Manufacturer | MPN | Best source (5 boards) | Unit $ | Stock |
|---|---:|---|---|---|---|---:|---:|
| C1 | 1 | 100uF 25V | Panasonic | EEE-FT1E101AP | LCSC C178590 | 0.4731 | 488 |
| C2 | 1 | 100nF 25V | Samsung | CL21B104KCFNNNE | LCSC C28233 | 0.0411 | 599050 |
| C3,C76,C77,C85 | 4 | 10uF 25V | Samsung | CL31B106KAHNNNE | LCSC C14860 | 0.1958 | 976180 |
| C4,C21-C24,C105-C108 | 9 | 22pF C0G | Murata | GCM1885C2A220JA16D | LCSC C408549 | 0.0244 | 52750 |
| C5,C6 | 2 | 22uF 10V | Taiyo Yuden | EMK316BB7226ML-T | Mouser 963-EMK316BB7226ML-T | 0.313 | 130308 |
| C7,C9,C95 | 3 | 1uF 10V | Yageo | CC0805KKX7R9BB105 | LCSC C91185 | 0.0427 | 807440 |
| C8,C96 | 2 | 4.7uF 10V | Murata | GRM21BZ71E475KE15L | Mouser 81-GRM21BZ71E475KE5L | 0.125 | 166843 |
| C10 | 1 | 47uF 10V | Taiyo Yuden | EMK316BBJ476ML-T | LCSC C385907 | 0.3279 | 118905 |
| C11,C33-C36,C40,C41,C43,C44,C47,C50,C54,C56,C64,C69-C73,C75,C78,C89,C109,C110 | 24 | 100nF | Samsung | CL10B104KB8NNNC | LCSC C1591 | 0.0105 | 1061000 |
| C12 | 1 | 1nF 1kV C0G | Yageo | CC0805KRX7RCBB102 | LCSC C309495 | 0.0541 | 303600 |
| C13-C16,C97-C100 | 8 | 100pF C0G | Murata | GRM1885C1H101JA01D | LCSC C71664 | 0.027 | 163900 |
| C17-C20,C25-C28,C101-C104 | 12 | 4.7uF 35V FILM | Rubycon | 35MU475KC44532 | LCSC C3778321 | 0.7848 | 6901 |
| C29-C32 | 4 | 10nF C0G | TDK | C1608C0G1H103JT000N | LCSC C76599 | 0.046 | 16000 |
| C37,C74,C88 | 3 | 10uF 16V | Samsung | CL31B106KAHNNNE | LCSC C14860 | 0.1958 | 976180 |
| C39 | 1 | 1uF | Yageo | CC0805KKX7R9BB105 | LCSC C91185 | 0.0427 | 807440 |
| C42,C45,C46,C55,C62 | 5 | 10uF | Samsung | CL31B106KAHNNNE | LCSC C14860 | 0.1958 | 976180 |
| C48,C49,C93,C94 | 4 | 10nF | Samsung | CL10B103KB8NNNC | LCSC C1589 | 0.0102 | 2495400 |
| C51,C52,C83 | 3 | 2.2uF | Samsung | CL21B225KAFNNNE | LCSC C19110 | 0.0378 | 62030 |
| C53,C59-C61,C65 | 5 | 1uF | Yageo | CC0603KRX7R8BB105 | LCSC C106858 | 0.0378 | 119980 |
| C57,C58,C86,C87 | 4 | 2.2uF 25V FILM | Rubycon | 25MU225MB23225 | LCSC C3778570 | 0.6146 | 429 |
| C66 | 1 | 100uF 16V | Panasonic | EEE-FK1C101P | LCSC C128532 | 0.2697 | 6090 |
| C67,C68 | 2 | 2.2nF C0G | Samsung | CL10C222JB8NNNC | LCSC C33353 | 0.0458 | 16980 |
| C79 | 1 | 47nF | Yageo | CC0603KRX7R9BB473 | LCSC C107093 | 0.0077 | 1544200 |
| C80 | 1 | 4.7nF C0G | Murata | GRM1885C1H472JA01D | LCSC C85980 | 0.0281 | 55320 |
| C81 | 1 | 47pF C0G | Murata | GCM1885C2A470JA16D | LCSC C126580 | 0.0162 | 850 |
| C90-C92 | 3 | 10uF 10V | Murata | GRM21BZ71E106KE15L | LCSC C237493 | 0.3768 | 92685 |
| D1,D10,D12,D14 | 4 | B340A 40V 3A | Diodes Incorporated | B340A-13-F | LCSC C7450457 | 0.0293 | 16280 |
| D2 | 1 | SMBJ12A | Littelfuse | SMBJ12A | Mouser 576-SMBJ12A | 0.48 | 45272 |
| D3 | 1 | SS14 | onsemi | SS14 | Mouser 512-SS14 | 0.44 | 189943 |
| D4 | 1 | POWER BLUE | Kingbright | WP7113QBC/D | Mouser 604-WP7113QBC/D | 0.44 | 3345 |
| D5 | 1 | RECORD RED | Kingbright | WP7113ID | Mouser 604-WP7113ID | 0.21 | 79616 |
| D6-D9,D20-D23 | 8 | PESD12VL1BA | Nexperia | PESD12VL1BA,115 | LCSC C38558 | 0.3046 | 20805 |
| D11 | 1 | USBLC6-2SC6 | STMicroelectronics | USBLC6-2SC6 | Mouser 511-USBLC6-2SC6 | 0.49 | 72716 |
| D13,D15-D19 | 6 | 1N4148W | Diodes Incorporated | 1N4148W-7-F | LCSC C81598 | 0.0127 | 2380300 |
| D24 | 1 | BAT54 | Diodes Incorporated | BAT54-7-F | Mouser 621-BAT54-F | 0.19 | 90466 |
| F1 | 1 | 750mA PTC | Littelfuse | 1206L075/13.2WR | Mouser 576-1206L075/13.2WR | 0.54 | 9240 |
| F2 | 1 | 2A PTC | Littelfuse | 1206L200PR | Mouser 576-1206L200PR | 0.65 | 9074 |
| J1 | 1 | 9V DC IN | CUI Devices | PJ-102AH | LCSC C3096093 | 1.0931 | 1676 |
| J2 | 1 | AMBISONIC MIC RJ45 | Amphenol ICC | RJHSE-5380 | Mouser 523-RJHSE-5380 | 1.66 | 6190 |
| J3 | 1 | MSP3526 TFT 3.5IN 14PIN SOCKET | Sullins Connector Solutions | PPTC141LFBN-RC | DigiKey S7043-ND |  | 0 |
| J4 | 1 | 1/4in BINAURAL LINE OUT | Neutrik | NRJ6HF | Mouser 550-20311 | 0.9 | 11473 |
| J5 | 1 | 1/8in BINAURAL HEADPHONE OUT | CUI Devices | SJ1-3533NG | Mouser 490-SJ1-3533NG | 1.68 | 7539 |
| J9 | 1 | USB-C POWER + DATA | HRO | TYPE-C-31-M-12 | LCSC C165948 | 0.1873 | 231585 |
| J10 | 1 | BATTERY 1S LiPo | JST | B2B-PH-K-S | Mouser 306-B2BPHKSLFSNPP | 0.11 | 42193 |
| K1 | 1 | G6K-2F-Y 5VDC | Omron | G6K-2F-Y DC5 | Mouser 653-G6K-2F-Y-DC5 | 4.98 | 3464 |
| L1 | 1 | 2.2uH 1.5A | Abracon | ASPIAIG-F4020-2R2M-T | Mouser 815-SPIAIGF40202.2MT | 1.87 | 4229 |
| L2 | 1 | 10uH 2A | Bourns | SRN6045TA-100M | Mouser 652-SRN6045TA-100M | 0.5 | 4332 |
| Q1,Q2,Q5,Q7,Q9 | 5 | 2N7002 | Nexperia | 2N7002NXAKR | Mouser 771-2N7002NXAKR | 0.061 | 671600 |
| Q3,Q4,Q6,Q8 | 4 | AO3401A | Alpha & Omega | AO3401A | LCSC C15127 | 0.095 | 217815 |
| R1 | 1 | 680k | Yageo | RC0603FR-07680KL | Mouser 603-RC0603FR-07680KL | 0.1 | 76895 |
| R2,R130 | 2 | 130k | Yageo | RC0603FR-07130KL | LCSC C163432 | 0.0048 | 59500 |
| R3,R43,R64,R77,R85,R94,R95,R98,R100,R101,R103,R108,R126-R129 | 16 | 100k | Yageo | RC0603FR-07100KL | LCSC C14675 | 0.0036 | 8126500 |
| R4,R14-R17,R86-R90,R114-R117 | 14 | 1M | Yageo | RC0603FR-071ML | LCSC C105578 | 0.0055 | 327100 |
| R5 (DNP) | 1 | 0R CHASSIS LINK | Yageo | RC0603FR-070RL |   |  |  |
| R6-R9 | 4 | 4.7k ELECTRET BIAS | Yageo | RC0603FR-074K7L | LCSC C99782 | 0.0043 | 6862500 |
| R10-R13,R110-R113 | 8 | 100R RF | Yageo | RC0603FR-07100RL | Mouser 603-RC0603FR-07100RL | 0.1 | 4700289 |
| R18,R20,R22,R24 | 4 | 68k 0.1% | Yageo | RT0603BRD0768KL | LCSC C705793 | 0.0351 | 104620 |
| R19,R21,R23,R25 | 4 | 33k 0.1% | Yageo | RT0603BRD0733KL | LCSC C705768 | 0.0374 | 133340 |
| R26-R29,R118-R121 | 8 | 10k 0.1% | Yageo | RT0603BRD0710KL | LCSC C95204 | 0.0331 | 226200 |
| R30-R33,R122-R125 | 8 | 90.9k 0.1% | Yageo | RT0603BRD0790K9L | LCSC C728600 | 0.0434 | 23080 |
| R34-R37,R42,R61,R84,R99,R102,R107 | 10 | 100R | Yageo | RC0603FR-07100RL | Mouser 603-RC0603FR-07100RL | 0.1 | 4700289 |
| R38-R41 (DNP) | 4 | 100k | Yageo | RC0603FR-07100KL |   |  |  |
| R44,R45 | 2 | 4.7k | Yageo | RC0603FR-074K7L | LCSC C99782 | 0.0043 | 6862500 |
| R46-R49,R57-R59,R69 | 8 | 33R | Yageo | RC0603FR-0733RL | Mouser 603-RC0603FR-0733RL | 0.014 | 556259 |
| R50-R53,R60,R70-R74,R79,R81,R83,R96,R97,R106 | 16 | 10k | Yageo | RC0603FR-0710KL | LCSC C98220 | 0.0035 | 11733600 |
| R54 | 1 | 2.2k | Yageo | RC0603FR-072K2L | LCSC C114662 | 0.0043 | 218400 |
| R55 | 1 | 1k | Yageo | RC0603FR-071KL | LCSC C22548 | 0.0039 | 10602300 |
| R56 | 1 | 100R TFT BACKLIGHT | Yageo | RC0805FR-07100RL | Mouser 603-RC0805FR-07100RL | 0.1 | 535302 |
| R62,R63 | 2 | 470R | Yageo | RC0603FR-13470RL | Mouser 603-RC0603FR-13470RL | 0.014 | 38179 |
| R65,R66 | 2 | 10R | Yageo | RC0603FR-0710RL | LCSC C109318 | 0.0089 | 3647900 |
| R67 | 1 | 100R MIC BIAS FILTER | Yageo | RC0603FR-07100RL | Mouser 603-RC0603FR-07100RL | 0.1 | 4700289 |
| R75,R76 | 2 | 5.1k | Yageo | RC0603FR-075K1L | LCSC C105580 | 0.0049 | 650900 |
| R78 | 1 | 47k | Yageo | RC0603FR-0747KL | Mouser 603-RC0603FR-0747KL | 0.1 | 1800998 |
| R80 | 1 | 75k | Yageo | RC0603FR-0775KL | LCSC C114636 | 0.0061 | 179900 |
| R82 | 1 | 80.6k | Yageo | RC0603FR-0780K6L | Mouser 603-RC0603FR-0780K6L | 0.11 | 5127 |
| R91 | 1 | 1.1k ILIM | Yageo | RC0603FR-071K1L | LCSC C137780 | 0.0055 | 4400 |
| R92 | 1 | 1.2k ISET | Yageo | RC0603FR-071K2L | LCSC C114605 | 0.0066 | 310400 |
| R93 | 1 | 10k TS | Yageo | RC0603FR-0710KL | LCSC C98220 | 0.0035 | 11733600 |
| R104 | 1 | 100k BLEED | Yageo | RC0603FR-07100KL | LCSC C14675 | 0.0036 | 8126500 |
| R131 | 1 | 20k | Yageo | RC0603FR-0720KL | LCSC C105575 | 0.0056 | 3894900 |
| SW2 | 1 | RECORD START/STOP | Same Sky | TS02-66-150-BK-160-LCR-D | Mouser 179-TS0266150BK160LC | 0.13 | 3418 |
| SW3 | 1 | MASTER GAIN | Alps Alpine | EC11E15244G1 | Mouser 688-EC11E15244G1 | 4.23 | 785 |
| SW4 | 1 | TFT MENU NAV | Alps Alpine | RKJXT1F42001 | Mouser 688-RKJXT1F42001 | 9.05 | 1258 |
| U1 | 1 | TPS62160DGK | Texas Instruments | TPS62160DGKR | LCSC C60726 | 1.3794 | 1238 |
| U2,U14 | 2 | TPS7A2033PDBV | Texas Instruments | TPS7A2033PDBVR | LCSC C2862740 | 0.2217 | 59795 |
| U3 | 1 | TLE2426ID | Texas Instruments | TLE2426IDR | Mouser 595-TLE2426IDR | 2.87 | 1886 |
| U4,U5,U15 | 3 | CD4053BPW | Texas Instruments | CD4053BPWR | LCSC C106760 | 0.3464 | 775 |
| U6,U16 | 2 | OPA1654 | Texas Instruments | OPA1654AIPWR | LCSC C544430 | 2.6201 | 1151 |
| U7 | 1 | PCM1864DBT | Texas Instruments | PCM1864DBTR | LCSC C544855 | 4.5395 | 100 |
| U8 | 1 | Teensy 4.1 | PJRC | TEENSY41 | PJRC / Mouser SparkFun DEV-20360 | 33.6 | 0 |
| U9 | 1 | PCM5102A | Texas Instruments | PCM5102APWR | LCSC C107671 | 1.416 | 7991 |
| U10 | 1 | TPA6130A2RTJ | Texas Instruments | TPA6130A2RTJR | LCSC C130046 | 1.0128 | 2870 |
| U11 | 1 | TPS61175PWP | Texas Instruments | TPS61175PWPR | LCSC C43276 | 1.929 | 7886 |
| U12 | 1 | ADP7142AUJZ | Analog Devices | ADP7142AUJZ-R7 | LCSC C514356 | 3.199 | 4725 |
| U13 | 1 | BQ24074RGT | Texas Instruments | BQ24074RGTR | LCSC C54313 | 2.1424 | 417 |

Off-board / extras (QuadPreRecorder-BOM-extras.csv): 2 x Samtec SLW-124-01-G-S sockets for the Teensy, PJRC Teensy 4.1 with pins, LCDWiki MSP3526 module, 4 x M3x11 standoffs, 9 V 1 A adapter, USB-C cable, knob, keycap. Parts total about $405 for five boards at the best source plus Teensy/display/battery.

## 18. Things only a human or a bench can verify

1. **Component orientation on the assembly PDFs**: pin 1 of U1, U4-U7, U9-U16 and K1's coil polarity; the LED anodes (D4/D5 pin 2 = anode = resistor side); D1/D10/D12/D14 cathode bands toward the load; D13 cathode to +5V.
2. **Charger behaviour on a weak USB port**: EN2 = VBUS, EN1 = GND selects the 1.46 A ILIM setting; on a 500 mA port the BQ24074's VIN-DPM loop throttles rather than browning out, but confirm the unit boots from a plain computer port with a flat battery.
3. **Teensy VIN-VUSB link** must be cut on every module before it is plugged in; TP1/TP2 wires under 20 mm. Before soldering the two 1x24 sockets, lay a real Teensy 4.1 on the bare board: its pins must drop into both rows (15.24 mm apart) with the USB connector at the board-centre end (y = 62.5) and the SD slot toward the rear wall, and the square pad (GND1) must sit under the module's GND pin next to pin 0.
4. **Relay K1 NC/NO sense** (audio must pass with the coil off).
5. **Boost load step**: 10.45 V with the compensation values as drawn; scope the rail while switching the mic bias and the TFT backlight.
6. **Mic bias thump**: switching 9 V / 5 V / off with capsules connected; firmware sequencing per section 9.
7. **CMRR in dynamic mode**: 300 R source, 1 kHz common-mode drive, expect > 60 dB.
8. **ADC clocks**: probe TP3-TP7 (bottom), check ADC_TDM_IC edge quality beside BRU_ADC.
9. **Display module**: pin 1 orientation on J3, 5 V VCC, backlight current through R56.
10. **Enclosure fit**: the 1590XX walls have never been drilled against this board; print the PDFs at 100 %.
11. **Thermal**: U13 case temperature while charging at 0.74 A from a 5 V port; U12 barely warm.

## 19. Rev D list (nothing here blocks the order)

- Move C92 (10 uF on VBAT) to within 2 mm of U13's BAT pins (it sits about 10 mm away; the pack and the wide trace make it harmless now).
- Move C2/C3 (buck input) against U1's VIN pins; move a 100 nF against each OPA1654 pin 4.
- Ferrite beads or 10 R + 100 pF on the headphone jack lines; ESD on J4/J5 tips.
- Clean up 105 overlapping reference designators on the silkscreen.
- Rotate U7 so its serial pins face the Teensy (deterministic fix for the 9.9 mm ADC_TDM_IC run).
- Consider 22 nF C0G at the ADC inputs (lower anti-alias corner) once the PGA settings are known.
