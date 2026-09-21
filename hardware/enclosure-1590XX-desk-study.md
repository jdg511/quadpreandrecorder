# Hammond 1590XX desk study — Rev B (2026-09-06), updated for Rev C (2026-09-08)

**Rev C update:** the 9 V barrel moved to the REAR-LEFT wall, a USB-C
receptacle sits on the REAR wall, the pad toggle (left) and volume pot
(right) are gone, and the display is the MSP3526 capacitive module on 11 mm
standoffs with its touch lens inside the lid window. The §3/§4 tables carry
the Rev C values; the Rev B rows are struck where they changed.

No 1590XX box was on hand when the Rev B board went order-ready, so this is
the paper half of the enclosure check, done against Hammond's dimensioned
drawing (`https://www.hammfg.com/files/parts/pdf/1590XX.pdf`) and the part
heights already established in the retired 1590F study
(`enclosure-stackup-and-templates.md`, same jacks / pot / switches). It is
enough to release the PCB; wall drilling still needs the real box and the
real parts.

## 1. Enclosure facts (Hammond 1590XX drawing)

- Outside 145.2 x 121.2 x 39.3 mm assembled; lid 2.0 mm thick with 4 x
  Ø4.1 screw holes. (The INSIDE LID view carries 137.07 / 121.78 and 97.7 /
  112.78 dimensions for the lid's inner rim and gasket land — use the box
  dimensions, not the lid, for anything that touches the PCB.)
- Cavity: 139.0 x 115.0 at the floor, drafting to 140.7 x 116.7 at the lid
  opening (~0.05 mm per side per mm of height). Inside height 35.2 mm floor
  to lid underside. Hammond's "max PCB 138 x 114" is the floor cavity minus
  1 mm.
- Four lid screws, 6-32 UNC, on a 135.0 x 111.0 pattern (5.1 mm in from the
  outer edges). Clear floor between the corner posts: 126.0 x 102.0. Post
  depth is not dimensioned — treat them as full-height columns until measured.
- No PCB standoffs or bosses. The board is carried by its wall hardware,
  which is what `tools/generate_pcb.py` assumes (no H1-H4).

## 2. Board outline vs the cavity and the posts

- 138 x 114 board: 0.5 mm per side at the floor, ~0.85 mm per side at the
  height it actually sits (section 3). OK.
- Corner posts: 135 x 111 screw pattern with 126 x 102 clear floor means each
  post is a ~Ø9 column (r ≈ 4.5) whose centre is ~1.5 mm inboard of the
  board edge in both axes. Distance from that centre to a 45° chamfer of
  size c is (c − 3)/√2:

  | Chamfer | Post-to-board clearance |
  |---|---|
  | 9 mm (as designed 2026-07-25) | **−0.26 mm** (interferes if posts are full height) |
  | 10 mm | +0.45 mm |
  | 11 mm | +1.16 mm (paper) / +0.5 mm measured on the STEP |
  | **12 mm (adopted 2026-09-06)** | **+1.0 mm measured on the STEP** |

  **Measured on Hammond's own STEP model (2026-09-06, later):** the posts
  are full height and their material ends **5.0 mm** along the board's
  corner diagonal, so 9 mm (clears to 4.5) interfered by 0.5 mm and 11 mm
  cleared by only 0.5 mm. `CORNER` in `tools/generate_pcb.py` is now
  **12.0** (1.0 mm clearance); 13 mm would clip J4's mounting pin at the
  front-left corner. The existing route needed no change (DRC 0/0/0 after
  re-import). Model probing also confirmed floor thickness 2.05 mm (inner
  floor at −33.15 from the rim), lid underside at +2.1, inside height 35.25.
  Interactive model: `enclosure-1590XX-fit-viewer.html` (Hammond STEP +
  board STEP + dimensioned placeholders for the parts without 3D models);
  Hammond's STEP is in `vendor_assets/Hammond-1590XX.step`. Nothing else lives in the corners — the nearest items are
  FID1/FID4 at (10, 8)/(12, 8) and J4's body at 8.3 mm from the left edge,
  which stays ~2.7 mm clear of the front-left post.

## 3. Height stack

