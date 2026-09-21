r"""Give every surface-mount GND pad its own via down to the In1.Cu plane,
BEFORE the board is routed.

Why this exists
---------------
Patching the Specctra DSN so In1.Cu is `(type power)` is what made Freerouting
finish at all (4 minutes instead of never). But that patch also tells the
router "GND is handled by the plane", and Specctra plane semantics only really
hold for THROUGH pads, which physically touch the inner layer. A surface-mount
GND pad touches nothing but its own outer layer, so the router leaves it alone
and the outer GND pour is left to pick it up. Where the pour gets pinched off,
the pad ends up with no ground at all.

That is not hypothetical: on the 2026-09-11 route, KiCad's own connectivity
engine found 12 floating GND pads, including U2 (the 3V3 LDO) and U9 (the
PCM5102A DAC). Patching it up afterwards is hard, because by then a through
via has to clear copper on all four layers.

Doing it first is easy - the board is empty - and it is also just better
practice: every GND pin gets a short, low-inductance path to the reference
plane, which is what you want under an audio ADC anyway.

Pipeline:
    generate_pcb.py          pristine placed board + DSN
    fanout_gnd.py            THIS: adds fanout vias, re-exports the DSN
    patch_dsn_plane.py       In1.Cu -> (type power)
    freerouting              signals only; GND is already home
    generate_pcb.py          pristine board again
    import_route.py          SES carries the fanout and the signals
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

VIA = (0.60, 0.30)      # small, so it tucks in beside an 0603 pad
TRACK_W = 0.30
MAX_REACH = 2.5         # a fanout stub should be short


def main():
    board = pcbnew.LoadBoard(str(BOARD))
    existing = len(list(board.GetTracks()))
    # Rev C3: fanout_decouple.py runs first and leaves its vias/stubs on the
    # board; they are simply obstacles here.
    if existing and "--allow-existing" not in sys.argv:
        raise SystemExit(
            "board already carries %d tracks/vias - run generate_pcb.py first"
            % existing)

    gnd = board.FindNet("GND")
    if gnd is None:
        raise SystemExit("no GND net")
    gndcode = gnd.GetNetCode()

    gnd_vias = [t.GetPosition() for t in board.GetTracks()
                if t.Type() == pcbnew.PCB_VIA_T and t.GetNetCode() == gndcode]
    gnd_track_ends = []
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_TRACE_T and t.GetNetCode() == gndcode:
            gnd_track_ends += [t.GetStart(), t.GetEnd()]
    smd = []
    for fp in board.Footprints():
        for p in fp.Pads():
            if p.GetNetCode() != gndcode:
                continue
            if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH,
                                    pcbnew.PAD_ATTRIB_NPTH):
                continue        # a through pad already reaches the plane
            if any(p.HitTest(v) for v in gnd_vias):
                continue        # already has a via IN it (U10's exposed-pad array)
            if any(p.HitTest(e) for e in gnd_track_ends):
                continue        # already tied to the plane by a stub (fanout_decouple)
            smd.append((fp.GetReference() + "." + p.GetNumber(), p))
    print("surface-mount GND pads needing a via: %d" % len(smd))

    sp.TRACK_W = TRACK_W
    obs = sp.build_obstacles(board)
    done, failed = 0, []

    for name, pad in smd:
        pos = pad.GetPosition()
        px, py = sp.to_mm(pos.x), sp.to_mm(pos.y)
        skip = pad.m_Uuid.AsString()
        layer = sp.pad_layers(pad)[0]
        bb = pad.GetBoundingBox()
        start = max(sp.to_mm(bb.GetWidth()), sp.to_mm(bb.GetHeight())) / 2.0 + 0.22

        placed = False
        r = start
        while r <= start + MAX_REACH and not placed:
            for deg in range(0, 360, 10):
                a = math.radians(deg)
                x, y = px + r * math.cos(a), py + r * math.sin(a)
                if not sp.via_is_legal(x, y, VIA[0], obs, skip):
                    continue
                if not sp.track_is_legal(px, py, x, y, layer, obs, skip,
                                         new_via=(x, y)):
                    continue
                via = pcbnew.PCB_VIA(board)
                via.SetPosition(pcbnew.VECTOR2I(sp.mm(x), sp.mm(y)))
                via.SetWidth(sp.mm(VIA[0]))
                via.SetDrill(sp.mm(VIA[1]))
                via.SetNetCode(gndcode)
                via.SetViaType(pcbnew.VIATYPE_THROUGH)
                via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                board.Add(via)

                trk = pcbnew.PCB_TRACK(board)
                trk.SetStart(pcbnew.VECTOR2I(sp.mm(px), sp.mm(py)))
                trk.SetEnd(pcbnew.VECTOR2I(sp.mm(x), sp.mm(y)))
                trk.SetWidth(sp.mm(TRACK_W))
                trk.SetLayer(layer)
                trk.SetNetCode(gndcode)
                board.Add(trk)

                obs = sp.build_obstacles(board)
                done += 1
                placed = True
                break
            r += 0.1
        if not placed:
            failed.append(name)

    print("fanout vias placed: %d" % done)
    if failed:
        print("no room for %d: %s" % (len(failed), ", ".join(failed)))

    pcbnew.SaveBoard(str(BOARD), board)
    if not pcbnew.ExportSpecctraDSN(board, str(DSN)):
        raise SystemExit("Specctra DSN export failed")
    print(BOARD)
    print(DSN)


if __name__ == "__main__":
    main()
