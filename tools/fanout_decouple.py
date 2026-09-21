r"""Rev C3 (2026-09-12): pre-place the vias that make the converter decoupling
and the headphone amp's exposed pad actually work, BEFORE fanout_gnd.py and
BEFORE Freerouting.

Why
---
The 2026-09-11 audio audit found every 100 nF decoupler 2.4 to 11.7 mm from
its pin. The caps now sit on the bottom directly under their pins
(generate_pcb.py), but a via still has to join the pin (top) to the cap pad
(bottom), and on a 0.5 / 0.65 mm pitch TSSOP a 0.6 mm via cannot sit in the
pin row itself: it would violate clearance to the neighbouring pins. The
only legal spot is just inside the IC body, past the pad's inner end. Left to
Freerouting that via lands wherever it likes; here it lands exactly on the
cap's pad 1, fed by a stub from the pin pad's inner end.

The TPA6130A2's 2.7 x 2.7 mm exposed pad had ZERO vias in it (nearest ground
via 2.55 mm from centre, outside the pad). It is the amp's main ground return
and its only heat path. It gets a 3 x 3 array of 0.30 mm-drill vias on a
0.9 mm pitch.

Runs on the pristine placed board (right after generate_pcb.py). fanout_gnd.py
then runs with --allow-existing and treats these as obstacles.
"""
import math
import sys
from pathlib import Path

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitch_pass3 as sp

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "hardware" / "QuadPreRecorder.kicad_pcb"
DSN = ROOT / "hardware" / "review_outputs" / "QuadPreRecorder-unrouted.dsn"

VIA = (0.60, 0.30)
STUB_W = 0.20

# (ref, pin, via x, via y[, bend]). The via must land on the matching
# bottom-side cap's pad 1 (see the placement table in generate_pcb.py). An
# optional bend point routes the stub as two segments: straight out of the
# pin row first, then across to the via, so it never grazes a neighbour pad.
DECOUPLE = [
    ("U7", "6",  82.0, 47.70, (81.6, 48.5)),  # VREF -> C40 100n ADC_VREF
    ("U7", "8",  82.0, 49.30, (81.6, 49.5)),  # AVDD -> C41 100n +3V3_A (bend: a straight diagonal grazed pin 7 by 0.7 um)
    ("U7", "11", 82.0, 50.90),   # LDO out -> C43 100n ADC_LDO
    ("U7", "14", 82.0, 52.50),   # IOVDD   -> C44 100n +3V3_DC (pin 13 DVDD joins on top)
    ("U9", "1",  98.5, 47.08),   # AVDD    -> C54 100n +3V3_A
    ("U9", "8",  98.5, 51.62),   # AVDD    -> C64 100n +3V3_A
    ("U9", "20", 101.5, 47.08),  # DVDD    -> C56 100n +3V3_DC
    ("U9", "18", 101.5, 48.65),  # LDOO    -> C53 1u   DAC_LDO
]

EP = ("U10", "21", 3, 0.90)      # ref, pad number, n x n, pitch


def find_pad(board, ref, number):
    for fp in board.Footprints():
        if fp.GetReference() != ref:
            continue
        for p in fp.Pads():
            if p.GetNumber() == number:
                return p
    raise SystemExit(f"{ref}.{number} not found")


def add_via(board, x, y, netcode):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I(sp.mm(x), sp.mm(y)))
    via.SetWidth(sp.mm(VIA[0]))
    via.SetDrill(sp.mm(VIA[1]))
    via.SetNetCode(netcode)
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(via)
    return via


def add_track(board, ax, ay, bx, by, layer, netcode, width):
    trk = pcbnew.PCB_TRACK(board)
    trk.SetStart(pcbnew.VECTOR2I(sp.mm(ax), sp.mm(ay)))
    trk.SetEnd(pcbnew.VECTOR2I(sp.mm(bx), sp.mm(by)))
    trk.SetWidth(sp.mm(width))
    trk.SetLayer(layer)
    trk.SetNetCode(netcode)
    board.Add(trk)
    return trk


