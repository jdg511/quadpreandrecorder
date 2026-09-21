# Rev B pre-order review — QuadPreRecorder (Hammond 1590XX, 2-layer)

Date: 2026-09-06. Board: `hardware/QuadPreRecorder.kicad_pcb` (Rev B,
138 x 114 mm, 190 footprints, 2477 track segments, 168 vias, GND pours both
sides). Package: `hardware/manufacturing/QuadPreRecorder-RevB-PCBWay-handoff.zip`.

## Verdict

**Electrically and fabrication-ready. Not yet order-ready** — one human step
remains: the board has never been test-fitted in a physical Hammond 1590XX.
Everything the tooling can check is clean; everything that needs the real box
is still open (table below).

## What changed today (2026-09-06)

| Change | Why | Where |
|---|---|---|
| Corner chamfers 9 → 12 mm | Hammond drawing: lid-screw posts are ~Ø9 columns centred ~1.5 mm inboard of the board edge; Measured on Hammond's 1590XX STEP the posts are full height and their material ends 5.0 mm along the board-corner diagonal: 9 mm interferes by ~0.5 mm, 11 mm clears by only ~0.5 mm, 13 mm clips J4's mounting pin (DRC), 12 mm clears by 1.0 mm. Existing route still DRC-clean, no re-route. | `tools/generate_pcb.py` (CORNER) |
| U7 (PCM1864) moved (68, 50) → (83.5, 49.5), top | It sat inside the Teensy socket's two THT pin columns (x=60 / x=77.78); every ADC clock/data/decoupling net had to thread 0.74 mm gaps between 1.8 mm socket pins on both layers. Two routers had failed on the same 17 items since 2026-07-29. Now sits directly over its C41-C45 decoupling column. | `tools/generate_pcb.py` |
| Router: Freerouting 2.2.4 → 1.9.0, `-mt 1 -oit 2.0` | 2.2.4 reports the board routed but its `.ses` silently omits wires for ADC_LRCLK_IC, ADC_MICBIAS, DAC_BCLK_IC, HP_OUT_R and parts of ~15 others (KiCad then shows 19 unconnected). 1.9.0 exports all 119 nets. | `tools/route_pcb.ps1`, `tools/cache/freerouting19.jar` |
| Fiducial keepouts (r = 1.7 mm, own layer) | The DSN does not carry the fiducial footprint's 0.6 mm local clearance / 2 mm mask opening; the router put LINE_R and +9V 0.22-0.29 mm from FID3/FID6 (4 DRC errors). | `tools/generate_pcb.py` |
| GND pours re-attached to net `GND` | `import_route.py` looked up `/GND` (the Rev A net name); the regenerated schematic names it `GND`, so since 2026-09-05 both "GND plane" pours were **un-netted floating copper**. KiCad DRC could not see it because Freerouting had routed every GND pad with tracks. | `tools/import_route.py` |
| Manufacturing package regenerated; outputs renamed `RevB`; Rev A / Rev3 files excluded from the handoff zip and checksums; stray Rev3 upload zip and Rev3 paste-notes moved into `manufacturing/rev3-4layer/` | The old zip swept in the out-of-scope 4-layer files and a note telling you to upload the wrong archive. | `tools/build_manufacturing.py`, `hardware/manufacturing/` |

## Blockers and open items

