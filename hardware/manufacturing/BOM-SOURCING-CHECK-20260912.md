# BOM sourcing check, Rev C3 mic-mode board (2026-09-12)

> **Update, same day (board `revc3mic4`).** Everything below section 0 is
> the morning check that found the problems; section 0 is what was done
> about them. The BOM now on disk already carries the new part numbers.

## 0. What changed after this check

**U12 is no longer the TPS7A4701.** The 9 V analog LDO is now the Analog
Devices **ADP7142AUJZ-R7** (TSOT-23-5, 200 mA, 11 uVrms, PSRR 88 dB at
10 kHz): Mouser 11 473 in stock at $4.17 (1) / $3.16 (10), LCSC C514356
4 725 at $3.20 (1) / $2.71 (10). The rail draws 25-40 mA, so the 1 A part
was never needed. Feedback divider R130 130k / R131 20k (new lines, both
deep-stock Yageo), C83 changed to 2.2 uF X7R on the LDO input. The
board was re-placed and re-routed for the new footprint; DRC/ERC clean.
Mouser tags the ADP7142 "Restricted Availability", which on that site
means export paperwork on large orders, not a stock problem; LCSC has
no such flag. Note for the parts drawer: a TPS7A4700RGWT bought earlier
only fits the old VQFN footprint, not this board.

**Every dead or zero-stock MPN in sections 2-3 was replaced in the
generators** (`tools/passive_catalog.py`, `generate_schematic.py`), so
PCBWay gets numbers that exist rather than a substitution list:

| Line | Was | Now (in stock 2026-09-12) |
|---|---|---|
| 100 nF 0603 (24 pcs) | Murata GRM188R71H104KA93D | Samsung CL10B104KB8NNNC (LCSC C1591, Basic, 1.06 M at $0.011; Mouser 0 today, Yageo CC0603KRX7R9BB104 is the listed alternate) |
| 100 nF 0805 (C2) | Murata GRM21BR71H104KA01L | Samsung CL21B104KCFNNNE (LCSC 599 k) |
| 1 uF 0805 (C7, C9, C39, C95) | Murata GRM21BR71H105KA12L | Yageo CC0805KKX7R9BB105 (Mouser 295 k, LCSC 807 k) |
| 1 uF 0603 (C53, C59-C61, C65) | Murata GRM188R71E105KA12D | Yageo CC0603KRX7R8BB105 (LCSC 120 k) |
| 10 nF 0603 X7R | Murata GRM188R71H103KA01D | Samsung CL10B103KB8NNNC (Mouser 833 k, LCSC 2.5 M) |
| 10 nF C0G (C29-C32) | Murata GRM1885C1H103JA01D | TDK C1608C0G1H103JT000N (LCSC 16 k; the Murata J successor is the alternate) |
| 2.2 nF C0G (C67, C68) | Murata GRM1885C1H222JA01D | Samsung CL10C222JB8NNNC (LCSC 17 k) |
| 10 uF 1206 (12 pcs) | Samsung CL31B106KAHNNNE (0 at Mouser) | unchanged: LCSC has 976 k of it; Murata GRM31CR71E106KA12L (LCSC 199 k) is the alternate, both are 0 at Mouser |
| 10 uF 0805 (C90-C92) | Samsung CL21B106KAYQNNE | Murata GRM21BZ71E106KE15L (LCSC 93 k; 25 V) |
| 47 uF 1206 (C10) | Murata GRM31CR61A476ME15L | Taiyo Yuden EMK316BBJ476ML-T (Mouser 208 k, LCSC 119 k) |
| 2N7002 (5 pcs) | Nexperia 2N7002,215 | Nexperia 2N7002NXAKR (Mouser 672 k) |
| BAT54 (D24) | Nexperia BAT54,215 | Diodes BAT54-7-F (Mouser 90 k) |
| SS14 (D3) | Diodes SS14-13-F | onsemi SS14 (Mouser 190 k) |
| 2 A PTC (F2) | Littelfuse 1206L200/12WR | Littelfuse 1206L200PR (Mouser 9 k) |
| LEDs D4 / D5 | Gui guang / Everlight | Kingbright WP7113QBC/D (blue) / WP7113ID (red) |

The 33k 0.1 % (R19-R25) stays Yageo RT0603BRD0733KL: 133 k at LCSC
(C705768), and the catalog now names Vishay TNPW060333K0BEEA (188 k at
Mouser) as the alternate.

**Best price, line by line.** `QuadPreRecorder-best-source-20260912.csv`
lists, for every BOM line, the cheaper of Mouser and LCSC at the 5-board
quantity with live stock. Summary: LCSC wins on 60 lines (every
capacitor and resistor, the film caps, the 0.1 % sets, the small diodes,
TPS7A2033, AO3401A, USB-C, and the ICs U1, U7, U9, U10, U11, U13, the
OPA1654s and the ADP7142 are all 10-60 % cheaper there); Mouser is
cheaper or the only stockist on 30 lines (connectors, relay, encoders,
switches, inductors, the SMA/SMB diodes, the two LEDs, the 33k 0.1 %
alternate). Parts total for five boards at the best source: about
**$405** ($229 LCSC + $175 Mouser, K1 included), plus five Teensy 4.1
(~$32-34 each), five displays (~$18) and batteries. Buying everything at
Mouser instead would be about $920 for the lines it stocks, $442 of that
being the film caps ($59 at LCSC). Three lines are neither: J3 (Sullins
socket, DigiKey only, any 1x14 female header will do), K1 (Mouser has it
under the hyphenated number G6K-2F-Y-DC5) and U8 (PJRC / SparkFun).
PCBWay sources from both, so the note in `PCBWAY-ORDER-NOTES-REVC.txt`
tells them which lines to take from LCSC.