def main():
    board = pcbnew.LoadBoard(str(BOARD))
    if list(board.GetTracks()):
        raise SystemExit("board already carries tracks/vias - run generate_pcb.py first")
    gnd = board.FindNet("GND").GetNetCode()
    sp.TRACK_W = STUB_W

    # --- exposed pad array -------------------------------------------------
    ref, num, n, pitch = EP
    pad = find_pad(board, ref, num)
    if pad.GetNetCode() != gnd:
        raise SystemExit(f"{ref}.{num} is not on GND")
    cx, cy = sp.to_mm(pad.GetPosition().x), sp.to_mm(pad.GetPosition().y)
    sx, sy = sp.to_mm(pad.GetSizeX()), sp.to_mm(pad.GetSizeY())
    half = (n - 1) / 2.0
    ep_vias = 0
    for i in range(n):
        for j in range(n):
            x = cx + (i - half) * pitch
            y = cy + (j - half) * pitch
            if abs(x - cx) + VIA[0] / 2 > sx / 2 or abs(y - cy) + VIA[0] / 2 > sy / 2:
                raise SystemExit("EP via array does not fit inside the pad")
            add_via(board, x, y, gnd)
            ep_vias += 1
    print(f"{ref} exposed pad {sx:.2f}x{sy:.2f} at ({cx:.2f},{cy:.2f}): {ep_vias} vias, pitch {pitch}")
    # U10.13 (GND, east edge) has no room for its own fanout via: tie it
    # straight into the exposed pad with a 0.2 mm stub instead of trusting
    # the top pour to bridge the 0.2 mm gap.
    p13 = find_pad(board, ref, "13")
    if p13.GetNetCode() == gnd:
        x13, y13 = sp.to_mm(p13.GetPosition().x), sp.to_mm(p13.GetPosition().y)
        add_track(board, x13, y13, cx + sx / 2 - 0.3, y13, pcbnew.F_Cu, gnd, 0.20)
        print(f"{ref}.13 GND stub into the exposed pad")
    # U10.3 (GND, west edge, between the two INM pins 2 and 4): fanout_gnd's
    # via for it sat 0.7 mm west of the pin row and fenced HP_INP_L/R in
    # (mic-mode rebuild). Tie it into the exposed pad 0.2 mm east instead.
    p3 = find_pad(board, ref, "3")
    if p3.GetNetCode() == gnd:
        x3, y3 = sp.to_mm(p3.GetPosition().x), sp.to_mm(p3.GetPosition().y)
        add_track(board, x3, y3, cx - sx / 2 + 0.3, y3, pcbnew.F_Cu, gnd, 0.20)
        print(f"{ref}.3 GND stub into the exposed pad")

    # U13 (BQ24074, VQFN-16) pins 6 and 8 are GND and flank pin 7 (PGOOD_N)
    # on the south edge. fanout_gnd dropped pin 6's via straight south and
    # boxed pin 7 in (Rev C3 test-point route). Tie both into the exposed pad
    # (0.21 mm away, same net) instead; fanout_gnd then leaves them alone.
    ep13 = find_pad(board, "U13", "17")
    ex, ey = sp.to_mm(ep13.GetPosition().x), sp.to_mm(ep13.GetPosition().y)
    for num in ("6", "8"):
        p = find_pad(board, "U13", num)
        if p.GetNetCode() == gnd:
            x, y = sp.to_mm(p.GetPosition().x), sp.to_mm(p.GetPosition().y)
            add_track(board, x, y, x, ey + 0.5, pcbnew.F_Cu, gnd, 0.20)
            print(f"U13.{num} GND stub into the exposed pad")

    # --- decoupling vias + stubs -------------------------------------------
    pad_net = {p.m_Uuid.AsString(): p.GetNetCode()
               for fp in board.Footprints() for p in fp.Pads()}

    def obstacles_for(netcode):
        """build_obstacles() only treats GND as 'same net'. For a supply via
        the pads of ITS OWN net (the pin, the cap pad it lands on, the IC's
        second DVDD pin) are connections, not obstacles."""
        pads, segs, vias, edges, holes, rule_areas = sp.build_obstacles(board)
        pads = [t for t in pads if pad_net.get(t[5]) != netcode]
        return pads, segs, vias, edges, holes, rule_areas

    for entry in DECOUPLE:
        ref, num, vx, vy = entry[:4]
        bend = entry[4] if len(entry) > 4 else None
        pad = find_pad(board, ref, num)
        net = pad.GetNetCode()
        px, py = sp.to_mm(pad.GetPosition().x), sp.to_mm(pad.GetPosition().y)
        layer = sp.pad_layers(pad)[0]
        skip = pad.m_Uuid.AsString()
        obs = obstacles_for(net)
        if not sp.via_is_legal(vx, vy, VIA[0], obs, skip):
            raise SystemExit(f"{ref}.{num}: via at ({vx},{vy}) is not legal")
        points = [(px, py)] + ([bend] if bend else []) + [(vx, vy)]
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            if not sp.track_is_legal(ax, ay, bx, by, layer, obs, skip, new_via=(vx, vy)):
                raise SystemExit(f"{ref}.{num}: stub ({ax:.2f},{ay:.2f})->({bx:.2f},{by:.2f}) is not legal")
        add_via(board, vx, vy, net)
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            add_track(board, ax, ay, bx, by, layer, net, STUB_W)
        print(f"{ref}.{num:>2} {pad.GetNetname():9} stub {math.hypot(vx-px, vy-py):.2f} mm -> via ({vx},{vy})")

    # U10.12 (VDD) is a 0.25 mm WQFN pad with 0.5 mm neighbours; Freerouting
    # has failed to escape it on every Rev C route. C65's pad 1 is 1.1 mm due
    # east, so draw the 0.2 mm track ourselves.
    p12 = find_pad(board, "U10", "12")
    c65 = find_pad(board, "C65", "1")
    x12, y12 = sp.to_mm(p12.GetPosition().x), sp.to_mm(p12.GetPosition().y)
    x65, y65 = sp.to_mm(c65.GetPosition().x), sp.to_mm(c65.GetPosition().y)
    add_track(board, x12, y12, x12 + 0.9, y12, pcbnew.F_Cu, p12.GetNetCode(), 0.20)
    add_track(board, x12 + 0.9, y12, x65, y65, pcbnew.F_Cu, p12.GetNetCode(), 0.20)
    print(f"U10.12 {p12.GetNetname()} stub -> C65.1 ({math.hypot(x65-x12, y65-y12):.2f} mm)")

    # U11 (TPS61175, rotated 180 so EN/SS face east). Pins 6 and 7 are both
    # GND; fanout_gnd's via for pin 6 sat 1 mm east of the pin row, right in
    # the 1 x 1.6 mm pocket that pins 4 (EN) and 5 (SS) need for their own
    # escape vias, and the mic-mode route left U11.5 unrouted. Tie pin 6 to
    # pin 7 and drop ONE via for the pair north-west of pin 7 (where
    # fanout_gnd used to put pin 7's anyway).
    p6 = find_pad(board, "U11", "6")
    p7 = find_pad(board, "U11", "7")
    if p6.GetNetCode() == gnd and p7.GetNetCode() == gnd:
        x6, y6 = sp.to_mm(p6.GetPosition().x), sp.to_mm(p6.GetPosition().y)
        x7, y7 = sp.to_mm(p7.GetPosition().x), sp.to_mm(p7.GetPosition().y)
        vx7, vy7 = x7 - 0.77, y7 - 0.65
        obs = sp.build_obstacles(board)
        if not sp.via_is_legal(vx7, vy7, VIA[0], obs, p7.m_Uuid.AsString()):
            raise SystemExit("U11.7 GND via at (%.2f,%.2f) is not legal" % (vx7, vy7))
        add_track(board, x6, y6, x7, y7, pcbnew.F_Cu, gnd, 0.30)
        add_track(board, x7, y7, vx7, vy7, pcbnew.F_Cu, gnd, 0.30)
        add_via(board, vx7, vy7, gnd)
        print(f"U11.6 -> U11.7 GND tie, shared via ({vx7:.2f},{vy7:.2f})")

    # --- pre-routes that Freerouting got wrong on the Rev C3 two-layer route --
    # HP_OUT_L: left alone, the router wraps it around the front of U10.12
    # and boxes that pin in. Lay its first 5 mm through the 0.65 mm gap
    # between C60's and C65's pads; the router continues from the loose end.
    # BOOST_EN: U11.4 is fenced in on both layers once CHASSIS and +9V are
    # routed, so its way out is laid first: down the left edge on B.Cu, two
    # via hops at y 62.5 / 63.0, then east to just north of Q4.
    # U11 (mic-mode rebuild): pins 4 (EN) and 5 (SS) can only leave the
    # TPS61175 through the 1.4 x 1.6 mm pocket east of the pin row, and the
    # router kept spending that pocket on VBOOST_IN's detour to C1 plus a
    # 0.8 mm BOOST_EN via. Lay them out by hand: VBOOST_IN pin 3 -> L2 pad
    # straight east, L2 pad -> C1 straight north (0.3 mm), BOOST_SS via at
    # (13.6,30.9) then B.Cu to C79.1, BOOST_EN via at (14.25,31.5).
    PREROUTES = {
        "VBOOST_IN": ("F:12.363,32.15;15.925,32.15", 0.30),
        "VBOOST_IN ": ("F:15.925,31.5;15.925,24.5", 0.30),
        "BOOST_SS": ("F:12.363,30.85;13.6,30.9 V B:13.6,30.9;15.0,29.775", STUB_W),
        "BOOST_EN": ("F:12.363,31.5;14.25,31.5 V", STUB_W),
        "HP_OUT_L": ("F:113.96,55.5;114.5,55.5;114.6,55.4;118.2,55.4;118.6,56.4", STUB_W),
    }
    for netname, (spec, width) in PREROUTES.items():
        netname = netname.strip()
        netcode = board.FindNet(netname).GetNetCode()
        sp.TRACK_W = width
        # build_obstacles only knows GND as "same net"; for a pre-route the
        # net's own escape via/stub must count as connections, and GND must
        # count as an obstacle - so swap the name in while checking.
        sp.GND_NAMES = (netname,)
        obs = sp.build_obstacles(board)
        cur = None
        for tok in spec.split():
            if tok == "V":
                if not sp.via_is_legal(cur[0], cur[1], VIA[0], obs, None):
                    raise SystemExit(f"{netname}: pre-route via at {cur} is not legal")
                add_via(board, cur[0], cur[1], netcode)
                continue
            layer = pcbnew.F_Cu if tok[0] == "F" else pcbnew.B_Cu
            pts = [tuple(map(float, q.split(","))) for q in tok[2:].split(";")]
            if cur is not None and pts[0] != cur:
                pts.insert(0, cur)
            for a, b in zip(pts, pts[1:]):
                if not sp.track_is_legal(a[0], a[1], b[0], b[1], layer, obs, None):
                    raise SystemExit(f"{netname}: pre-route segment {a}->{b} on {board.GetLayerName(layer)} is not legal")
                add_track(board, a[0], a[1], b[0], b[1], layer, netcode, width)
            cur = pts[-1]
        print(f"{netname} pre-routed")
    sp.GND_NAMES = ("GND", "/GND")
    sp.TRACK_W = STUB_W

    # sanity: every decoupling via must sit on a bottom pad of the same net
    for t in board.GetTracks():
        if t.Type() != pcbnew.PCB_VIA_T or t.GetNetCode() == gnd:
            continue
        pos = t.GetPosition()
        hit = None
        for fp in board.Footprints():
            for p in fp.Pads():
                if p.GetNetCode() == t.GetNetCode() and p.IsOnLayer(pcbnew.B_Cu) and p.HitTest(pos):
                    hit = fp.GetReference() + "." + p.GetNumber()
        if hit is None:
            if t.GetNetname() in ("BOOST_EN", "BOOST_SS", "HP_OUT_L"):
                continue     # escape / pre-route vias, not decouplers
            raise SystemExit(f"via {t.GetNetname()} at ({sp.to_mm(pos.x):.2f},{sp.to_mm(pos.y):.2f}) lands on no bottom pad")
        print(f"   via {t.GetNetname():9} -> {hit}")

    pcbnew.SaveBoard(str(BOARD), board)
    if not pcbnew.ExportSpecctraDSN(board, str(DSN)):
        raise SystemExit("Specctra DSN export failed")
    print(BOARD)


if __name__ == "__main__":
    main()