Constraints (all heights above the board's top surface unless noted):

| Item | Height | Source |
|---|---|---|
| Teensy 4.1 (TEENSY41_PINS) in 2x Samtec SLW-124-01-G-S sockets, bottom side | ~11.7 mm below the board (4.57 socket + ~2.5 pin-header plastic + 1.6 PCB + ~2.9 tallest Teensy part); 13.0 if standard 8.5 mm sockets are used instead | Samtec / PJRC |
| C66 6.3 x 5.8 electrolytic, bottom | 5.8 below | BOM |
| J2 RJHSE-5380 RJ45 body | 13.7 above (tallest wall part) | Amphenol |
| SW3 EC11E15244G1 encoder, "H20mm" footprint | shaft tip ~20 above | KiCad footprint / Alps H dim — **verify** |
| SW2 B3F-5150 | plunger **7.3** above (CORRECTED 2026-09-09: this table and the schematic both said 17.5, which is wrong; the B3F-5xxx 12 mm series is a single 7.3 mm height) | Omron drawing |
| SW4 RKJXT1F42001 nav (Rev C2) | 17 x 17 x 10.5 mm body, shaft above that - **measure the real part**; replaced the SKQUCAA010 on 2026-09-11 | Alps / LCSC C160841 |
| TFT MSP3526 in the J3 socket on 11 mm standoffs (Rev C) | module PCB bottom 11.0 above (8.5 socket + 2.5 header body); lens top ≈ 11 + 1.6 + 2.5 + 0.5 + 0.8 ≈ 16.4-16.9 above — **verify** on the purchased module | LCDWiki spec V1.0 |
| USB-C J9 receptacle (Rev C) | 3.2 above, face 0.55 inside the board edge | HRO drawing |
| LiPo 906090 pouch on the floor (Rev C battery) | 9 mm above the floor under the RIGHT half (x 80..140, y 15..105); board underside is ~18.4 above the floor and the Teensy stack (x 58..79) reaches down to ~6.7 — the pouch must stay east of x 80 | pack drawing |
| J10 JST-PH (bottom, 121, 109.5) | 6 mm below the board; pouch lead exits toward it | JST |

With inside height 35.2:

- Bottom clearance ≥ 14 mm (Teensy + 1 mm) ⇒ board top ≥ 15.6 mm above the
  floor.
- RJ45 body must stay ≥ 1 mm under the lid underside ⇒ board top ≤ 20.5 mm
  above the floor.
- **Working window: board top 19.5-20 mm above the floor = 15-16 mm below
  the lid underside.** This is essentially the 1590F study's "15 mm below the
  rim" recipe, so its control-reach fixes carry over.

Reach vs a lid underside 15.5 mm above the board (2.0 mm lid):

| Part | Result | Action |
|---|---|---|
| J2 RJ45 (13.7) | 1.8 mm under the lid underside | OK; the wall cutout is a 16.5 x 13.5-ish rectangle — measure the real jack |
| SW2 B3F-5150 (**7.3**, corrected) | **8.2 mm SHORT of the underside**, not proud of it | The old "fit a ~4 mm keycap" plan was built on the wrong 17.5 mm figure and does not work. Options: a tall plunger cap, a lid-mounted button wired down to the pads, or a panel-mount switch. See `reviews/rev-c2-sourcing-report.md` section 3. |
| SW4 RKJXT1F42001 (Rev C2) | body 10.5, shaft above that | **The 2026-09-06 "no lid hole for SW4" decision is withdrawn.** That was forced by the SKQUCAA010's short stem with no knob available. The RKJXT has a proper knob shaft plus a rotary encoder, so it gets a lid hole after all: Ø8-9 at (91, 73.5), with a ~9-11 mm knob chosen once the real part is measured against the 15.5 mm lid gap. |
| SW3 encoder H20 | shaft ends ~2.5 mm outside the lid face — **too short for a knob set-screw** | swap to the 25 or 30 mm total-height EC11E variant (same footprint, BOM change only) or use a shaft extension. Confirm the H dimension on the Alps drawing for EC11E15244G1 first |
| TFT lens on 11 mm standoffs (≈16.4-16.9, Rev C) | 0.9-1.4 mm proud of the lid underside — i.e. inside the 2 mm lid window, lens face 0.6-1.1 mm below the outer lid face | intentional: near-flush touch surface. The lid window must clear the lens outline (85.5 x 56.0 cut for the 84.96 x 55.5 lens); the module PCB (98 x 55.5) stays 2.65 mm under the lid. Everything under the module must be < 11 mm: the tallest are the barrel jack (11.0, but it is outside the module's X range) and C1 (5.8) |
| Teensy stack | 19.5 − 1.6 − 11.7 ≈ 6 mm floor clearance | OK |
| microSD access | Teensy card slot is at the rear wall (design intent, `SD CARD SLOT THIS EDGE`); card plane ≈ 9-10 mm below the board underside ≈ 8-9 mm above the floor | cut a rear-wall slot at X ≈ 69; verify finger reach with the real Teensy — the card sits nearly flush with the Teensy edge, ~3.7 mm inside the wall's inner face. The Adafruit 6070 round extender needs a Ø30 mm hole and cannot fit a 35 mm-tall box with the PCB across it; if the direct slot is unreachable, use a slim flat-ribbon microSD extender through a rectangular rear-wall cutout |

## 4. Wall cutouts — what to transfer when the box arrives

Lateral positions come straight from the routed board (print
`exports/QuadPreRecorder-top.pdf` / `-bottom.pdf` at 100%, check the scale bar,
and transfer the real part centres — bushing/shell centres, not footprint
anchors; the July study lists which parts had that trap). Heights are board
top + the part's centreline height from its datasheet, with board top set
19.5-20 mm above the floor:

| Wall | Part | Board X or Y of the feature | Centreline above board (datasheet — **measure the real part**) |
|---|---|---|---|
| Left (x=0) | J2 RJ45 port | Y ≈ 69.3-85.8 fab extent, centre ≈ 77.5 | port spans ~1.5 to ~12 |
| ~~Left~~ | ~~SW1 toggle~~ | removed in Rev C (pad is on screen) | — |
| ~~Right~~ | ~~RV1 pot~~ | removed in Rev C (HP volume is on the encoder/screen) | — |
| Right (x=138) | J5 SJ1-3533NG nose | Y ≈ 41 | ~2.5-3 |
| Rear (y=0) | J1 PJ-102AH barrel (Rev C) | X ≈ 17.5 | ~6.5 (Ø ~6.5-7 hole; body 13-22 in X sits between the corner post and the display standoff H5) |
| Rear (y=0) | J9 USB-C (Rev C) | X ≈ 40 | centre ~1.6 above the board top; cut ~9.5 x 4.0 rounded (receptacle 8.94 x 3.26 face) |
| Front | J4 NRJ6HF bushing | X ≈ 16.2 | ~7.5-8.9 |
| Rear (y=0) | Teensy microSD slot | X ≈ 69 (below the board) | board underside − ~10 |
| Lid | SW2 / SW3 / SW4 / TFT window | (47, 73.5) / (69, 73.5) / **(91, 73.5), Ø8-9 for the RKJXT knob** / lens window 85.5 x 56.0 centred on (72.0, 35.75) | — |

Drill pilots first; open to final size only after a dry fit with the real
board and parts.

## 5. Physical checklist (with the box in hand)

1. Confirm the posts are full height (Hammond's STEP says they are) and that
   the bare board drops to ~15.5 mm below the rim without touching; the 12 mm
   chamfer should leave ~1 mm at each post.
2. Verify the 100 mm scale bar on the printed templates.
3. Dry-fit the bare PCB at depth; transfer any deviation to all wall heights.
4. Compare the purchased MSP3526 against its drawing (hole pattern 92.0 x
   49.5, header 2.0 mm from the left edge, pin length, lens 84.96 x 55.5,
   stack thickness) before cutting the lid window or buying standoffs.
5. Confirm the encoder height variant and how SW2 reaches the lid (its plunger
   is 7.3 mm, not the 17.5 mm this study used to claim, so it falls 8.2 mm
   short) before final lid drilling. SW4 DOES get a lid hole now that it is the
   RKJXT1F42001: size it to the knob, not the shaft.
6. Re-measure J4's bushing X on the current board before drilling the front
   wall. Rev C2 moved J4's anchor from x=22 to x=26 to clear the front-left
   corner post, so the "X ≈ 16.2" figure in section 4 predates that move.
7. Rev C: check the USB-C plug overmold clears the wall cutout (plug shells
   are ~6.5 mm long; the receptacle face is ~4 mm behind the outer wall
   face) and that a barrel plug seats fully at the rear-left corner.