Thin spots worth a spare order: U7 PCM1864DBTR has 100 at LCSC (25
needed; Mouser 1 856 as fallback), the 2.2 uF PMLCAP has 429 (20 needed),
the 22 pF C0G Murata GCM1885C2A220JA16D has 370 at Mouser (LCSC 52 k).

Checked every MPN in `QuadPreRecorder-BOM.csv` against Mouser (live API,
exact-MPN match, stock and unit price at the 5-board quantity) and
cross-checked the risky lines against LCSC/JLC and DigiKey. Per-line results
are in `QuadPreRecorder-BOM-stock-check-20260912.csv`. The 4 new 100k
resistors (R126-R129) added after this check use the same Yageo
RC0603FR-07100KL line that is already in the BOM (3.7 M in stock).

## Verdict

Nothing blocks a PCBWay turnkey order, but one part is thin everywhere and a
handful of MPNs are dead numbers that PCBWay would have to substitute. The
order notes already allow generic R/C substitutes; the specific asks below
keep them from guessing.

## 1. The one real risk: U12 TPS7A4701RGWR (9 V analog LDO)

| Source | Stock | Price |
|---|---|---|
| Mouser | 0 (RGWT tube version also 0) | $5.92 |
| DigiKey | full reel only (3000 min), no cut tape shown | $5.95 |
| LCSC | 48 pcs | $12.28 |

It is TI's low-noise 1 A LDO and it has been supply-constrained for a while.
For 5 boards LCSC's 48 pieces are enough, but they can vanish in a week.
Options, best first: (a) buy 6 from LCSC now (~$75) and tell PCBWay U12 is
consigned; (b) let PCBWay source it and accept a possible hold; (c) a
drop-in does not exist in this footprint; the nearest electrical equivalents
(LT3045, TPS7A49) are different packages and would be a re-spin.

## 2. Dead or unavailable MPNs on generic lines (let PCBWay substitute)

These are all commodity parts. Mouser lists the exact numbers as obsolete or
zero stock; equivalents are everywhere. Add the substitutes to the BOM before
upload so PCBWay does not ask.

