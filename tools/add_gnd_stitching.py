r"""Add GND stitching vias so the F/B pour islands tie down to the In1 plane.

Run with KiCad's bundled Python after import_route/cleanup_board.

A via here is a through via (F->B), so it must be clear of other nets on every
layer it passes. Rather than compute clearances directly, a candidate point is
accepted only if a small test square around it lies inside the GND fill on
F.Cu, In2.Cu AND B.Cu. If a point is inside a net's own fill on a layer, it is
clear of everything else on that layer by construction. In1.Cu is a solid GND
plane, so it is safe everywhere.
"""

from pathlib import Path
import pcbnew

ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hardware" / "QuadPreRecorder.kicad_pcb"

VIA_DIA = 0.80   # must match settings.m_ViasMinSize in generate_pcb.py
VIA_DRILL = 0.40
CLEARANCE = 0.25
GRID = 0.5
HALF = VIA_DIA / 2.0 + CLEARANCE


def mm(v):
    return pcbnew.FromMM(v)


def to_mm(v):
    return pcbnew.ToMM(v)


def fills_for(board, layer):
    """Union of every filled polygon of the GND zones on one layer."""
    out = []
    for zone in board.Zones():
        if zone.GetIsRuleArea():
            continue
        if not zone.IsOnLayer(layer):
            continue
        try:
            poly = zone.GetFilledPolysList(layer)
        except Exception:
            continue
        if poly:
            out.append(poly)
    return out


def contains(polys, x, y):
    pt = pcbnew.VECTOR2I(mm(x), mm(y))
    for p in polys:
        if p.Contains(pt):
            return True
    return False


def blocked_by_rule_area(board, x, y, margin):
    """True if a via here would land in a rule area that forbids vias.

    The fiducial keepouts and the board-edge keepouts both set DoNotAllowVias,
    and two stitching vias landed inside fiducial rings on the first attempt.
    """
    pt_offsets = ((0, 0), (margin, 0), (-margin, 0), (0, margin), (0, -margin))
    for zone in board.Zones():
        if not zone.GetIsRuleArea():
            continue
        if not zone.GetDoNotAllowVias():
            continue
        poly = zone.Outline()
        for dx, dy in pt_offsets:
            if poly.Contains(pcbnew.VECTOR2I(mm(x + dx), mm(y + dy))):
                return True
    return False


def fits(polys_by_layer, x, y):
    for dx, dy in ((0, 0), (HALF, 0), (-HALF, 0), (0, HALF), (0, -HALF),
                   (HALF * 0.7, HALF * 0.7), (-HALF * 0.7, -HALF * 0.7),
                   (HALF * 0.7, -HALF * 0.7), (-HALF * 0.7, HALF * 0.7)):
        for polys in polys_by_layer:
            if not contains(polys, x + dx, y + dy):
                return False
    return True


def main():
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    gnd = board.FindNet("GND") or board.FindNet("/GND")
    if gnd is None:
        raise RuntimeError("no GND net")

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())

    layers = (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
    fills = [fills_for(board, ly) for ly in layers]
    for ly, f in zip(layers, fills):
        n = sum(p.OutlineCount() for p in f)
        print(f"  {board.GetLayerName(ly):8} GND fill islands: {n}")

    # existing GND vias, so we do not pile up on top of one another
    placed = []
    for track in board.GetTracks():
        if track.Type() == pcbnew.PCB_VIA_T and track.GetNetname() in ("GND", "/GND"):
            p = track.GetPosition()
            placed.append((to_mm(p.x), to_mm(p.y)))
    print(f"  existing GND vias: {len(placed)}")

    added = 0
    x = 4.0
    while x < 134.0:
        y = 4.0
        while y < 110.0:
            if (fits(fills, x, y)
                    and not blocked_by_rule_area(board, x, y, HALF)
                    and all((x - px) ** 2 + (y - py) ** 2 > 36.0 for px, py in placed)):
                via = pcbnew.PCB_VIA(board)
                via.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
                via.SetWidth(mm(VIA_DIA))
                via.SetDrill(mm(VIA_DRILL))
                via.SetNet(gnd)
                via.SetViaType(pcbnew.VIATYPE_THROUGH)
                via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                board.Add(via)
                placed.append((x, y))
                added += 1
            y += GRID
        x += GRID

    print(f"  stitching vias added: {added}")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(BOARD_PATH), board)
    print(BOARD_PATH)


if __name__ == "__main__":
    main()