| # | Item | Severity | Owner |
|---|---|---|---|
| 1 | **Physical 1590XX fit check** — no box on hand as of 2026-09-06, so a desk study against the Hammond drawing was done instead (`../enclosure-1590XX-desk-study.md`): corner chamfers raised 9 → 12 mm for the lid-screw posts (posts measured full-height on Hammond's STEP) (DRC still clean, no re-route), height stack works with the board ~15-16 mm below the lid underside. Remaining physical items happen after the PCB arrives: wall cutout drilling, SW3 encoder height variant, TFT standoff height. SW4 gets no lid hole (10 mm SKQU stem cannot reach; UI is touch + encoder push, SW4 is an internal setup control). | Not blocking the PCB order; order the 1590XX now | Jason |
| 2 | Confirm the purchased MSP3520 module's 14-pin order and 93.3 x 51.34 mm hole pattern (H5-H8 are marked PROVISIONAL-VERIFY on the board). | Blocking before drilling the lid, not before ordering the PCB | Jason |
| 3 | Confirm the CAT6 plug/cable mates with the RJHSE-5380 and preserves the pinout in `connector-pinout.md`. | Before first use | Jason |
| 4 | Firmware/mode note carried over from the 2026-07-25 review: 192 kHz four-channel TDM pushes PCM1864 BCK to 49.152 MHz; run 96 kHz 4-ch TDM or 192 kHz via 2x I2S (DOUT2 → R69 → Teensy). No PCB change needed. | Advisory | Firmware |

## Verification basis

- **KiCad 10.0.4 CLI** on the routed board: DRC `--all-track-errors
  --schematic-parity --severity-error` → 0 violations, 0 unconnected, 0
  parity issues. ERC `--severity-all` → 0 errors, 0 warnings. Same gates are
  enforced inside `build_manufacturing.py` before any export is written.
- **Raw-file checks (this review):** GND pour net assignment read directly
  from the `.kicad_pcb` (both pours `(net "GND")`, filled); board outline
  138.0 x 114.0 from Edge.Cuts; U7 and Teensy pad columns from footprint
  geometry; BOM/CPL grep for J2 = `RJHSE-5380`, U7 at (83.5, 49.5).
- **Generator checks:** 0 same-side courtyard overlaps;
  `tools/check_panel_orientation.py` passes for J2/SW1/J5/RV1/J1/J4/U8.
- **kicad-happy analyzers** (schematic, PCB `--full`, gerber, cross-domain,
  EMC, thermal, SPICE) — results and triage below.
- **Datasheets:** the electrical design (schematic) is unchanged since the
  2026-07-25 per-IC datasheet review (`rev-a-final-review.md`, instance files
  in `instances/`). This review did not repeat the pin-level datasheet pass;
  the claims below about IC behaviour are inherited from that review, not
  re-verified today. 175/175 BOM parts carry MPNs.

## Analyzer results and triage

**Schematic** (180 parts, 150 nets, trust: high): 5 "errors", all
expected topology — PP-001 on U10.12 HPVDD / U10.8 HPVSS (TPA6132A2
charge-pump rails, cap-only by design), U7.11 LDO (PCM1864 internal LDO
output, cap-only), U8.VIN (fed through D3 — the analyzer's 2-hop path search
stops at the diode), VM-001 HP_ENABLE 3.3 V → 5 V domain (TPA6132A2 EN is a
logic input with VIH well below 3.3 V). Warnings: no `datasheets/` dir in the
analysis copy (extracted text lives in `hardware/datasheets/text/`), SPI
MISO pull-up (not required), RS-001 on +9V_IN/+9V_FUSED/+9V_MIC/PWR_LED_A
(connector/fuse/diode-derived rails; ERC is clean), C37 10 µF/16 V on 9 V
(56 % — acceptable, X7R DC-bias derating applies).

**SPICE** (ngspice, 47 subcircuits): 43 pass, 0 warn, 0 fail, 4 skipped
(R19/R21/R23/R25 with C10 — sub-Hz "filters" formed by bias resistors and a
bulk cap, not real filters). Divider ratios, RC cutoffs, decoupling and the
regulator feedback network all match the schematic values.

**PCB** (`--full`, routing_complete = true): 11 "errors" — 6 × KO-001
(fiducials inside their own keepout rings; the rings allow pads, KiCad DRC
passes — analyzer does not read the pads flag) and 5 × PM-002 (J2/J4/J5/RV1/
SW1 courtyards overhang the board edge — intentional, these are the
wall-mounted parts). Warnings: TE-001 no test-point footprints (J6/J7 test
headers serve that role), TV-001 U10 has no thermal vias (TPA6132A2 in its
QFN package dissipates well under 100 mW at headphone levels — acceptable).

**Cross-domain:** 0 errors; 8 × RP-002 reference-plane coverage warnings on
the audio clock nets (ADC_LRCLK 51 %, ADC_MCLK 78 %, ADC_BCLK 84 %, DAC_BCLK
79 %, …). On a two-layer autorouted board with pours on both sides this is
inherent; the nets are 36-102 mm with 0-3 vias each.

**EMC** (risk score 23.5/100, i.e. low-moderate): 46 × GP-001 plane-gap
findings (same cause as RP-002), RP-001 missing ground stitching via next to
the DAC_BCLK_IC and ADC_BCLK layer changes, SW-001 U1 (TPS62160 buck)
harmonics land in 30-88 MHz, IO-001 no ferrite/TVS on the J5 headphone jack,
PD-001 +5 V PDN anti-resonance (analytical). None of these affect function;
they matter only if the unit is ever formally EMC-tested. The metal 1590XX
enclosure and the shielded RJ45 shell (CHASSIS) help. Cheapest wins if a
respin ever happens: two GND stitching vias near the two clock vias, and a
"Power" net class at 0.4-0.5 mm for +5V/+9V*/+3V3* (today every power net is
routed at the 0.20 mm default; adequate for the ~0.4 A total load but a wider
class would lower drop and loop inductance).

**Thermal:** 0 findings, score 100 (no component estimated above 85 °C).

**Gerbers:** all 9 expected layers plus PTH/NPTH drills present, outline
closed, dimensions 138.15 x 114.15 (line-width inclusive), X2 attributes
intact. Two GR-004 paste-vs-copper ratio warnings are the THT pads and vias
(copper flashes without paste) — expected.

## PCBWay capability check (standard 2-layer)

| Parameter | Board | PCBWay minimum | OK |
|---|---|---|---|
| Track width | 0.20 mm | 0.10 mm | ✓ |
| Clearance | 0.15 mm (min measured 0.1516) | 0.10 mm | ✓ |
| Via drill / pad / annular | 0.40 / 0.80 / 0.20 mm | 0.15 / 0.30 / 0.15 mm | ✓ |
| Smallest hole | 0.40 mm | 0.15 mm | ✓ |
| Copper to edge | ≥ 0.65 mm (keepouts) | 0.30 mm | ✓ |
| Board size | 138 x 114 mm | 3 x 3 … 600 x 1200 mm | ✓ |
| Layers / thickness / copper | 2 / 1.6 mm / 1 oz | — | ✓ |
| Solder-mask bridges | DRC mask-min-width check clean | — | ✓ |

Assembly: 175 placements (112 top / 63 bottom), 13 through-hole parts, DNP
R5 and R38-R41 flagged in the BOM and absent from the CPL. Order text is in
`manufacturing/PCBWAY-ORDER-NOTES-REVB.txt`.

## Not performed / limits

- Physical enclosure fit (item 1 above) — cannot be done from the files.
- Per-IC datasheet re-verification — inherited from the 2026-07-25 review;
  the schematic has not changed since, only placement and routing.
- Lifecycle/obsolescence audit — not run (no distributor API keys in this
  session). All parts are current-production TI/Alps/Amphenol/Neutrik/CUI
  parts as of the July review; re-check stock at quote time.
- Prior-review delta — `rev-a-final-review.md` covers a different board
  (174 x 174 Rev A). Its electrical blockers were already implemented in the
  schematic (see `rev_a_change_list` notes); its mechanical section is
  superseded by `enclosure-fit-audit.md`.
- Freerouting 2.4.1 was not tried (would need a download); 1.9.0 from the GAS
  repo was used instead and is now the pipeline default.

## Files

- Board: `hardware/QuadPreRecorder.kicad_pcb` (backup of this exact state:
  `QuadPreRecorder.kicad_pcb.revb-routed-clean-20260906`; the 17-open Sep 5
  board is `.bak-revb-17open-20260906`).
- Package: `hardware/manufacturing/QuadPreRecorder-RevB-PCBWay-handoff.zip`
  (Gerbers zip, BOM, CPL x2, STEP, assembly PDFs, schematic PDF, DRC/ERC
  reports, board stats, drill report, connector pinout, mechanical notes,
  README, order notes, SHA256SUMS).
- Renders: `hardware/exports/QuadPreRecorder-top.png`, `-bottom.png`,
  `-isometric.png`.
- Analyzer JSON (kicad-happy run 2026-09-06_0313): schematic, pcb, gerber,
  cross_analysis, emc, thermal, spice — kept in the Claude session workspace,
  not committed.