| Line | BOM MPN | Problem | Use instead |
|---|---|---|---|
| 100 nF 0603 (24 pcs) | Murata GRM188R71H104KA93D | obsolete, 0 | any 0.1 uF 50 V X7R 0603 (e.g. Samsung CL10B104KB8NNNC, Yageo CC0603KRX7R9BB104) |
| 100 nF 0805 (C2) | Murata GRM21BR71H104KA01L | obsolete | any 0.1 uF 50 V X7R 0805 |
| 1 uF 0805 (C7, C9, C39, C95) | Murata GRM21BR71H105KA12L | obsolete | any 1 uF 50 V X7R 0805 |
| 1 uF 0603 (C53, C59-C61, C65, C83) | Murata GRM188R71E105KA12D | obsolete | any 1 uF 25 V X7R 0603 (C59-C61 are U10's charge-pump caps: keep 25 V or better) |
| 10 nF 0603 (C48, C49, C93, C94) | Murata GRM188R71H103KA01D | factory special order | any 10 nF 50 V X7R 0603 |
| 10 nF C0G (C29-C32, ADC inputs) | Murata GRM1885C1H103JA01D | 0 | Murata GRM1885C1H103JA01J (21 k in stock, $0.13); must stay C0G |
| 2.2 nF C0G (C67, C68, DAC filter) | Murata GRM1885C1H222JA01D | 0 | Murata GRM1885C1H222JA01J (28 k, $0.10); must stay C0G |
| 2.2 uF 0805 (C51, C52) | Murata GRM21BR71E225KE11L | 0 | Murata GRM21BR71E225KE11K (16 k, $0.15) |
| 47 uF 1206 (C10, VREF) | Murata GRM31CR61A476ME15L | 0 | GRM31CR61A476ME15K (11 pcs) or any 47 uF 10 V X5R 1206 |
| 10 uF 1206 (12 pcs) | Samsung CL31B106KAHNNNE | 0 at Mouser | CL31B106KAHNNNF or any 10 uF 25 V X7R 1206 |
| 10 uF 0805 (C90-C92) | Samsung CL21B106KAYQNNE | 0 at Mouser | CL21B106KOQNNNE (134 k, $0.30) |
| 33k 0.1 % (R19, R21, R23, R25) | Yageo RT0603BRD0733KL | 0 at Mouser, 142 k at LCSC | fine via LCSC; Vishay TNPW060333K0BEEA (188 k at Mouser) if not. Keep 0.1 %, keep the four from one lot |
| 10R, 5.1k 0603 | Yageo RC0603FR-0710RL / -075K1L | 0 at Mouser | any 1 % 0603 |
| 2N7002 (Q1, Q2, Q5, Q7, Q9) | Nexperia 2N7002,215 | 0 at Mouser | Nexperia 2N7002NXAKR (672 k) or Diodes 2N7002-7-F |
| BAT54 (D24) | Nexperia BAT54,215 | 0 at Mouser | Diodes BAT54-7-F (90 k, $0.19) |
| PESD12VL1BA (D6-D9, D20-D23) | Nexperia PESD12VL1BA,115 | "restricted" at Mouser, 20 k at LCSC | fine via LCSC. If substituted, insist on <= 30 pF: the UMW/BORN clones on LCSC are 30 pF, acceptable; do not accept a generic 12 V TVS |
| SS14 (D3) | Diodes SS14-13-F | not at Mouser | onsemi SS14 (190 k) or Vishay SS14-E3/61T |
| 2 A PTC (F2) | Littelfuse 1206L200/12WR | number not found | Littelfuse 1206L200PR (9 k, $0.65) |
| LEDs D4, D5 | Gui guang 3A4BUD / Everlight 1254-10SURT | obscure / 3000 min | any blue and any red LED of the same footprint; allow substitutes |
| 9 V barrel J1 | CUI PJ-102AH | 0 at Mouser, 1.7 k at LCSC | fine via LCSC |
| 22 pF C0G (C4, C21-C24, C105-C108) | Murata GCM1885C2A220JA16D | 370 left at Mouser | enough for 5 boards (45 needed); GCM1885C2A220JA16J is the successor |

## 3. Parts PCBWay can only get from LCSC (fine, but say so)

| Line | MPN | LCSC | Stock | Price |
|---|---|---|---|---|
| C17-C20, C25-C28, C101-C104 (4.7 uF 35 V PMLCAP 1812) | Rubycon 35MU475KC44532 | C3778321 | 8264 | $1.05 (Mouser: 0 stock and $7.37) |
| C57, C58, C86, C87 (2.2 uF 25 V PMLCAP 1210) | Rubycon 25MU225MB23225 | C3778570 | 429 | $0.75 (Mouser: 0 and $5.38) |
| J9 USB-C | HRO TYPE-C-31-M-12 | C165948 | 245 k | $0.19 |
| U2, U14 TPS7A2033PDBVR | TI | C2862740 | 47 k | $0.22 (Mouser 0) |
| Q3, Q4, Q6, Q8 AO3401A | AOS | C15127 (basic) | 597 k | $0.09 |
| U4, U5, U15 CD4053BPWR | TI | C106760 | 876 | $0.43 (Mouser 3184, $0.67 either way) |

The film caps are the biggest single cost line on the board (60 pieces for
5 boards, about $63 from LCSC versus $442 if someone bought them at Mouser).
Make sure the quote shows them sourced from LCSC.

## 4. Key ICs, all available

| Ref | MPN | Mouser stock | Mouser unit (qty 5-10) | LCSC |
|---|---|---|---|---|
| U7 | PCM1864DBTR | 1856 | $6.32 | 100 |
| U9 | PCM5102APWR | 69 | $3.81 | 8916 |
| U10 | TPA6130A2RTJR | 265 | $1.24 | 2870 |
| U11 | TPS61175PWPR | 53 | $4.49 | 7886 |
| U13 | BQ24074RGTR | 1342 | $2.43 | 720 |
| U6, U16 | OPA1654AIPWR | 1335 | $2.75 | 1182 |
| U3 | TLE2426IDR | 1886 | $2.87 | not stocked (SOIC-8 only at Mouser/DigiKey) |
| U1 | TPS62160DGKR | 163 | $1.80 | 1240 |
| K1 | Omron G6K-2F-Y DC5 | 3464 (as "G6K-2F-Y-DC5") | $4.98 | |
| SW3, SW4 | Alps EC11E15244G1 / RKJXT1F42001 | 785 / 1258 | $4.91 / $9.05 | |
| J2, J4, J5 | Amphenol RJHSE-5380 / Neutrik NRJ6HF / Same Sky SJ1-3533NG | 6190 / 11473 / 7539 | $1.66 / $0.90 / $1.68 | |
| U8 | PJRC Teensy 4.1 | not at Mouser (SparkFun DEV-20360 = Teensy 4.1 w/ headers, 40 in stock, $33.60) | | |

## 5. Cost picture (5 boards, parts only)

Mouser extended price on the lines it could quote: about $910, but $550 of
that is the film caps at Mouser's price; buying those from LCSC brings the
parts total to roughly $420-450 for five boards, i.e. $85-90 per board
before the Teensy (~$32), display (~$18) and battery. Add PCBWay's board,
stencil and assembly charges (rough guess $250-350 for five two-sided
boards) and the five populated units land somewhere around $900-1100 all
in. Treat that as a sanity number, not a quote.
