# Rev 3 -> 4-layer conversion: status

**Date:** 2026-08-01

## Result

`QuadPreRecorder_rev3_4layer_routed.kicad_pcb` is a **4-layer board with 17 of
18 nets routed**, verified by `kicad-cli` DRC:

| Check | Result |
|---|---|
| Unconnected items | **1** (was 16) |
| DRC violations | 63 -- **all severity `warning`, zero errors** |
| Schematic parity | clean |
| Stackup (from pcbnew) | F.Cu / In1.Cu / In2.Cu / B.Cu |

The 63 warnings are 58 cosmetic silkscreen items and 2 hole-to-hole that were
already in the Rev 3 baseline, plus 3 `track_dangling` stubs left by the rip-up.

## Stackup

- **F.Cu** - signal (all original routing preserved)
- **In1.Cu** - solid GND plane
- **In2.Cu** - routing layer + GND pour
- **B.Cu** - signal (all original routing preserved)

Placement, footprints, board outline, Hammond 1590F fit and the Cat 6 jack (J2)
are **unchanged**. Only the stackup and the 18 nets differ.

## Why this was worth doing

On the 2-layer board these nets were forced into enormous detours. Same nets,
same placement, after adding the two inner layers:

| Net | 2-layer | 4-layer |
|---|---|---|
| ADC_TDM (192 kHz data) | 109.3 mm, 10 vias | **29.2 mm, 0 vias** |
| ADC_BCLK_IC | 108.5 mm, 9 vias | **49.3 mm, 2 vias** |
| ADC_DOUT2_IC | 103.7 mm, 9 vias | **49.9 mm, 2 vias** |
| ADC_MCLK_IC (24.6-49.2 MHz) | ~110 mm, 9 vias | **45.1 mm, 2 vias** |
| ADC_LDO | 126.2 mm, 9 vias | **23.8 mm, 2 vias** |
| GAIN_B | 116.9 mm, 5 vias | **47.2 mm, 1 via** |

Total: **847.5 mm over 17 nets with 34 vias**, versus roughly 1.6 m and ~120
vias on 2 layers. Every clock and data line now has a solid ground plane
directly beneath it.

## Cuts made (8 segments)

Two pads were physically stranded -- their only escape corridor was occupied by
another net, leaving 0.165 mm / 0.152 mm where 0.5 mm is required. Inner layers
do not help, because a 0.8 mm via cannot fit beside the pad either; the track
must escape laterally on the outer layer first.

- `+3V3_A` x=64.135 wall (1 seg) -- frees **U7.11 ADC_LDO**
- `HP_CPN` escape up the east side of U10 (4 segs) -- frees **U10.11 HP_CPP**
- `GND` diagonal at the U7 west neck (3 segs) -- safe, GND is carried by pours
  on F.Cu/B.Cu **and** the new solid In1.Cu plane

`HP_CPN` was rerouted (7.6 mm) and DRC confirms GND remains fully connected.

## The one open item: +3V3_A (U7 pin 8)

**This needs about a minute of hand-routing in KiCad.**

U7 pin 8 (`+3V3_A`) must run north-south past pin 11 (`ADC_LDO`), which must
escape west. **The two traces have to cross**, so one of them must change layer
in a ~1 mm corridor beside a 0.5 mm-pitch TSSOP. Only one via fits there, and
ADC_LDO has taken it.

Exhaustive search confirms no legal path for +3V3_A at 0.05 mm grid resolution
under a strict 0.15 mm clearance model. The margins are thin enough (a few
hundredths of a millimetre) that KiCad's interactive push-and-shove router,
which can place a via off-grid and nudge neighbours, will very likely succeed
where the grid-based search does not.

**To finish it:** open the board, select `+3V3_A`, and route from **U7 pin 8**
to the existing +3V3_A trace at **(64.294, 53.962)** -- about 3.7 mm south --
dropping to **In2.Cu** to cross under ADC_LDO's escape at y approximately 51.5.
Then re-run DRC; it should report 0 unconnected.

The 3 `track_dangling` warnings will also clear once this is routed (two of them
are the +3V3_A stubs themselves); the third is a 5.8 mm HP_CPN tail that can be
trimmed.

## Reproducing

`tools/autoroute/` contains the router (`arlib.py`), per-net driver (`step.py`),
exact analytic clearance validator (`validate.py`), minimal-cut search
(`autocut.py`) and the cut list (`ripup.py`). The geometry model was validated
against KiCad before use: pad positions 19/19 exact, board area exact, and net
connectivity reproducing KiCad's island count on all 16 nets.
